import json
import logging
import os


class LikiConfig(dict):
    paths = [os.path.expanduser(_) for _ in ('/etc/liki', '~/.liki', '.liki')]

    def __init__(self, seq=None, **kwargs):
        super(LikiConfig, self).__init__(seq=seq, **kwargs)
        for path in self.paths:
            if os.path.exists(path):
                self._load_config(path)
            if os.path.exists(f'{path}.json'):
                self._load_config(f'{path}.json')

    def _load_config(self, path):
        try:
            with open(os.path.expanduser(path), 'r', encoding='utf-8') as f:
                self.update(json.loads(f.read()))
        except Exception as ex:
            logging.warning(ex)

    def _save_config(self, path):
        try:
            with open(os.path.expanduser(path), 'w', encoding='utf-8') as f:
                f.write(json.dumps(self, ensure_ascii=False, indent=2))
        except Exception as ex:
            logging.warning(ex)

    def __setitem__(self, key, value):
        super(LikiConfig, self).__setitem__(key, value)
        self._save_config('~/.liki.json')
