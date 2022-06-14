# coding:utf8
import json
import logging
import os
import pathlib

import requests

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)-8s] %(message)s')

AS_URL = 'https://as.wiz.cn'


class WizNoteDownloader:
    def __init__(self, username, password, data_path):
        self.username = username
        self.password = password
        self.data_path = pathlib.Path(data_path)

    def run(self):
        self._recreate_data_path()
        self._download()

    def _recreate_data_path(self):
        logging.info('recreate data path %s', self.data_path)
        for filename in os.listdir(self.data_path):
            os.remove(self.data_path / str(filename))
        self.data_path.rmdir()
        self.data_path.mkdir(exist_ok=True)

    def _download(self):
        self._login()
        for folder in self._crawl_top_folders():
            self._crawl_folder_notes(folder)

    def _login(self):
        """
        登录
        """
        logging.info('login, username: %s', username)

        url = AS_URL + '/as/user/login'
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

    def _crawl_top_folders(self):
        """
        爬取顶层文件夹
        """
        # TODO
        url = self.kb_server + '/ks/category/all/' + self.kb_guid
        payload = self._get(url).json()
        if payload['returnCode'] != 200:
            logging.error('request failure: %s', payload)
            raise

        return payload['result']

    def _crawl_folder_notes(self, folder):
        """
        爬取文件夹下的笔记
        """
        # TODO
        logging.info('crawl folder notes, folder: %s', folder)
        url = self.kb_server + '/ks/note/list/category/' + self.kb_guid
        params = {
            'start': 0,
            'count': 100,
            'category': folder,
            'orderBy': 'created',
        }
        response = self._get(url, params)
        payload = response.json()
        if payload['returnCode'] != 200:
            logging.error('request folder note list failure: %s', payload)
            raise

        for note_metadata in payload['result']:
            self._download_note(note_metadata['docGuid'])

    def _download_note(self, doc_guid):
        """
        下载笔记
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
        file = self.data_path / category.strip('/') / title.strip('/')

        logging.info('save note: %s', file)

        file.parent.mkdir(parents=True, exist_ok=True)
        file.write_text(json.dumps(payload, indent=4))

    def _get(self, url, params=None):
        headers = {
            'User-Agent': 'PostmanRuntime/7.29.0',
            'Accept': '*/*',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'X-Wiz-Token': self.token
        }
        return requests.get(url, params, headers=headers)


if __name__ == '__main__':
    username = os.getenv('WIZEVER_WIZ_USERNAME')
    password = os.getenv('WIZEVER_WIZ_PASSWORD')
    data_path = os.getenv('WIZEVER_DATA_PATH')
    assert username and password

    downloader = WizNoteDownloader(username, password, data_path)
    downloader.run()
