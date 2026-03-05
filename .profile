# Shell Style Guide: https://google.github.io/styleguide/shellguide.html

# enable vi mode
set -o vi

# helper functions
checkCMD () { command -v "$1" > /dev/null 2>&1; }
checkRun () { checkCMD "$1" && "$@"; }
path_prepend () {
  case ":${PATH}:" in
    *":$1:"*) ;;
    *) PATH="$1${PATH:+:${PATH}}" ;;
  esac
}
ld_library_path_prepend () {
  case ":${LD_LIBRARY_PATH:-}:" in
    *":$1:"*) ;;
    *) LD_LIBRARY_PATH="$1${LD_LIBRARY_PATH:+:${LD_LIBRARY_PATH}}" ;;
  esac
}

# general aliases
alias ..="cd .."
alias bv="bumpversion"
alias cc="claude"
alias ccc="CLAUDE_CODE_USE_VERTEX=1 CLOUD_ML_REGION=global claude"
alias ccusage="npx -y ccusage@latest --since='20260101'"
alias conf="vim ~/.profile"
alias cx="codex --yolo"
alias cxusage="npx -y @ccusage/codex@latest --since='20260101'"
alias dp="env KUBECONFIG='' dapr"
alias gdate="date"
alias la="ls -ah"
alias ll="ls -lh"
alias pt="poetry"
alias reload="source ~/.profile"
alias sk="skaffold"
alias sp="scoop"
alias st="stern --tail 200 --color=always"
alias ta="tmux attach"
alias tf="terraform"
alias tsl="tailscale"
alias vk="HOST=0.0.0.0 PORT=20080 npx -y vibe-kanban@latest"
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
  checkRun scoop cache rm -a
  git -C ~/.vim pull --rebase
  git -C ~/.lki pull --rebase
  checkRun python -m pip install -U pip setuptools wheel lki virtualenv pipenv pynvim
  checkRun go install github.com/oligot/go-mod-upgrade@latest
  checkRun npm i -g npm
  checkRun brew update
  checkRun brew upgrade
}
ws () {
  WS=$(find ~/code/src -maxdepth 4 -name .git | sed "s/\/.git$//" | sort | fzf --exact --filter "$*" | fzf -1 -0)
  [ -z "${WS}" ] && return 0
  cd "${WS}" || return 1
}
ggv() {
  local PATTERN
  local -a FILES
  PATTERN="${1}"
  shift
  if [[ -z "${PATTERN}" ]]; then
    return 0
  fi
  mapfile -t FILES < <(git grep -- "${PATTERN}" | cut -d':' -f1 | sort -u | fzf -m -1 -0)
  if (( ${#FILES[@]} > 0 )); then
    vim -- "${FILES[@]}"
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
alias gbad="git branch --list | grep -Ev '^[*+] ' | fzf -m -1 -0 | xargs -I {} git branch -D {} && git worktree list | grep 'detached HEAD' | xargs -I {} git worktree remove {} --force"
alias gcr="gf && gbr -r | grep -E 'lirian[-/]' | sed 's#origin/##' | awk '{\$1=\$1};1' | fzf | xargs -I{} bash -c 'git checkout {} && git reset --hard origin/{}'"
alias ghb="gh browse"
alias ghpc="gpd && gh pr create -f && ghpr"
alias ghpr="gh pr view -w"
alias gof="git log --all --pretty=format:'%Cred%h%Creset -%C(yellow)%d%Creset %s %Cgreen(%cr) %C(bold blue)<%an>%Creset' --abbrev-commit --date=relative --color=always | head -n 1000 | fzf --ansi --no-sort --preview 'git show {1} --color=always' --preview-window=:wrap | cut -d' ' -f1"
alias it="git"
alias lg="git logg"
alias lgs="git logs"
alias qgit="git"
gwta() { git fetch origin main && mkdir -p ~/code/src/worktrees && git worktree add -b lirian/$1 ~/code/src/worktrees/$1 origin/main; }
gwtd() {
  local selected WT_PATH WT_BRANCH

  selected="$(git worktree list --porcelain | awk '
    /^worktree / { path = substr($0, 10) }
    /^branch / {
      branch = substr($0, 8)
      sub("^refs/heads/", "", branch)
      print path "\t" branch
    }
  ' | fzf -1 -0 --delimiter=$'\t' --with-nth=2,1 --prompt='worktree> ')"

  [ -z "${selected}" ] && return 0

  WT_PATH="${selected%%$'\t'*}"
  WT_BRANCH="${selected#*$'\t'}"

  git worktree remove "${WT_PATH}" --force && git branch -D "${WT_BRANCH}"
}

# gcloud aliases
alias gc="gcloud"
alias gcp="gcloud projects"

# ackerr/lab aliases
alias lb="lab browser"
alias lc="lki clone"
alias lo="lab open -r o"
alias lop="lab open -r o --subpage pulls"

# node aliases
alias nd="npm run dev"
alias nr="npm run"
alias nci="npm clean-install"

# nx aliases
alias nxd="nx dev"

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
alias kgp="kubectl get pods"
alias kgpa="kubectl get pods -A"
alias km="kustomize"
alias kp="kapp"
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
kcl() {
  CONTEXT=${1}
  if [[ -z "${CONTEXT}" ]]; then
    CURRENT=$(kc current-context)
    CONTEXT=$(kc get-contexts -o=name | fzf --height=20 --preview='kubectl --context {} get ns' --preview-window=:75%)
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
export BASH_SILENCE_DEPRECATION_WARNING=1
export EDITOR=vim
export KUBECONFIG="${HOME}/.kube/config"
export LANG="en_US.UTF-8"
ld_library_path_prepend "/usr/lib/wsl/lib"
path_prepend "${HOME}/.lki/scripts"
path_prepend "${HOME}/.pyenv/bin"
path_prepend "${HOME}/.local/bin"
path_prepend "${HOME}/.temporalio/bin"
export LD_LIBRARY_PATH
export PATH
export PIPENV_VERBOSITY=-1
export UV_NATIVE_TLS=true

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
csh () {
  KEYWORD=${1}
  shift
  HOST=$(gethost "${KEYWORD}" | fzf -1 -0 | cut -d" " -f1)
  if [[ -n "${HOST}" ]]; then
    ssh -t "${HOST}" "$@";
  fi
}

# auto aliases: pre-generated by .githooks/pre-commit
source ~/.lki/scripts/git_aliases.bash

## enable oh-my-posh
if checkCMD oh-my-posh; then
  eval "$(oh-my-posh init bash --config ~/.lki/.oh-my-posh.json | sed 's|\[\[ -v MC_SID \]\]|[[ -n "$MC_SID" ]]|')"
fi

## enable pyenv
if checkCMD pyenv; then
  eval "$(pyenv init -)"
fi

## enable nvm
if [ -d /opt/homebrew/opt/nvm ]; then
  export NVM_DIR=/opt/homebrew/opt/nvm
else
  export NVM_DIR="$([ -z "${XDG_CONFIG_HOME-}" ] && printf %s "${HOME}/.nvm" || printf %s "${XDG_CONFIG_HOME}/nvm")"
fi
[ -s "$NVM_DIR/nvm.sh" ] && \. "$NVM_DIR/nvm.sh" || true

## auto-switch node version on cd
_nvm_auto_use() {
  local nvmrc_path
  nvmrc_path="$(nvm_find_nvmrc 2>/dev/null)"
  if [ -n "$nvmrc_path" ]; then
    local nvmrc_node_version
    nvmrc_node_version=$(nvm version "$(cat "$nvmrc_path")")
    if [ "$nvmrc_node_version" = "N/A" ]; then
      nvm install
    elif [ "$nvmrc_node_version" != "$(nvm version)" ]; then
      nvm use
    fi
  elif [ -n "$(PWD=$OLDPWD nvm_find_nvmrc 2>/dev/null)" ] && [ "$(nvm version)" != "$(nvm version default)" ]; then
    nvm use default
  fi
}
if checkCMD nvm; then
  _nvm_auto_use
  cd() { builtin cd "$@" && { type _nvm_auto_use >/dev/null 2>&1 && _nvm_auto_use || true; }; }
fi

# --- WSL2 Proxy Auto Config ---
if grep -qi microsoft /proc/version 2>/dev/null; then
  WSL_HOST=$(ip route | awk '/default/ {print $3}')
  WSL_PROXY_PORT=3067
  WSL_PROXY_UP=0

  if [[ -n "${WSL_HOST}" ]]; then
    if checkCMD timeout; then
      timeout 0.2 bash -c ">/dev/tcp/${WSL_HOST}/${WSL_PROXY_PORT}" 2>/dev/null && WSL_PROXY_UP=1
    else
      nc -z -w1 "${WSL_HOST}" "${WSL_PROXY_PORT}" 2>/dev/null && WSL_PROXY_UP=1
    fi
  fi

  if [[ "${WSL_PROXY_UP}" -eq 1 ]]; then
    export HTTP_PROXY="http://${WSL_HOST}:${WSL_PROXY_PORT}"
    export HTTPS_PROXY="http://${WSL_HOST}:${WSL_PROXY_PORT}"
    export ALL_PROXY="socks5://${WSL_HOST}:${WSL_PROXY_PORT}"
    export NO_PROXY=localhost,127.0.0.1
    export WSL_PROXY_ENABLED=1
  else
    unset HTTP_PROXY HTTPS_PROXY ALL_PROXY
    export WSL_PROXY_ENABLED=0
  fi
fi
