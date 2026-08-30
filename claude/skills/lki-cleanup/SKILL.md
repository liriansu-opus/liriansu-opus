---
name: lki-cleanup
description: Use when doing routine cleanup on this Mac — orphaned dev processes holding ports, zombie background servers from old debug sessions, stale Docker volumes/images, bloated package-manager caches, Colima memory/disk growth, or leftover AI-agent runtime caches. Triggers on "日常清理", "清理电脑", "端口被占用", "磁盘满了", "内存不够", "swap 爆了".
---

# Mac 日常清理

## 核心前提

**我正在用的进程都在 cmux 里。** 这是整个 skill 的判据基础：一个进程的祖先链走到 `cmux` 就是活的，走到 `launchd` (PID 1) 就是孤儿 —— 启动它的终端早已消失，没人再看它的输出，它却还在占端口、吃内存。

先诊断，再动手。诊断阶段全部只读，跑 `./diagnose.sh` 一次拿到全貌。

## 绝不动的东西

- cmux 树下的任何进程（`claude`、`codex`、编辑器、dev server）
- **Cloudflare WARP** —— 断开会切断和 Claude 的 API 连接
- `tailscaled`（如果在跑，注意它需要 `--tun=userspace-networking` 才能和 WARP 共存）
- `~/Downloads`、`~/Documents` 等用户文件
- 任何还有活跃进程持有锁的缓存目录

## 判断孤儿的三个信号

强度递减，命中任意一个就值得清：

1. **工作目录已被删除** —— worktree/项目目录没了进程还在跑。铁证。
2. **祖先链走到 launchd** —— 且进程是 dev 工具（`make`、`uv run`、`npm run`、`port-forward`）。
3. **运行时长以「天」计** —— 配合上面两条看，单独出现不足以定罪。

追祖先链：

```bash
trace() { local p=$1; while [ -n "$p" ] && [ "$p" != "0" ]; do
  local i=$(ps -o ppid=,comm= -p "$p" 2>/dev/null); [ -z "$i" ] && break
  echo -n " <- $p:$(echo "$i" | awk '{$1="";print}' | xargs basename)"
  p=$(echo "$i" | awk '{print $1}'); done; echo; }
trace <PID>
```

## 六个阶段

### 1. 孤儿进程与端口

**先找 supervisor，再杀工作进程。** 这是最容易踩的坑 —— 详见下方 Common Mistakes。

```bash
# 谁在占端口
lsof -nP -iTCP -sTCP:LISTEN | awk 'NR>1 {print $1, $2, $9}' | sort -u

# 孤儿 dev 进程（PPID=1 且不是系统组件）
ps -Ao pid,ppid,etime,rss,user,command | awk '$2==1 && $5=="'"$USER"'"' \
  | grep -vE "/System/|/usr/libexec/|/Applications/|com\.apple"
```

杀的顺序：**supervisor / 循环脚本 → 父进程 → 子进程**。倒过来杀，supervisor 会立刻把子进程拉起来。

`uv run`、`npm run` 这类 wrapper **会忽略 SIGTERM**。先 `kill -TERM`，2 秒后没死直接 `kill -9`。

### 2. Docker

```bash
docker system df                    # 先看可回收多少
docker ps -a --format "{{.Names}}\t{{.Status}}"
docker volume ls -qf dangling=true  # 看清楚名字再删
```

**具名 volume 里通常是本地数据库数据**（`*-pgdata`、`*-data`），删了就没了。随机哈希名的才是安全的悬空卷。不确定就问。

镜像只删「无容器引用 + 明显陈旧」的。基础镜像（node/postgres 等）删了要重拉，收益不抵麻烦。

### 3. 包管理器缓存（收益最大，风险最低）

按经验收益排序：

```bash
pnpm store prune       # 通常是最大单项，可达 10GB+
npm cache clean --force
uv cache prune         # 注意锁，见下
brew cleanup --prune=all
```

**清之前先确认没有活跃进程持有锁**，否则会打断别的 session：

```bash
lsof ~/.cache/uv/.lock 2>/dev/null && echo "有进程在用，跳过"
```

被占用就跳过，**不要用 `--force` 强清** —— 那会让正在跑的任务失败。等它结束再回来清。

### 4. Colima / VM

先问用户 —— 重启会中断所有容器，可能打断别的 session 的活。

```bash
colima stop && colima start
colima ssh -- sudo fstrim -av     # 关键：不做这步磁盘不会真正释放
docker ps -a                       # 关键：核对容器是否都回来了
```

两个必做的收尾在 Common Mistakes 里。

### 5. AI agent 缓存

session / 对话历史是**有价值的资产，默认全部保留**，除非用户明确同意删。

可以放心清的是缓存：

```bash
du -sh ~/Library/Caches/<agent>/org.sparkle-project.Sparkle/Installation  # 更新残留，常有 1GB+
du -sh ~/.cache/*runtime*                                                  # 运行时，会重新下载
du -sh ~/Library/Caches/<agent>/Default                                    # 内嵌浏览器缓存
```

清 runtime 前先确认没被占用：`lsof +D <dir>`。

顺手看一眼 GUI agent 应用下挂的长命子进程（repl / sandbox / helper），跑了一天以上的基本是遗留的，杀掉会按需重建。

### 6. 复核

```bash
df -h /System/Volumes/Data
sysctl vm.swapusage
lsof -nP -iTCP -sTCP:LISTEN | awk 'NR>1 {print $1, $9}' | sort -u
```

## Common Mistakes

| 坑 | 现象 | 正确做法 |
|---|---|---|
| **杀了 supervisor 的子进程** | port-forward 杀掉几秒后又出现，端口一直不放 | 先 `trace` 找到循环脚本本体（常是 `*-pf.sh`、`dev-*.sh`），杀它，再杀子进程 |
| **只用 SIGTERM** | `uv run` / `npm run` 纹丝不动 | TERM 后 2 秒没死就 `kill -9` |
| **强清被锁的缓存** | 别的 session 任务突然失败 | `lsof` 确认无占用；被占用就跳过，事后重试 |
| **Colima 重启后不管** | 部分容器没起来，端口缺失 | 没有 restart policy 的容器**不会自动恢复**，必须 `docker start` 手动补，再核对端口 |
| **只做 stop/start 就以为回收了磁盘** | `~/.colima` 大小纹丝不动 | 稀疏镜像需要在 guest 内 `fstrim -av` 才会真正释放块 |
| **删具名 Docker volume** | 本地数据库数据没了 | 只删随机哈希名的悬空卷；具名的先问 |
| **删了 session 历史** | 不可恢复 | 默认只清缓存，session 要用户明确同意 |

## 通常不该自作主张动的大户

扫出来会很显眼，但都该留给用户决定：

- IM / 浏览器的 `Application Support` 数据（常是最大单项，几十 GB）
- 模型权重缓存（`~/.cache/huggingface` 等）—— 删了要重下
- `~/Downloads`

报告出来，让用户自己选。
