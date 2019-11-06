import fire

from lki.exceptions import LKIComplain
from lki.fires import LKI

__version__ = "0.0.6"
__all__ = [
    "LKI",
    "LKIComplain",
]


def entry():
    fire.Fire(LKI)


if __name__ == "__main__":
    entry()
