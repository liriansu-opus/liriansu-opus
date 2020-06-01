import fire

from lki.error import LKIError
from lki.fires import LKI

__version__ = "0.4.0"
__all__ = [
    "LKI",
    "LKIError",
]


def entry():
    fire.Fire(LKI)


if __name__ == "__main__":
    entry()
