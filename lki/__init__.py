import fire

from lki.exceptions import LKIComplain
from lki.fires import LKI

__version__ = "0.1.0"
__all__ = [
    "LKI",
    "LKIComplain",
]


def entry():
    fire.Fire(LKI)


if __name__ == "__main__":
    entry()
