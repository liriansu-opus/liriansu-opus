import datetime
import os
import re
import shutil
import sys

from lki.config import LKIConfig
from lki.error import LKIError
from lki.utils import check_executable, check_file, link, run

REGEX_GIT_URLS = (
    re.compile(r"^git@([^:]+):(.*?)(.git)?$"),
    re.compile(r"^http[s]?://([^/]+)/(.*?)(.git)?$"),
)
HOME = os.path.expanduser("~")
IS_WIN32 = sys.platform == "win32"


class Command:  # base command class
    def __str__(self):
        return self.__class__.__doc__.strip()


class LKI(Command):
    """ Lirian Su's useful configuration and shortcuts.
    This command will helps you swim through windows and unix,
    git and vim, docker and k8s, and all the fancy.

    See also: https://github.com/LKI/LKI """

    def __init__(self):
        self._config = LKIConfig()
        self.op = Operation()

    def install(self):
        """ install configuration to ~/.lki/

        Examples:
            lki install
        """
        check_executable("git")
        repo_path = os.path.join(HOME, ".lki")
        if not os.path.exists(repo_path):
            run("git clone -o o --recursive https://github.com/LKI/LKI.git {}".format(repo_path))
        else:
            run("git -C {} pull --rebase".format(repo_path))

        def _link(src, dst=None, **kwargs):
            target = os.path.join(HOME, dst or src)
            if os.path.exists(target):
                os.remove(target)
            link(os.path.join(repo_path, src), target, force=True)

        try:
            _link(".gitconfig")
            _link(".gitignore")
            _link(".ideavimrc")
            _link(".profile")
            _link(".tmux.conf")
            # TODO: implement `lki install --vim`
            # _link("dotvim/vimrc", ".vimrc")
            #
            # if IS_WIN32:
            #     _link("dotvim/vimrc", "_vimrc")
            #     _link("dotvim", "vimfiles", target_is_directory=True)
            #     _link("dotvim", ".vim", target_is_directory=True)
        except OSError as ex:
            sys.stderr.writelines(
                [
                    "OSError: {}".format(ex),
                    "  Please check your permissions.",
                    "Hint: windows requires admin permission when creating symlink.",
                ]
            )
            sys.exit(1)

    def clone(self, url):
        """ clone a git repository to workspace

        Examples:
            lki clone git@github.com:zaihui/hutils.git
        Equals to:
            git clone -o o git@github.com:zaihui/hutils.git {workspace}/github.com/zaihui/hutils

        """
        check_executable("git")
        if not url.startswith("git@") and not url.startswith("http"):
            if url.count("/") == 1:
                if os.path.exists("{}/.ssh/id_rsa".format(HOME)):
                    url = "git@github.com:{}.git".format(url)
                else:
                    url = "https://github.com/{}.git".format(url)
            else:
                url = "https://{}".format(url)
        match = next((m for m in (e.search(url) for e in REGEX_GIT_URLS) if m), None)
        if not match:
            raise LKIError("lki can not understand git url: {}".format(url))
        domain, project, _ = match.groups()  # type: str
        workspace = self._config.get("workspace", ".")
        path = os.path.join(workspace, domain, project)
        try:
            os.makedirs(os.path.dirname(path))
        except OSError:
            pass
        run("git clone -o o {} {}".format(url, path))
        for key, value in self._config.get(domain, {}).items():
            run("git -C {} config {} {}".format(path, key, value))

    def hook(self, force=False, path="{}/.lki/.pre-commit.sh".format(HOME)):
        """ install git hook """
        link(path, ".git/hooks/pre-commit", force=force)

    def link(self, target, link_path, force=False):
        """ link target to link_path """
        link(target, link_path, force=force)

    def set_workspace(self, path):
        """ set your workspace, where lki clones repositories into """
        if not os.path.isdir(path):
            raise LKIError("lki thinks this is not a directory: {}".format(path))
        self._config["workspace"] = path

    def set_git_config(self, domain, **kwargs):
        """ set your domain specific configurations. user.name/user.email for example """
        domain_config = self._config.get(domain, {})
        domain_config.update(**kwargs)
        self._config[domain] = domain_config


class Operation(Command):
    """ collections of various operation commands """

    def boost_apt(self):
        """ boost apt speed by changing apt's source

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

    def update_apt(self):
        """ perform apt update """
        check_executable("apt")
        run("apt update", "apt upgrade --auto-remove -y")
