import datetime
import distutils.spawn as spawn
import os
import re
import shutil

import fire

from lki.config import LKIConfig

__version__ = '0.0.5'
__all__ = [
    'LKI',
    'LKIComplain',
]

REGEX_GIT_URLS = (
    re.compile(r'^git@([^:]+):(.*?)(.git)?$'),
    re.compile(r'^http[s]?://([^/]+)/(.*?)(.git)?$'),
)


class LKIComplain(Exception):
    """ lki is complaining about something """


class Source:
    """ change source to china region """

    def apt(self):
        """ change apt's source

        translate from https://raw.githubusercontent.com/ldsink/toolbox/master/ubuntu-set-aliyun-mirror.sh
        """
        if not spawn.find_executable('apt'):
            raise LKIComplain('there is no apt executable')
        if not os.path.exists('/etc/apt/sources.list'):
            raise LKIComplain('there is no sources.list')
        backup_file = datetime.datetime.now().strftime('/etc/apt/sources.list.%Y%m%d%H%M%S.bak')
        print('Backing up at {}'.format(backup_file))
        shutil.copyfile('/etc/apt/sources.list', backup_file)
        os.system(
            r'sed -i -E "s/deb (ht|f)tp(s?)\:\/\/[0-9a-zA-Z]'
            r'([-.\w]*[0-9a-zA-Z])*(:(0-9)*)*(\/?)'
            r'([a-zA-Z0-9\-\.\?\,\'\/\\\+&amp;%\$#_]*)?\/ubuntu/deb'
            r'http\:\/\/mirrors\.aliyun\.com\/ubuntu/g" /etc/apt/sources.list'
        )


class LKI:
    """ lki is omnipotent! """

    def __init__(self):
        self._config = LKIConfig()
        self.source = Source()

    def clone(self, url: str):
        """ lki will clone a repo at a proper place.

        Examples:
            lki clone git@github.com:zaihui/hutils.git
        Equals to:
            git clone -o o git@github.com:zaihui/hutils.git {workspace}/github/zaihui-hutils

        """
        if not url.startswith('git@') and not url.startswith('http'):
            url = 'https://{}'.format(url)
        match = next((m for m in (e.search(url) for e in REGEX_GIT_URLS) if m), None)
        if not match:
            raise LKIComplain('lki can not understand git url: {}'.format(url))
        domain, project, _ = match.groups()  # type: str
        slug_domain = domain.split('.', 1)[0]
        slug_project = project.replace('/', '-')
        workspace = self._config.get('workspace', '.')
        path = os.path.join(workspace, slug_domain, slug_project)
        os.system('git clone -o o {} {}'.format(url, path))
        for key, value in self._config.get(domain, {}).items():
            os.system('cd {} && git config {} {}'.format(path, key, value))

    def set_workspace(self, path: str):
        """ set your workspace, where lki clones repositories into """
        if not os.path.isdir(path):
            raise LKIComplain('lki thinks this is not a directory: {}'.format(path))
        self._config['workspace'] = path

    def set_git_config(self, domain: str, **kwargs: str):
        """ set your domain specific configurations. user.name/user.email for example """
        domain_config = self._config.get(domain, {})
        domain_config.update(**kwargs)
        self._config[domain] = domain_config

    def __str__(self):
        return self.__class__.__doc__.strip()


def entry():
    fire.Fire(LKI)


if __name__ == '__main__':
    entry()
