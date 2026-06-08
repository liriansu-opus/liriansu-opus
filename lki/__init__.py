from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("lki")
except PackageNotFoundError:  # running from a raw checkout without an install
    __version__ = "0.0.0+unknown"
