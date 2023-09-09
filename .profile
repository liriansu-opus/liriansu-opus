#!/bin/bash
# Shell Style Guide: https://google.github.io/styleguide/shellguide.html

# enable vi mode
set -o vi

# helper functions
checkCMD () { command -v $@ &> /dev/null; }
checkRun () { checkCMD $1 && bash -c "$@"; }

# general aliases
alias ..="cd .."
alias bv="bumpversion"
alias conf="vim ~/.profile"
alias dp="env KUBECONFIG='' dapr"
alias la="ls -ah"
alias ll="ls -lh"
alias ln="lerna"
alias pt="poetry"
alias reload="source ~/.profile"
alias sk="skaffold"
alias sp="scoop"
alias st="stern --tail 200 --color=always"
alias ta="tmux attach"
alias wea="curl https://wttr.in/"
alias yn="yarn"

# conditional aliases
if checkCMD nvim; then
  alias vi="nvim"
  alias vim="nvim"
fi
if [[ "${OS}" == "Windows_NT" || -z "${OS}" ]]; then
  alias ls="/bin/ls --color"
fi

# general functions
update () {
  checkRun scoop update -a
  checkRun scoop cleanup -a
  git -C ~/.vim pull --rebase
  git -C ~/.lki pull --rebase
  checkRun python -m pip install -U pip setuptools wheel lki virtualenv pipenv black pynvim
  checkRun go install github.com/oligot/go-mod-upgrade@latest
  checkRun npm i -g npm
  checkRun brew update
}
ws () {
  WS=$(find ~/code/src -maxdepth 5 -type d -name .git | sed "s/\/.git//" | fzf -1 -0)
  cd "${WS}" || exit
  if test -f Pipfile; then
    if command -v pipenv &> /dev/null; then
      if [[ ! -z "${VIRTUAL_ENV}" ]]; then
        pipenv shell --fancy;
      fi
    fi
  fi
}
ggv() {
  PATTERN="${1}"
  shift
  if [[ -z "${PATTERN}" ]]; then
    exit 0
  fi
  FILES=$(git grep "${PATTERN}" | cut -d':' -f1 | sort | uniq | fzf -m -1 -0)
  if [[ -n "${FILES}" ]]; then
    vim $FILES
  fi
}

# datarc aliases
sshpm() { ssh -t "${1}" -- docker exec -it datarc_beat_1 pipenv run python manage.py shell; }
alias devpm="sshpm dev"
alias rcpm="sshpm rc"

# brew aliases
alias bi="brew install"
alias bic="brew install --cask"
alias br="brew"
alias bs="brew search"

# git aliases
alias frd="git f && git rd"
alias g="git"
alias gbad="git branch --list | grep -Ev '^\* ' | fzf -m -1 -0 | xargs -I {} git branch -D {}"
alias gc="git remote show | xargs -I{} git remote prune {} && git gc"
alias it="git"
alias lg="git logg"
alias lgs="git logs"
alias qgit="git"

# ackerr/lab aliases
alias lb="lab browser"
alias lc="lki clone"
alias lo="lab open -r o"
alias lop="lab open -r o --subpage pulls"

# node aliases
alias cnpm="npm --registry=https://registry.npm.taobao.org --cache=\${HOME}/.npm/.cache/cnpm --disturl=https://npm.taobao.org/dist --userconfig=\${HOME}/.cnpmrc"
alias nd="npm run dev"
alias nr="npm run"

# go aliases
alias gmt="go mod tidy"
alias gfm="go fmt"
alias gmu="go-mod-upgrade"  # https://github.com/oligot/go-mod-upgrade
alias gilo="go list -u -m -f '{{if not .Indirect}}{{.}}{{end}}' all"
gguv() { go get -u -v github.com/"${1}"; }

# python/pip/pipenv aliases
alias pf="pipenv run fab"
alias pi="python -m pip"
alias pii="python -m pip install"
alias piiu="python -m pip install -U"
alias pilo="python -m pip install -U pip black && python -m pip list --outdated"
alias pip="python -m pip"
alias pm="python manage.py"
alias pmt="python manage.py test"
alias ppm="pipenv run python manage.py"
alias pr="pipenv run"
alias psi="python setup.py install"
alias pv="pipenv"
alias pvs="pipenv shell --fancy"
alias pvsd="pipenv sync --dev && pipenv clean"
alias pvud="pipenv update --dev && pipenv clean"

alias jsonify="python -mjson.tool"

# make aliases
alias m="make"
alias mb="make build"
alias mf="make fmt"
alias ml="make lint"
alias mm="make migrations"
alias ms="make ensure"
alias mt="make test"

# docker aliases from tcnksm/docker-alias
alias d="docker"
alias dc="docker compose"
alias dex="docker exec -i -t"
alias di="docker images"
alias dip="docker inspect --format '{{ .NetworkSettings.IPAddress }}'"
alias dkd="docker run -d -P"
alias dki="docker run -i -t -P --rm"
alias dl="docker logs -f --tail=100"
alias dpa="docker ps -a"
alias dpq="docker ps -l -q"
alias dps="docker ps"
alias drminone="docker images | grep none | tr -s ' ' | cut -d' ' -f3 | xargs -I{} docker rmi {}"
alias dspf="docker system prune -f"
dalias() { alias | grep 'docker' | sed "s/^\([^=]*\)=\(.*\)/\1 => \2/"| sed "s/['|\']//g" | sort; }
dbash() { docker exec -it "$(docker ps -aqf "name=${1}")" bash; }
dbu() { docker build -t="${1}" .; }
dkiv() { MSYS_NO_PATHCONV=1 dki -v "$(pwd)":/app --workdir /app "$@"; }
dri() { docker rmi "$(docker images -q)"; }
drm() { docker rm "${1}"; }
drmf() { docker stop "${1}"; docker rm "${1}"; }
dsh() { docker exec -it "$(docker ps -aqf "name=${1}")" sh; }
dstop() { docker stop "$(docker ps -a -q)"; }

alias ts="dki soimort/translate-shell"
alias tz="ts :zh"

# kubectl aliases
alias k="kubectl"
alias kk="k9s"
alias kaf="kubectl apply -f"
alias kak="kubectl apply -k"
alias kc="kubectl config"
alias kd="kubectl describe"
alias kdel="kubectl delete"
alias ke="kubectl edit"
alias kex="kubectl exec -it"
alias kg="kubectl get"
alias kga="kubectl get all"
alias kgns="kubectl get ns"
alias km="kustomize"
alias kp="kapp"
alias kgpa="kubectl get pods -o wide -A"
alias kr="kubectl rollout"
alias krr="kubectl rollout restart"
alias krs="kubectl rollout status"
alias kt="kubectl top"
kbash() { kex "$(kpo "${1}")" -- bash; }
kpm() { kex "$(kpo "${1}")" -- python manage.py shell; }
kppm() { kex "$(kpo "${1}")" -- pipenv run python manage.py shell; }
kpo() { kg po | grep "${1}" | head -n1 | cut -d" " -f1; }
kpy() { kex "$(kpo "${1}")" -- python; }
ksh() { kex "$(kpo "${1}")" -- sh; }
ktl() { stern --tail 200 --color=always "${1}" | grep -Ev ' (200|201|202|204|301|302|304) '; }
kgp() {
  KEYWORD=${1}
  if [[ -z "${KEYWORD}" ]]; then
    kubectl get pods -o wide;
  else
    kubectl get pods -o wide | grep "${1}";
  fi
}
kcl() {
  CONTEXT=${1}
  if [[ -z "${CONTEXT}" ]]; then
    CURRENT=$(kc current-context)
    CONTEXT=$(kc get-contexts -o=name | fzf --height=20 --preview='kubectl config use-context {} && kubectl get ns' --preview-window=:75%)
    CONTEXT=${CONTEXT:-${CURRENT}}
  fi
  kubectl config use-context "${CONTEXT}" > /dev/null
}
kns() {
  NAMESPACE=${1}
  if [[ -z "${NAMESPACE}" ]]; then
    NAMESPACE=$(kg ns -o=name | sed 's/namespace\///' | fzf --height=50% --preview='kubectl get all -n {}' --preview-window=:70%)
  fi
  if [[ -n "${NAMESPACE}" ]]; then
    kubectl config set-context --current --namespace "${NAMESPACE}" > /dev/null
  fi
}
kl() {
  POD=${1}
  shift
  if [[ -z "${POD}" ]]; then
    POD=$(kg po -o=name | fzf --height=50% --preview='kubectl describe {}' --preview-window=:70%)
  fi
  if [[ -n "${POD}" ]]; then
    kubectl logs -f "${POD}" "$@"
  fi
}

# --- --- --- #

# set path
export PIPENV_VERBOSITY=-1
export BASH_SILENCE_DEPRECATION_WARNING=1
export EDITOR=vim
export LANG=en_US.UTF-8
export PATH=~/.lki/scripts:~/.pyenv/bin:${PATH}
export KUBECONFIG=~/.kube/config

# ssh aliases
gethost () {
  KEYWORD=${1}
  shift
  if [[ -z "${KEYWORD}" ]]; then
    cat ~/.ssh/*config | grep -e "^Host" | cut -c6- | sort "$@";
  else
    cat ~/.ssh/*config | grep -e "^Host" | cut -c6- | grep --color "${KEYWORD}" "$@";
  fi
}
gsh () {
  KEYWORD=${1}
  shift
  HOST=$(gethost "${KEYWORD}" | fzf -1 -0 | cut -d" " -f1)
  if [[ -n "${HOST}" ]]; then
    ssh -t "${HOST}" "$@";
  fi
}

# auto aliases  TODO: optimize speed
mkdir -p ~/.bash_aliases
if checkCMD python3; then
  python3 ~/.lki/scripts/git-to-bash.py > ~/.bash_aliases/git_aliases
  source ~/.bash_aliases/*_aliases
fi

## enable oh-my-posh
if checkCMD oh-my-posh; then
  eval "$(oh-my-posh init bash | sed 's|\[\[ -v MC_SID \]\]|[[ -n "$MC_SID" ]]|')"
fi

## enable pyenv
if checkCMD pyenv; then
  eval "$(pyenv init --path)"
fi

## enable nvm
if [ -d /opt/homebrew/opt/nvm ]; then
  export NVM_DIR=/opt/homebrew/opt/nvm
else
  export NVM_DIR="$([ -z "${XDG_CONFIG_HOME-}" ] && printf %s "${HOME}/.nvm" || printf %s "${XDG_CONFIG_HOME}/nvm")"
fi
[ -s "$NVM_DIR/nvm.sh" ] && \. "$NVM_DIR/nvm.sh" # This loads nvm
