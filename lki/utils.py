import distutils.spawn as spawn
import os

import lki


def check_executable(name: str):
    """ check if executable exists. (raise exeception if not) """
    if not spawn.find_executable(name):
        raise lki.LKIComplain('there is no {} executable'.format(name))


def check_file(path: str):
    """ check if file exists. (raise exeception if not) """
    if not os.path.exists(path):
        raise lki.LKIComplain('there is no {} file'.format(path))


def run(*commands: str):
    """ run commands """
    for command in commands:
        print('Executing {}'.format(command))
        os.system(command)
