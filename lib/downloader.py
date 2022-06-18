import abc
import json
import logging
import os
import pathlib
from concurrent.futures import ThreadPoolExecutor
from functools import wraps

import requests

downloaders = {}


def downloader(name: str):
    def inner(clazz):
        downloaders[name] = clazz

        @wraps(clazz)
        def wrapper(*args, **kwargs):
            clazz(*args, **kwargs)

        return wrapper

    return inner


class Downloader(abc.ABC):
    @abc.abstractmethod
    def run(self):
        ...


@downloader('wiznote')
class WizNoteDownloader(Downloader):
    AS_URL = 'https://as.wiz.cn'
    PATH_CONNECTOR = '#__#'
    NOTE_COUNT_PER_REQUEST = 100
    GET_RETRY_COUNT = 5
    GET_CONNECT_TIMEOUT = 10
    GET_READ_TIMEOUT = 60

    def __init__(self):
        username = os.getenv('WIZEVER_WIZ_USERNAME')
        password = os.getenv('WIZEVER_WIZ_PASSWORD')
        data_path = os.getenv('WIZEVER_DATA_PATH')

        assert username and password and data_path

        self.username = username
        self.password = password
        self.data_path = pathlib.Path(data_path)
        self.tag_map = {}

    def run(self):
        self._recreate_data_path()
        self._download()

    def _recreate_data_path(self):
        logging.info('recreate data path %s', self.data_path)
        os.system('rm -rf "%s"' % self.data_path)
        self.data_path.mkdir(exist_ok=True)

    def _download(self):
        self._login()
        self._store_tags()
        for folder in self._crawl_top_folders():
            self._crawl_folder_notes(folder)

    def _login(self):
        """
        登录
        """
        logging.info('login, username: %s', self.username)

        url = self.AS_URL + '/as/user/login'
        data = {
            'userId': self.username,
            'password': self.password
        }
        response = requests.post(url, data)
        payload = response.json()

        if payload['returnCode'] != 200:
            logging.error('login failure: %s', payload)
            raise

        self.token = payload['result']['token']
        self.user_guid = payload['result']['userGuid']
        self.kb_guid = payload['result']['kbGuid']
        self.kb_server = payload['result']['kbServer']

        logging.info('login success, token: %s, userGuid: %s', self.token, self.user_guid)

    def _store_tags(self):
        """
        保存标签ID、标签名、标签层级信息
        """
        url = self.kb_server + '/ks/tag/all/' + self.kb_guid
        payload = self._get(url).json()
        if payload['returnCode'] != 200:
            logging.error('request all tag failure: %s', payload)
            raise

        self.tag_map = dict([(it['tagGuid'], it['name']) for it in payload['result']])

    def _crawl_top_folders(self):
        """
        爬取顶层文件夹
        """
        url = self.kb_server + '/ks/category/all/' + self.kb_guid
        payload = self._get(url).json()
        if payload['returnCode'] != 200:
            logging.error('request folders failure: %s', payload)
            raise

        return payload['result']

    def _crawl_folder_notes(self, folder):
        """
        爬取文件夹下的笔记
        1. 为知笔记服务端对于每次查询的笔记数量有限制，故分页查询，参考 NOTE_COUNT_PER_REQUEST
        2. 查询到的笔记列表汇总后，由 _download_note 下载并保存
        """
        logging.info('crawl folder notes, folder: %s', folder)
        url = self.kb_server + '/ks/note/list/category/' + self.kb_guid
        all_folder_notes = []
        times = 0
        while True:
            params = {
                'start': self.NOTE_COUNT_PER_REQUEST * times,
                'count': self.NOTE_COUNT_PER_REQUEST,
                'category': folder,
                'orderBy': 'created',
            }
            response = self._get(url, params)
            payload = response.json()
            if payload['returnCode'] != 200:
                logging.error('request folder note list failure: %s', payload)
                raise

            all_folder_notes.extend(payload['result'])

            if len(payload['result']) < self.NOTE_COUNT_PER_REQUEST:
                break
            times += 1

        executor = ThreadPoolExecutor(max_workers=10)
        for note_metadata in all_folder_notes:
            executor.submit(self._download_note, note_metadata['docGuid'])
        executor.shutdown()

    def _download_note(self, doc_guid):
        """
        下载并存储笔记
        1. 下载笔记信息、笔记内容
        2. 笔记保存到 data_path, 由环境变量 WIZEVER_DATA_PATH 确定
        3. 下载的笔记并没有目录层级，文件名由目录 + 原始文件名组成，层级信息之间由 PATH_CONNECTOR 连接
        4. 如果文件名太长，会触发 OSError: [Errno 63] File name too long, 故文件名超过200字符, 则替换
           为 doc_guid
        """
        logging.info('download note: %s', doc_guid)

        url = self.kb_server + '/ks/note/download/' + self.kb_guid + '/' + doc_guid
        params = {
            'downloadInfo': 1,
            'downloadData': 1,
        }
        response = self._get(url, params)
        payload = response.json()
        if payload['returnCode'] != 200:
            logging.error('download note failure: %s', payload)
            raise

        category = payload['info']['category']
        title = payload['info']['title']
        note_name = (category + title).replace('/', self.PATH_CONNECTOR)
        if len(note_name) > 200:
            note_name = doc_guid
        file = self.data_path / note_name

        logging.info('save note: %s', file)

        file.write_text(json.dumps(self._post_process_note(payload), indent=4, ensure_ascii=False), encoding='utf8')

    def _post_process_note(self, note):
        note['info']['tag_names'] = [self.tag_map.get(it) for it in note['info'].get('tags', '').split('*')]
        return note

    def _get(self, url, params=None):
        """
        封装对为知笔记服务器的 GET 请求
        1. 自动添加 UA、Token
        2. 支持重试，详见 GET_RETRY_COUNT
        3. 支持设置超时时间，详见 GET_CONNECT_TIMEOUT、GET_READ_TIMEOUT
        """
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_12_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/73.0.3683.75 Safari/537.36',
            'Accept': '*/*',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'X-Wiz-Token': self.token
        }
        timeout = (self.GET_CONNECT_TIMEOUT, self.GET_READ_TIMEOUT)
        exception = None
        for i in range(self.GET_RETRY_COUNT):
            try:
                return requests.get(url, params, headers=headers, timeout=timeout)
            except Exception as e:
                exception = e
        raise exception
