#!/usr/bin/env python
import os
import sys

home = os.path.expanduser("~")
config = os.path.join(home, ".gitconfig")

with open(config) as f:
    lines = f.readlines()[1:]

aliases = []

for line in lines:
    if line.startswith("["):
        break
    alias = line.split("=", 1)[0].strip()
    aliases.append(f'alias g{alias}="git {alias}"\n')

sys.stdout.writelines(aliases)
