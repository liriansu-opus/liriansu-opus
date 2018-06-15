#!/usr/bin/env bash
# a setup script to initialize a lite environment

set -e

echo "installing"
curl -fsSL https://raw.githubusercontent.com/LKI/myconf/master/.tmux.conf > ~/.tmux.conf
curl -fsSL https://raw.githubusercontent.com/LKI/myconf/master/.gitconfig | head -n -3 > ~/.gitconfig
curl -fsSL https://raw.githubusercontent.com/tpope/vim-sensible/master/plugin/sensible.vim > ~/.vimrc
echo "done"
