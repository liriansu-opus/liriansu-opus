import datetime
import os
import pathlib
import re
import shutil
import sys

import click

from lki.utils import check_executable, check_file, is_windows, make_link, run

REGEX_GIT_URLS = (
    re.compile(r"^git@([^:]+):(.*?)(.git)?$"),
    re.compile(r"^https?://([^/]+)/(.*?)(.git)?$"),
    re.compile(r"^ssh://git@([^/]+)/(.*?)(.git)?$"),
)
HOME = pathlib.Path("~").expanduser()


@click.group()
def entry():
    """Lirian Su's useful configuration and shortcuts.
    This command will helps you swim through windows and unix,
    git and vim, docker and k8s, and all the fancy.

    See also: https://github.com/LKI/LKI"""


@entry.command()
def install():
    """install configuration to ~/.lki/

    Examples:
        lki install
    """
    check_executable("git")
    repo_path = HOME.joinpath(".lki")
    if not repo_path.exists():
        run(f"git clone -o o --recursive https://github.com/LKI/LKI.git {repo_path}")
    else:
        run(f"git -C {repo_path} pull --rebase")

    def _link(src, dst=None):
        target = HOME.joinpath(dst or src)
        if os.path.exists(target):
            os.remove(target)
        make_link(repo_path.joinpath(src), target, force=True)

    try:
        _link(".gitconfig")
        _link(".gitignore")
        _link(".ideavimrc")
        _link(".inputrc")
        _link(".profile")
        _link(".tmux.conf")
        if is_windows:
            _link(
                ".windows-terminal.json",
                "AppData/Local/Packages/Microsoft.WindowsTerminal_8wekyb3d8bbwe/LocalState/settings.json",
            )
        # TODO: implement `lki install --vim`
        # _link("dotvim/vimrc", ".vimrc")
        #
        # if IS_WIN32:
        #     _link("dotvim/vimrc", "_vimrc")
        #     _link("dotvim", "vimfiles", target_is_directory=True)
        #     _link("dotvim", ".vim", target_is_directory=True)
    except OSError as ex:
        click.echo(
            f"OSError: {ex}\n"
            "  Please check your permissions.\n"
            "Hint: windows requires admin permission when creating symlink.",
            err=True,
        )
        sys.exit(1)


@entry.command()
@click.argument("target")
@click.argument("link_path")
@click.option("-f", "--force", is_flag=True, default=False)
def link(target, link_path, force):
    """link target to link_path

    Examples:
        lki link /usr/bin/python3 /usr/bin/python
    """
    make_link(target, link_path, force=force)


@entry.command()
@click.argument("path", default=str(HOME.joinpath(".lki", ".pre-commit")))
@click.option("-f", "--force", is_flag=True, default=False)
def hook(path, force):
    """install git hook

    Examples:
        lki hook -f
    """
    make_link(path, ".git/hooks/pre-commit", force=force)


@entry.command()
@click.argument("key", required=False, default=None)
@click.argument("value", required=False, default=None)
def env(key, value):
    """list/grep/set environment variable (windows only)"""
    if not is_windows:
        click.echo("lki env only support windows currently", err=True)
        sys.exit(1)
    mute_keys = ("PS1", "_")
    data = {k.lower(): v for k, v in os.environ.items() if k not in mute_keys}
    if key is None:
        for k, v in data.items():
            click.echo(f"{k}={v}")
    elif value is None:
        if key.lower() in data:
            click.echo(data[key.lower()])
        else:
            for k, v in data.items():
                if key.lower() in k:
                    click.echo(f"{k}={v[:100]}")
    else:
        if not value:
            value = "''"
        click.echo(f"Setting environment {key} to {value}")
        run("SETX {} {}".format(key, value))


@entry.command()
@click.argument("url")
def clone(url):
    """clone a git repository to workspace

    Examples:
        lki clone git@github.com:zaihui/hutils.git
    Equals to:
        git clone -o o git@github.com:zaihui/hutils.git {workspace}/github.com/zaihui/hutils

    """
    check_executable("git")
    if not url.startswith("git@") and not url.startswith("http") and not url.startswith("ssh:"):
        if url.count("/") == 1:
            if HOME.joinpath(".ssh", "id_rsa").exists():
                url = f"git@github.com:{url}.git"
            else:
                url = f"https://github.com/{url}.git"
        else:
            url = "https://{}".format(url)
    match = next((m for m in (e.search(url) for e in REGEX_GIT_URLS) if m), None)
    if not match:
        click.echo(f"lki can not understand git url: {url}", err=True)
        sys.exit(1)
    domain, project, _ = match.groups()  # type: str
    domain = domain.split(":")[0]
    workspace = HOME.joinpath("code", "src")
    path = workspace.joinpath(domain, project)
    run(f"git clone -o o {url} {path}")


@entry.command()
def boost():
    """boost apt speed by changing apt's source

    translate from https://raw.githubusercontent.com/ldsink/toolbox/master/ubuntu-set-aliyun-mirror.sh
    """
    check_executable("apt")
    check_file("/etc/apt/sources.list")
    backup_file = datetime.datetime.now().strftime("/etc/apt/sources.list.%Y%m%d%H%M%S.bak")
    print("Backing up at {}".format(backup_file))
    shutil.copyfile("/etc/apt/sources.list", backup_file)
    run(
        r'sed -i -E "s/deb (ht|f)tp(s?)\:\/\/[0-9a-zA-Z]'
        r"([-.\w]*[0-9a-zA-Z])*(:(0-9)*)*(\/?)"
        r"([a-zA-Z0-9\-\.\?\,\'\/\\\+&amp;%\$#_]*)?\/ubuntu/deb"
        r' http\:\/\/mirrors\.aliyun\.com\/ubuntu/g" /etc/apt/sources.list'
    )


if __name__ == "__main__":
    entry()
