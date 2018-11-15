# LKI's Conf - 我的配置脚本

[![Build Status][svg]][travis]

[我][me]的[开发环境是 Windows 系统][win-env]，
时常也会在 \*nix 系统上游荡，
本 repo 存了一些我常用的配置。

# Dev Environment 配置

* Unix 系统可以用 curl 命令一键安装：

```sh
    bash -c "$(curl -fsSL https://raw.githubusercontent.com/LKI/LKI/master/setup.sh)"
```

* Windows 系统

> Working on it...

# Server 配置

在 Server 上我不习惯引入过多配置，一般来说只会包括这么几个配置：

* git aliases
* tmux conf
* [vim-sensible][vim-sensible]

可以用以下命令一键安装：

```sh
    bash -c "$(curl -fsSL https://raw.githubusercontent.com/LKI/LKI/master/setup-lite.sh)"
```

[svg]: https://travis-ci.org/LKI/LKI.svg?branch=master
[travis]: https://travis-ci.org/LKI/LKI
[me]: http://www.liriansu.com/about
[win-env]: http://www.liriansu.com/windows-dev-env
[vim-sensible]: https://github.com/tpope/vim-sensible/

