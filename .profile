# enable vi mode
set -o vi

# general aliases
alias ..="cd .."
alias cls="echo -e '\\0033c'"
alias cnpm="npm --registry=https://registry.npm.taobao.org --cache=${HOME}/.npm/.cache/cnpm --disturl=https://npm.taobao.org/dist --userconfig=${HOME}/.cnpmrc"
alias conf="vim ~/.profile"
alias la="/bin/ls -ah --color=auto 2>/dev/null"
alias ll="/bin/ls -lh --color=auto 2>/dev/null"
alias ls="/bin/ls --color=auto 2>/dev/null"
alias m="make"
alias n="npm"
alias please="sudo"
alias pp="popd"
alias pu="pushd"
alias py="winpty python"
alias reload="source ~/.profile"
alias sk="skaffold"
alias sp="scoop"
alias ta="tmux attach"
alias vi="vim"
alias ws="cd '$CODE'"
alias wsg="cd '$CODE'/github.com"
alias wsp="cd '$CODE'/pasta.zaihui.com.cn"

# git aliases
alias g="git"
alias gc="git remote show | xargs -I{} git remote prune {} && git gc"
alias it="git"
alias lg="git logg"
alias lgs="git logs"
alias qgit="git"

# go aliases
alias gmt="go mod tidy"
alias gfm="go fmt"
gguv() { go get -u -v github.com/$1; }

# python aliases
alias pm="python manage.py"
alias psi="python setup.py install"
alias bv="bumpversion"

# pip/pipenv aliases
alias pi="python -m pip"
alias pii="python -m pip install"
alias piiu="python -m pip install -U"
alias pilo="python -m pip list --outdated"
alias pv="pipenv"
alias pf="pipenv run fab"
alias ppm="pipenv run python manage.py"
alias pr="pipenv run"

# vagrant aliases
alias vgst="vagrant global-status"
alias vr="vagrant"
alias vst="vagrant status"
alias vu="vagrant up"

# docker aliases from tcnksm/docker-alias
alias d="docker"
alias dc="docker-compose"
alias dm="docker-machine"
alias dl="docker ps -l -q"
alias dps="docker ps"
alias dpa="docker ps -a"
alias di="docker images"
alias dip="docker inspect --format '{{ .NetworkSettings.IPAddress }}'"
alias dkd="docker run -d -P"
alias dki="docker run -i -t -P --rm"
alias dex="docker exec -i -t"
alias ts="dki soimort/translate-shell"
alias tz="ts :zh"
alias drminone="docker images | grep none | tr -s ' ' | cut -d' ' -f3 | xargs -I{} docker rmi {}"
dalias() { alias | grep 'docker' | sed "s/^\([^=]*\)=\(.*\)/\1 => \2/"| sed "s/['|\']//g" | sort; }
dstop() { docker stop $(docker ps -a -q); }
drm() { docker rm $1; }
drmf() { docker stop $1; docker rm $1; }
dri() { docker rmi $(docker images -q); }
dbu() { docker build -t=$1 .; }
dbash() { docker exec -it $(docker ps -aqf "name=$1") bash; }
dsr() { dki -v d:/Code/pasta.zaihui.com.cn/zaihui/server:/home/zaihui/server:ro docker-inter.zaihui.com.cn/zaihui/server/base:latest $@; }
dspm() { dsr python -W ignore::RuntimeWarning home/zaihui/server/ygg/manage.py $@; }
dst() { dspm test --failfast $@; }

# kubectl aliases
alias k="kubectl"
alias kaf="kubectl apply -f"
alias kak="kubectl apply -k"
alias kc="kubectl config"
alias kcl="kubectl config get-contexts"
alias kcns="kubectl config set-context --current --namespace"
alias kcu="kubectl config use-context"
alias kd="kubectl describe"
alias kdel="kubectl delete"
alias ke="kubectl edit"
alias kex="kubectl exec -it"
alias kg="kubectl get"
alias kga="kubectl get all"
alias kgns="kubectl get ns"
alias kgp="kubectl get pods -o wide"
alias kl="kubectl logs --tail=100"
alias km="kustomize"
alias kr="kubectl rollout"
alias krr="kubectl rollout restart"
alias krs="kubectl rollout status"
alias kt="kubectl top"
kpm() { kex `kpo $1` pipenv run python manage.py shell; }
kpo() { kg po | grep $1 | head -n1 | cut -d" " -f1; }

# --- --- --- #

# set path
export EDITOR=vim
export LANG=en
export PATH=/c/codeenv/git/usr/bin:~/.lki/scripts:${PATH}
export DOCKER_REGISTRY=docker-inter.zaihui.com.cn

# ssh aliases
alias gash='ssh -t awsgate ssh -t'
alias gethost='cat ~/.ssh/zaihui_ssh_config | grep -e "^Host" | grep --color'
alias gsh='ssh -t gate ssh -l zaihui -t'
alias stp='kcu stp && kex `kg po | grep worker | head -n1 | cut -d" " -f1` pipenv run python manage.py shell'
alias stt='kcu stt && kex `kg po | grep worker | head -n1 | cut -d" " -f1` pipenv run python manage.py shell'
alias svp='kcu ddp && kcns zaihui-main && kex `kpo prod-celerybeat-` python manage.py shell'

fsh() {
  IMAGE=${1}
  ssh -t gate ssh -l zaihui -t f1 docker exec -e ENV_TEST=1 -it ${IMAGE:="forseti_uwsgi"} pipenv run python manage.py shell
}

alias sv="cd /d/code/src/pasta.zaihui.com.cn"
alias svf="cd /d/code/src/pasta.zaihui.com.cn/stdev/forseti-be"
alias svl="cd /d/code/github.com/LKI/lki.github.io"

# auto aliases  TODO: optimize speed
mkdir -p ~/.bash_aliases
python ~/.lki/scripts/git-to-bash.py > ~/.bash_aliases/git_aliases
source ~/.bash_aliases/*_aliases
