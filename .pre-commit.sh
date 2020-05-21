#!/usr/bin/env bash
# this pre-commit hook will run several checkings
# go for a coffee if it's committing
#
# Install (*nix):
#   ln -sf ~/.pre-commit.sh .git/hooks/pre-commit
# Install (Windows):
#   mklink .git\hooks\pre-commit C:\Users\liriansu\.pre-commit.sh
set -e

# /dev/null not work on Windows
VENV="`pipenv --venv 2>&1 || true`"

if [[ ${VENV} =~ "Aborted" ]];
then
  exit 0;
fi

# get changed (modified + staged) python files
PYTHON_FILES="`git diff --name-only --diff-filter=AMR HEAD | grep --color=never '.py$' || true`"

# do nothing if no python file
if [[ ! "${PYTHON_FILES}" ]];
then
  exit 0
fi

if [[ ! -z "`pipenv run pip list | grep '^isort '`" ]];
then
  echo 'Running isort...'
  pipenv run isort -up -y ${PYTHON_FILES}
  git add ${PYTHON_FILES}
fi

if [[ ! -z "`pipenv run pip list | grep '^yapf '`" ]];
then
  echo 'Running yapf...'
  pipenv run yapf -i -r ${PYTHON_FILES}
  git add ${PYTHON_FILES}
fi

if [[ ! -z "`pipenv run pip list | grep '^black '`" ]];
then
  echo 'Running black...'
  pipenv run black -l 120 ${PYTHON_FILES}
  git add ${PYTHON_FILES}
fi

if [[ ! -z "`pipenv run pip list | grep '^flake8 '`" ]];
then
  echo 'Running flake8...'
  pipenv run flake8 ${PYTHON_FILES}
fi

PYLINT_FILES="`git diff --name-only --diff-filter=AMR HEAD | grep --color=never '.py$' | grep -v migrations || true`"

# do nothing if no pylint file
if [ ! "${PYLINT_FILES}" ]; then
  exit 0
fi

if [[ ! -z "`pipenv run pip list | grep '^pylint '`" ]];
then
  echo 'Running pylint...'
  pipenv run pylint ${PYLINT_FILES}
fi

exit 0
