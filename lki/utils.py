import ctypes
import os
import shutil
import sys

import click

from lki import error


def check_executable(name):
    """check if executable exists. (raise exeception if not)"""
    if not shutil.which(name):
        raise error.LKIError(f"there is no {name} executable")


def check_file(path):
    """check if file exists. (raise exeception if not)"""
    if not os.path.exists(path):
        raise error.LKIError(f"there is no {path} file")


def full_path(*paths):
    def _f(p):
        return os.path.abspath(os.path.expanduser(str(p)))

    if len(paths) == 1:
        return _f(paths[0])
    return map(_f, paths)


def is_superuser():
    if is_windows:
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    return os.getuid() == 0


is_windows = bool(sys.platform == "win32")


def make_link(target, link_path, force=False):
    error.LinkError.check(is_windows and not is_superuser(), "please run as admin to link files")

    target, link_path = full_path(target, link_path)
    if os.path.lexists(link_path):
        if force:
            rm(link_path)
        else:
            raise error.LinkError(f"{link_path} exists, specify --force to override.")

    kwargs = {}
    if is_windows and os.path.isdir(target):
        kwargs["target_is_directory"] = True
    os.symlink(target, link_path, **kwargs)


def rm(path):
    if os.path.isdir(path):
        os.rmdir(path)
    else:
        os.remove(path)


def run(*commands):
    """run commands"""
    for command in commands:
        click.echo(f"(Running)> {command}")
        os.system(command)
