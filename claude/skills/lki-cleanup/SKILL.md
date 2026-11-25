---
name: lki-cleanup
description: Use when doing routine cleanup on this Mac — orphaned dev processes holding ports, zombie background servers from old debug sessions, stale Docker volumes/images, bloated package-manager caches, Colima memory/disk growth, idle git worktrees, or leftover AI-agent runtime caches. Triggers on "日常清理", "清理电脑", "清硬盘", "端口被占用", "磁盘满了", "内存不够", "swap 爆了", "worktree 太多".
---

# Mac 日常清理

## 核心前提

**我正在用的进程都挂在某个终端或 agent 应用下。** 这是整个 skill 的判据基础：一个进程的祖先链走到终端或 agent 应用（`/Applications/` 下的 App）就是活的，走到 `launchd` (PID 1) 就是孤儿 —— 启动它的终端早已消失，没人再看它的输出，它却还在占端口、吃内存。

先诊断，再动手。诊断阶段全部只读，跑 `./diagnose.sh` 一次拿到全貌。

## 绝不动的东西

- 终端或 agent 应用树下的任何进程（`claude`、`codex`、编辑器、dev server）
- **Cloudflare WARP** —— 断开会切断和 Claude 的 API 连接
- `tailscaled`（如果在跑，注意它需要 `--tun=userspace-networking` 才能和 WARP 共存）
- `~/Downloads`、`~/Documents` 等用户文件
- 任何还有活跃进程持有锁的缓存目录
- 别的 session 认领或正在用的 worktree，以及有未提交改动的 worktree

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

## 七个阶段

磁盘紧张时先做第 6 阶段（闲置 worktree），通常收益最大。动缓存和 worktree 前先用 `ListAgents` + `SendMessage` 问清别的 session 在用什么，**等全部回复再动手**。

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

### 3. 包管理器缓存（风险低）

```bash
brew cleanup --prune=all
npm cache clean --force   # 只删 _cacache，_npx 里已安装的包会保留
uv cache prune            # 注意锁，见下
pnpm store prune          # 放最后，见下
```

**`pnpm store prune` 可能把整个 store 清空。** 实测 7.4G、5730 个包被全删，磁盘却只多出约 2G，疑似 APFS 克隆的文件看起来都没人引用。现有项目不受影响，但之后所有 `pnpm install` 都要重新下载。跑之前：

- 告诉别的 session，确认没有 `pnpm install` 或打包在跑
- `pnpm config get enableGlobalVirtualStore` 如果是 `true`，确认 `<store>/links` 是空的，否则项目依赖会断

**清之前先确认没有活跃进程持有锁**，否则会打断别的 session：

```bash
lsof ~/.cache/uv/.lock 2>/dev/null && echo "有进程在用，跳过"
```

被占用就跳过，**不要用 `--force` 强清** —— 那会让正在跑的任务失败。等它结束再回来清。

### 4. Colima / VM

**回收磁盘不用重启**，`fstrim` 可以直接跑，不会中断容器。Docker 清理之后一定要做（实测 `~/.colima` 从 18G 降到 5.3G）：

```bash
colima ssh -- sudo fstrim -av     # 关键：不做这步磁盘不会真正释放
```

只有要回收内存时才重启。先问用户 —— 重启会中断所有容器，可能打断别的 session 的活。

```bash
colima stop && colima start
colima ssh -- sudo fstrim -av
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

### 6. 闲置 worktree

monorepo 全量安装的 worktree 可达近百 GB。Claude Code 的自动清理会跳过 `git worktree add` 手动建的 worktree，所以它们会一直积累。**删之前要用户点头。**

命中任意一条就保留：

1. **有进程在用**：工作目录或打开的文件落在里面（`diagnose.sh` 的 `IN-USE` 标记、`lsof -n -Fn`）。
2. **有 session 认领**：Agent 的主目录常在仓库根，靠绝对路径操作 worktree，只查进程工作目录会漏。逐个问 peer session，问不到的 Codex 查 `~/.codex/sessions` 最近的 rollout，再用 agent 应用自己的工作区列表核对。
3. **有未提交改动**：`git --no-optional-locks status --porcelain` 非空。这些改动删了找不回。
4. **6 小时内新建**：`stat -f %B`。可能有 session 正要开始用，防竞态。

未推送的 commit 不会丢，`git worktree remove` 会保留分支。但 `.env.local` 这类 git 不管的文件会没，要在确认时告诉用户。

删除步骤：

1. 生成清单，空跑一遍看计划。**临删前重新生成**，期间可能有新 worktree 出现。
2. 按路径长度从长到短删，嵌套的 worktree 先删。
3. 已注册的用 `git worktree remove --force <path>`。
4. 没注册的残留目录要先核对：`git -C <path> rev-parse --show-toplevel` 不等于 `<path>` 时，git 读到的是外层仓库的状态，"干净"不算数。先看清里面除依赖外还有什么，再删。
5. 用 `df` 算实际释放量，复核保留的 worktree 都还在。

### 7. 复核

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
| **用 `du` 估算收益** | 3 处 `du` 显示 238G，实际释放约 60G | `du` 会重复计算 APFS 克隆共享的块，也不要把多次 `du` 的结果相加。收益以删前后的 `df` 为准 |
| **只凭进程工作目录判断 worktree 没人用** | 今天还有 commit 的 worktree 显示无人使用 | 必须问 peer session，并查 Codex 日志 |
| **没等 peer 回复就清缓存** | 别的 session 正在用 `npx` 渲染时缓存被清 | 等全部回复；问不到的就跳过 |
| **用 `git status` 判断最近活动** | 自己的扫描刷新了 index，mtime 全变成"刚刚" | 用 `git --no-optional-locks status`，活动时间只看工作区文件 |

## 通常不该自作主张动的大户

扫出来会很显眼，但都该留给用户决定：

- IM / 浏览器的 `Application Support` 数据（常是最大单项，几十 GB）
- 模型权重缓存（`~/.cache/huggingface` 等）—— 删了要重下
- 仓库里没进 git 的实验数据（`experiments/`、`runs/` 等）—— 删了找不回
- Claude App 的 `vm_bundles`（约 11G 的 Linux 虚拟机）—— 确认不用它再删，先 `lsof +D` 确认没被占用
- `~/Downloads`

报告出来，让用户自己选。
