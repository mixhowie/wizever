# coding:utf8
import os
from collections import namedtuple

from wiznote import WizNote


class MyWizNote(WizNote):
    def get(self, url, **params):
        return self.session.get(self.url('{AS_URL}' + url), params=params)

    def get_json(self, url, **params):
        return self.get(url, **params).json()

    def get_bizs(self):
        return self.get_json('/as/user/bizs')

    def get_groups(self) -> dict:
        return self.get_json('/as/user/groups')

    def get_kbs(self):
        return self.get_json('/as/user/kb/info/all')

    def get_single_kb_info(self, kb_guid):
        return self.get_json(f'/as/user/groups/{kb_guid}')


WizGroup = namedtuple('WizGroup', 'id, name, kb_guid, kb_server')


class Note(object):
    tags = []
    content = None


def get_personal_notes():
    pass


def get_group_notes(guid):
    pass


if __name__ == '__main__':
    username = os.getenv('WIZEVER_WIZ_USERNAME')
    password = os.getenv('WIZEVER_WIZ_PASSWORD')
    assert username and password

    with MyWizNote(username=username, password=password) as wiz:
        notes = []

        wiz_groups = []
        for it in wiz.get_groups().get('result'):
            wiz_groups.append(WizGroup(it['id'], it['name'], it['kbGuid'], it['kbServer']))
        print(wiz_groups)

        notes += get_personal_notes()
