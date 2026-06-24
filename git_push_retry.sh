#!/bin/bash
# ============================================
#  Git Push 自动重试脚本
#  用途：在网络不稳定时自动重试 git push，
#        直到推送成功为止。
#  用法：
#    bash git_push_retry.sh              # 推送到当前分支对应的远端
#    bash git_push_retry.sh origin main  # 推送到指定远端/分支
#    INTERVAL=30 MAX_RETRY=20 bash git_push_retry.sh
#  可调环境变量：
#    INTERVAL   两次重试之间的基础等待秒数（默认 10）
#    MAX_RETRY  最大重试次数（默认 50，0 表示无限重试）
#    PUSH_ARGS  额外透传给 git push 的参数，例如 " --force-with-lease"
# ============================================
set -u

INTERVAL="${INTERVAL:-10}"
MAX_RETRY="${MAX_RETRY:-50}"
PUSH_ARGS="${PUSH_ARGS:-}"

# 参数解析：可选 [remote] [branch]
REMOTE="${1:-}"
BRANCH="${2:-}"

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

print_info()  { echo -e "${BLUE}[INFO]${NC}  $*"; }
print_ok()    { echo -e "${GREEN}[ OK ]${NC}  $*"; }
print_warn()  { echo -e "${YELLOW}[WARN]${NC}  $*"; }
print_err()   { echo -e "${RED}[FAIL]${NC}  $*"; }

# 必须在 git 仓库内
if ! git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
    print_err "当前目录不是 git 仓库，请在项目根目录下执行。"
    exit 1
fi

# 没有指定远端/分支时尝试推断
if [ -z "$REMOTE" ] || [ -z "$BRANCH" ]; then
    CURRENT_BRANCH="$(git symbolic-ref --short HEAD 2>/dev/null || git rev-parse --short HEAD)"
    UPSTREAM="$(git rev-parse --abbrev-ref --symbolic-full-name '@{u}' 2>/dev/null || true)"
    if [ -n "$UPSTREAM" ]; then
        REMOTE="${UPSTREAM%%/*}"
        BRANCH="${UPSTREAM#*/}"
        print_info "自动检测到上游：$REMOTE $BRANCH（当前分支：$CURRENT_BRANCH）"
    else
        REMOTE="origin"
        BRANCH="$CURRENT_BRANCH"
        print_warn "未配置上游，默认将推送到 $REMOTE $BRANCH"
    fi
fi

# 检查远端是否存在，避免无意义的失败
if ! git remote get-url "$REMOTE" >/dev/null 2>&1; then
    print_err "远端 $REMOTE 不存在，请先执行 git remote -v 检查。"
    exit 1
fi

# 提前尝试 fetch 一次以减少 push 时的失败
print_info "尝试拉取远端最新引用（best effort）..."
git fetch "$REMOTE" "$BRANCH" --prune 2>/dev/null || true

# 构造 push 命令
PUSH_CMD=(git push)
if [ -n "$REMOTE" ]; then
    PUSH_CMD+=("$REMOTE" "$BRANCH")
fi
if [ -n "$PUSH_ARGS" ]; then
    # shellcheck disable=SC2206
    EXTRA=( $PUSH_ARGS )
    PUSH_CMD+=("${EXTRA[@]}")
fi

attempt=0
sleep_seconds=$INTERVAL
last_error=""

print_info "开始推送：${PUSH_CMD[*]}"
print_info "基础重试间隔：${INTERVAL}s；最大重试：${MAX_RETRY}（0 表示无限）"

while :; do
    attempt=$((attempt + 1))
    print_info "—— 第 $attempt 次推送尝试 ——"

    output_file="$(mktemp -t gitretry.XXXXXX)"
    if "${PUSH_CMD[@]}" >"$output_file" 2>&1; then
        cat "$output_file"
        rm -f "$output_file"
        print_ok "🎉 推送成功！共尝试 $attempt 次。"
        exit 0
    fi
    last_error="$(tail -n 5 "$output_file")"
    print_err "推送失败（尝试 $attempt）"
    echo "------- git push 输出尾部 -------"
    echo "$last_error"
    echo "---------------------------------"
    rm -f "$output_file"

    if [ "$MAX_RETRY" -gt 0 ] && [ "$attempt" -ge "$MAX_RETRY" ]; then
        print_err "已达到最大重试次数 $MAX_RETRY，放弃。"
        exit 1
    fi

    # 指数退避 + 随机抖动，封顶 120s，避免长时间不释放
    jitter=$((RANDOM % 5))
    sleep_for=$(( sleep_seconds + jitter ))
    if [ "$sleep_for" -gt 120 ]; then
        sleep_for=120
    fi
    print_warn "等待 ${sleep_for}s 后重试…（下次的等待时间会逐步增加）"
    sleep "$sleep_for"

    # 下一次等待时间翻倍，但不超过 60s 基础值
    sleep_seconds=$(( sleep_seconds * 2 ))
    if [ "$sleep_seconds" -gt 60 ]; then
        sleep_seconds=60
    fi
done
