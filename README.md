# Lirian Su (LKI)'s Configuration

[![Build Status][badge-build]][github] [![PyPI][badge-pypi]][pypi] [![PyPI][badge-version]][pypi]

Hello, [I'm Lirian Su][me].
My [development environment is Windows][win-env],
but I also frequently work on Unix systems (cloud servers or WSL).
Since I often set up new environments,
I created a dedicated project to sync my various configurations.
Coincidentally, this project called [LKI][github] was later treated by GitHub as my self-introduction profile repository.
If you're interested in learning more about me, feel free to read [my introduction][me].


## Configuration Style

I'm lazy and primarily use various shortcuts and hotkeys to execute commands.
This project contains numerous abbreviations,
but these changes are purely additive and don't alter existing command habits.

For convenient installation,
I've written the configuration installation process as Python scripts.
(So the first thing I do when I get a new computer is install a Python environment.)


## Quick Installation

First, ensure you have Python 3.12+ in your environment, then use `pip` for quick installation:

```
pip install lki && lki install
```

> This command supports Unix, MacOS, and Windows environments.
> If you encounter any issues, please [report them as an Issue][issue].


## macOS Packages

On a new Mac, after installing [Homebrew](https://brew.sh), restore every tap, formula, and cask from the committed [Brewfile](./Brewfile) with `brew bundle --file ~/.lki/Brewfile`. After installing new packages, refresh the list with `brew bundle dump --file ~/.lki/Brewfile --force`.


## Usage Guide

> [~/.gitconfig](./.gitconfig) contains numerous git aliases:

``` bash
# View git configuration
$ cat ~/.gitconfig

# Basic git abbreviations
$ git ci  # `git commit`
$ git br  # `git branch`
$ git pf  # `git push -f`
$ git sv  # `git save` <=> `git stash`
$ git ld  # `git load` <=> `git stash pop`

# Common git abbreviations
$ git cm    # amend last commit
$ git logg  # log in graph
$ git pd    # push dev with gitlab merge request created
$ git yes   # show what happened yesterday
```

> [~/.profile](./.profile) contains numerous bash aliases:
``` bash
# View bash configuration
$ cat ~/.profile

# Common abbreviations
$ please visudo  # `sudo visudo`
$ g st  # `git status`
$ pv sync --dev  # `pipenv sync --dev`

# Compound subcommand abbreviations
$ dpa  # `docker ps -a`
$ kgp  # `kubectl get pods`
$ gcm  # `git cm`
$ gsh  # ssh through gate

# Personal shortcuts that you might not need
# I'm just showing you what commands I commonly run
$ svl  # go into my blog repo
$ dspm test  # run django test for zaihui/server project
$ stp  # exec bash into k8s cluster
```

> For Vim configuration, see another project [liriansu-opus/dotvim][dotvim]

There's much more functionality in this project,
but the margin here is too small to contain it all. XD


## License

[Permissive MIT License][license],
meaning you can make any changes,
even change the author name to yours.


## Questions?

No worries, whether it's questions about the project or about me personally,
or if you think a certain command isn't user-friendly enough,
feel free to [submit an Issue directly in the project.][issue]


[badge-build]: https://github.com/liriansu-opus/liriansu-opus/actions/workflows/build.yml/badge.svg
[badge-pypi]: https://img.shields.io/pypi/v/lki.svg
[badge-version]: https://img.shields.io/pypi/pyversions/lki.svg
[dotvim]: https://github.com/liriansu-opus/dotvim
[github]: https://github.com/liriansu-opus/liriansu-opus
[issue]: https://github.com/liriansu-opus/liriansu-opus/issues/new
[license]: https://github.com/liriansu-opus/liriansu-opus/blob/HEAD/LICENSE
[me]: https://www.liriansu.com/about
[pypi]: https://pypi.org/project/lki/
[win-env]: https://www.liriansu.com/windows-dev-env
