import io
import json
import logging
import os


class LKIConfig(dict):
    path = os.path.expanduser("~/.lki.json")

    def __init__(self, seq=None, **kwargs):
        super(LKIConfig, self).__init__(seq=seq, **kwargs)
        self._load_config()

    def __setitem__(self, key, value):
        super(LKIConfig, self).__setitem__(key, value)
        self._save_config()

    def _load_config(self):
        if not os.path.isfile(self.path):
            return
        try:
            with io.open(self.path, "r", encoding="utf-8") as f:
                self.update(json.loads(f.read()))
        except Exception as ex:
            logging.warning(ex)

    def _save_config(self):
        try:
            with io.open(os.path.expanduser(self.path), "w", encoding="utf-8") as f:
                f.write(json.dumps(self, ensure_ascii=False, indent=2))
        except Exception as ex:
            logging.warning(ex)
