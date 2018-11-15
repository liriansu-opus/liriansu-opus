import os
import re

import fire

from liki.config import LikiConfig

__version__ = '0.0.2'
__all__ = [
    'Liki',
    'LikiComplain',
]

REGEX_GIT_URLS = (
    re.compile(r'^git@([^:]+):(.*?)(.git)?$'),
    re.compile(r'^http[s]?://([^/]+)/(.*?)(.git)?$'),
)


class LikiComplain(Exception):
    """ liki is complaining about something """


class Liki:
    """ liki is omnipotent! """

    def __init__(self):
        self._config = LikiConfig()

    def clone(self, url: str):
        """ liki will clone a repo at a proper place.

        Examples:
            liki clone git@github.com:LKI/myconf
        Equals to:
            git clone -o o git@github.com:LKI/myconf {WS}/github/LKI-myconf

        """
        if not url.startswith('git@') and not url.startswith('http'):
            url = f'https://{url}'
        match = next((m for m in (e.search(url) for e in REGEX_GIT_URLS) if m), None)
        if not match:
            raise LikiComplain(f'liki can not understand git url: {url}')
        domain, project, _ = match.groups()  # type: str
        slug_domain = domain.split('.', 1)[0]
        slug_project = project.replace('/', '-')
        workspace = self._config.get('workspace', '.')
        path = os.path.join(workspace, slug_domain, slug_project)
        os.system(f'git clone -o o {url} {path}')

    def set_workspace(self, path: str):
        print(self._config.get('workspace', None))
        if not os.path.isdir(path):
            raise LikiComplain(f'liki thinks this is not a directory: {path}')
        self._config['workspace'] = path


def entry():
    fire.Fire(Liki)
