# Lirian Su(LKI)'s Configuration, 我的配置

[![Build Status][badge-build]][github] [![PyPI][badge-pypi]][pypi] [![PyPI][badge-version]][pypi]

[我][me]的[开发环境是 Windows 系统][win-env]，
但我也时常会在 Unix 系统上游荡。
因为经常折腾环境，
所以我专门开了一个项目来同步我的各类配置。


## 配置风格

我很懒，
我的大部分命令都是各种缩写。
但这些改动都是附加项，
不会变动原有的任何命令习惯。

不过 :)
我的环境里，`python` 是必选项噢。


## 快速安装

首先，确保环境中有 Python 3.5+，然后使用 `pip` 快速安装：

```
pip install lki && lki install
```

> 本命令同时支持 Unix, MacOS, Windows 环境
> 发现有问题就[给我报 Issue][issue]


## 使用指南

> [~/.gitconfig](/.gitconfig) 中包含了大量的 git alias：

``` bash
# 查看 git 配置
$ cat ~/.gitconfig

# git 的基础缩写
$ git ci  # `git commit`
$ git br  # `git branch`
$ git pf  # `git push -f`
$ git sv  # `git save` <=> `git stash`
$ git ld  # `git load` <=> `git stash pop`

# git 的常用缩写
$ git cm    # amend last commit
$ git logg  # log ing graph
$ git pd    # push dev with gitlab merge request created
$ git yes   # show what happened yesterday
```

> [~/.profile](/.profile) 中包含了大量的 bash alias：
``` bash
# 查看 bash 配置
$ cat ~/.profile

# 常用缩写
$ please visudo  # `sudo visudo`
$ g st  # `git status`
$ pv sync --dev  # `pipenv sync --dev`

# 子命令复合缩写
$ dpa  # `docker ps -a`
$ kgp  # `kubectl get pods`
$ gcm  # `git cm`
$ gsh  # ssh through gate

# 个人向的，你们用不上的缩写
# 我写这就是给你们看看我平常跑那些命令
$ svl  # go into my blog repo
$ dspm test  # run django test for zaihui/server project
$ stp  # exec bash into k8s cluster
```

> Vim 的配置，参见另外一个项目 [LKI/dotvim][dotvim]

关于本项目的功能还有很多，
但是这里的空白太少我写不下了 XD


## 开源协议

[宽松的 MIT License][license],
意味着你可以做任何更改，
甚至把作者名都改成你。


## 我有问题要问

没关系，不论是对项目的问题还是对我个人的问题，
或者是你觉得哪条命令不够好用，
都欢迎[来项目里直接提 Issue。][issue]


[badge-build]: https://github.com/LKI/LKI/workflows/Build/badge.svg
[badge-pypi]: https://img.shields.io/pypi/v/lki.svg
[badge-version]: https://img.shields.io/pypi/pyversions/LKI.svg
[dotvim]: https://github.com/LKI/dotvim
[github]: https://github.com/LKI/LKI
[issue]: https://github.com/LKI/LKI/issues/new
[license]: https://github.com/LKI/LKI/blob/master/LICENSE
[me]: https://www.liriansu.com/about
[pypi]: https://pypi.python.org/pypi/lki
[win-env]: https://www.liriansu.com/windows-dev-env
