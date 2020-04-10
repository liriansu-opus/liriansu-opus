#!/usr/bin/env python
import io
import os
import sys

home = os.path.expanduser("~")
config = os.path.join(home, ".gitconfig")

with io.open(config, "r") as f:
    lines = f.readlines()[1:]

aliases = []

for line in lines:
    if line.startswith("["):
        break
    alias = line.split("=", 1)[0].strip()
    aliases.append('alias g{alias}="git {alias}"\n'.format(alias=alias))

sys.stdout.writelines(aliases)
