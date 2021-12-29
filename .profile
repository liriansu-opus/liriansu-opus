# enable vi mode
set -o vi

if [[ "${OS}" == "Windows_NT" ]]; then
  alias ls="/bin/ls --color"
fi

# general aliases
alias ..="cd .."
alias bv="bumpversion"
alias cnpm="npm --registry=https://registry.npm.taobao.org --cache=${HOME}/.npm/.cache/cnpm --disturl=https://npm.taobao.org/dist --userconfig=${HOME}/.cnpmrc"
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
alias vi="nvim"
alias vim="nvim"
alias wea="curl https://wttr.in/"
alias ws='cd $(lab ws 2>&1) && git fetch'
alias yn="yarn"
update () {
  scoop update '*'
  scoop cleanup '*'
  git -C ~/.vim pull --rebase
  git -C ~/.lki pull --rebase
  python -m pip install -U pip setuptools wheel lki virtualenv pipenv black
  go install github.com/oligot/go-mod-upgrade@latest
}

# brew aliases
alias bc="brew cask"
alias bi="brew install"

# zeus aliases
alias z="docker exec -i -t zeus zeus"

# git aliases
alias frd="git f && git rd"
alias g="git"
alias gc="git remote show | xargs -I{} git remote prune {} && git gc"
alias it="git"
alias lg="git logg"
alias lgs="git logs"
alias qgit="git"

# ackerr/lab aliases
alias lb="lab browser"
alias lc="lab clone"
alias li="lab ci -r o"
alias lia="lab ci -b alpha-only -r o"
alias lo="lab open -r o -p"

# go aliases
alias gmt="go mod tidy"
alias gfm="go fmt"
alias gmu="go-mod-upgrade"  # https://github.com/oligot/go-mod-upgrade
alias gilo="go list -u -m -f '{{if not .Indirect}}{{.}}{{end}}' all"
gguv() { go get -u -v github.com/$1; }

# python/pip/pipenv aliases
alias pf="pipenv run fab"
alias pi="python -m pip"
alias pii="python -m pip install"
alias piiu="python -m pip install -U"
alias pilo="python -m pip install -U pip setuptools wheel black && python -m pip list --outdated"
alias pip="python -m pip"
alias pm="python manage.py"
alias ppm="pipenv run python manage.py"
alias pr="pipenv run"
alias psi="python setup.py install"
alias pv="pipenv"
alias pvsd="pipenv sync --dev"
alias pvud="pipenv update --dev && pipenv clean"

alias jsonify="python -mjson.tool"

# make aliases
alias m="make"
alias mb="make build"
alias mf="make fmt"
alias mm="make migrations"
alias ms="make ensure"
alias mt="make test"

# docker aliases from tcnksm/docker-alias
alias d="docker"
alias dc="docker-compose"
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
dbash() { docker exec -it $(docker ps -aqf "name=$1") bash; }
dbu() { docker build -t=$1 .; }
dkiv() { MSYS_NO_PATHCONV=1 dki -v $(pwd):/app --workdir /app $@; }
dri() { docker rmi $(docker images -q); }
drm() { docker rm $1; }
drmf() { docker stop $1; docker rm $1; }
dspm() { dsr python -W ignore::RuntimeWarning home/zaihui/server/ygg/manage.py $@; }
dsr() { dki -v d:/Code/pasta.zaihui.com.cn/zaihui/server:/home/zaihui/server:ro docker-inter.zaihui.com.cn/zaihui/server/base:latest $@; }
dst() { dspm test --failfast $@; }
dstop() { docker stop $(docker ps -a -q); }

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
kbash() { kex `kpo $1` -- bash; }
kpm() { kex `kpo $1` -- python manage.py shell; }
kpo() { kg po | grep $1 | grep Running | head -n1 | cut -d" " -f1; }
kpy() { kex `kpo $1` -- python; }
ksh() { kex `kpo $1` -- sh; }
ktl() { stern --tail 200 --color=always $1 | grep -Ev ' (200|201|202|204|301|302|304) '; }
kgp() {
  KEYWORD=${1}
  if [[ -z "${KEYWORD}" ]]; then
    kubectl get pods -o wide;
  else
    kubectl get pods -o wide | grep ${1};
  fi
}
kcl() {
  CONTEXT=${1}
  if [[ -z "${CONTEXT}" ]]; then
    CURRENT=`kc current-context`
    CONTEXT=$(kc get-contexts -o=name | fzf --height=20 --preview='kubectl config use-context {} && kubectl get ns' --preview-window=:75%)
    CONTEXT=${CONTEXT:-${CURRENT}}
  fi
  kubectl config use-context ${CONTEXT} > /dev/null
}
kns() {
  NAMESPACE=${1}
  if [[ -z "${NAMESPACE}" ]]; then
    NAMESPACE=$(kg ns -o=name | sed 's/namespace\///' | fzf --height=50% --preview='kubectl get all -n {}' --preview-window=:70%)
  fi
  if [[ ! -z "${NAMESPACE}" ]]; then
    kubectl config set-context --current --namespace ${NAMESPACE} > /dev/null
  fi
}
kl() {
  POD=${1}
  if [[ -z "${POD}" ]]; then
    POD=$(kg po -o=name | fzf --height=50% --preview='kubectl describe {}' --preview-window=:70%)
  fi
  if [[ ! -z "${POD}" ]]; then
    kubectl logs -f ${POD}
  fi
}

# --- --- --- #

# set path
export PIPENV_VERBOSITY=-1
export BASH_SILENCE_DEPRECATION_WARNING=1
export EDITOR=vim
export LANG=en_US.UTF-8
export PATH=~/.lki/scripts:${PATH}
export DOCKER_REGISTRY=docker-inter.zaihui.com.cn
export KUBECONFIG=~/.kube/config

# ssh aliases
alias gethost='cat ~/.ssh/*_config | grep -e "^Host" | grep --color'
alias gsh='z gsh'

# auto aliases  TODO: optimize speed
mkdir -p ~/.bash_aliases
python ~/.lki/scripts/git-to-bash.py > ~/.bash_aliases/git_aliases
source ~/.bash_aliases/*_aliases

if command -v starship &> /dev/null;
then
  eval "$(starship init bash)"
fi

if command -v pyenv &> /dev/null;
then
  eval "$(pyenv init -)"
fi

