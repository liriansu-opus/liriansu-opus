# Lirian Su's Configuration

[![Build Status][badge-build]][github]

Hello, [I'm Lirian Su][me]. I work primarily on macOS these days, and frequently on Unix systems too (cloud servers or WSL). Because I set up new environments so often, I keep this project to sync my various configurations across every machine I touch.

This repo happens to share my GitHub username, so GitHub also renders its README as my profile page. If you'd like to know more about me, feel free to read [my introduction][me].


## Configuration Style

I'm lazy and primarily drive everything through shortcuts and hotkeys. This project defines numerous abbreviations, but the changes are purely additive — they don't alter any existing command habits.

Configurations live in `~/.lki` and are linked into each application's config directory.


## Setup

Clone this repository once (keep an existing `~/.lki` checkout):

```bash
git clone https://github.com/liriansu-opus/liriansu-opus.git ~/.lki
git -C ~/.lki config core.hooksPath .githooks
```

On macOS or Linux/WSL, back up any existing destination files, then link the configurations you want. These commands deliberately refuse to overwrite existing files:

```bash
for file in .gitconfig .gitignore .inputrc .profile .tmux.conf; do
  ln -s "$HOME/.lki/$file" "$HOME/$file"
done
mkdir -p ~/.claude
for file in settings.json CLAUDE.md RTK.md; do
  ln -s "$HOME/.lki/claude/$file" "$HOME/.claude/$file"
done
```

The shell configuration targets Bash. Ensure your interactive Bash startup file sources `~/.profile`; put machine-specific overrides in `~/.profile.local`.

For cmux on macOS:

```bash
mkdir -p ~/.config/ghostty ~/.config/cmux
ln -s ~/.lki/ghostty/config.ghostty ~/.config/ghostty/config
ln -s ~/.lki/cmux/cmux.json ~/.config/cmux/cmux.json
```

On native Windows, copy `.windows-terminal.json` into Windows Terminal's settings file (open it from Terminal settings). Use the Bash setup above inside WSL.

Update configurations with `git -C ~/.lki pull --rebase`. Existing symlinks continue to work. The former Python CLI and PyPI release workflow have been retired; uninstall an old pip installation with `python -m pip uninstall lki`. Use `git clone` and `ln -s` directly in place of its clone/link commands.

## Development

Run `make lint` (requires uv) and `make test` (Python 3.12+). Python is used for the cmux helpers, with no installable package or third-party runtime dependencies. See [cmux maintenance notes](cmux/README.md) for lifecycle and diagnostic details.


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
$ g st           # `git status`
$ reload         # re-source ~/.profile after an edit
$ pv sync --dev  # `pipenv sync --dev`

# Compound subcommand abbreviations
$ dpa  # `docker ps -a`
$ kgp  # `kubectl get pods`
$ gcm  # `git cm`

# fzf-powered helpers that I reach for constantly
$ ws <keyword>    # jump into a matching repo under ~/code/src
$ csh <host>      # ssh into a matching host from ~/.ssh/*config
$ kbash <pod>     # exec bash into a matching k8s pod
```

> For Vim configuration, see another project [liriansu-opus/dotvim][dotvim]

There's much more in this project, but the margin here is too small to contain it all. XD


## License

[Permissive MIT License][license], meaning you can make any changes — even change the author name to your own.


## Questions?

No worries — whether it's about the project or about me personally, or if you think a certain command isn't friendly enough, feel free to [submit an Issue directly in the project][issue].


[badge-build]: https://github.com/liriansu-opus/liriansu-opus/actions/workflows/build.yml/badge.svg
[dotvim]: https://github.com/liriansu-opus/dotvim
[github]: https://github.com/liriansu-opus/liriansu-opus
[issue]: https://github.com/liriansu-opus/liriansu-opus/issues/new
[license]: https://github.com/liriansu-opus/liriansu-opus/blob/HEAD/LICENSE
[me]: https://www.liriansu.com/about
