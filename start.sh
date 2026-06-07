#!/bin/bash
# ============================================
#  Digital Planner - 自动启动/重启/停止脚本
#  用法: 
#    bash start.sh          - 启动服务
#    bash start.sh restart  - 重启服务
#    bash start.sh stop     - 停止服务
#    bash start.sh status   - 检查状态
# ============================================
set -e

cd "$(dirname "$0")"

APP_NAME="digital-planner"
PORT=8000
PID_FILE=".diary.pid"
LOG_FILE=".diary.log"

# ============================================
#  功能函数
# ============================================

# 检查端口是否被占用
check_port() {
    if lsof -i :$PORT >/dev/null 2>&1; then
        return 0  # 端口被占用
    else
        return 1  # 端口未被占用
    fi
}

# 获取进程 PID
get_pid() {
    if [ -f $PID_FILE ]; then
        local PID=$(cat $PID_FILE 2>/dev/null)
        if [ -n "$PID" ] && kill -0 $PID 2>/dev/null; then
            echo $PID
            return 0
        fi
        rm -f $PID_FILE
    fi
    return 1
}

# 停止服务
stop_service() {
    echo ""
    echo "[停止服务]"
    
    local PID=$(get_pid)
    if [ -n "$PID" ]; then
        echo "  正在停止进程 $PID..."
        kill $PID 2>/dev/null || true
        sleep 2
        
        if kill -0 $PID 2>/dev/null; then
            echo "  进程仍在运行，强制停止..."
            kill -9 $PID 2>/dev/null || true
            sleep 1
        fi
    fi
    
    rm -f $PID_FILE
    echo "  ✓ 服务已停止"
}

# 启动服务
start_service() {
    echo ""
    echo "[启动服务]"
    
    # 先检查是否已有运行的进程
    local PID=$(get_pid)
    if [ -n "$PID" ]; then
        echo "  [警告] 服务已在运行 (PID: $PID)"
        echo "  使用 'bash start.sh restart' 来重启"
        return 1
    fi
    
    # 检查 .env 文件
    if [ ! -f .env ]; then
        echo "  [WARN] .env 文件不存在，使用默认配置"
    fi
    
    # 检查依赖
    echo "  [1/3] 检查依赖..."
    python3 -c "from fastapi import FastAPI" 2>/dev/null || {
        echo "  [ERROR] 缺少依赖，请先运行: pip install -r requirements.txt"
        exit 1
    }
    echo "    ✓ 依赖检查通过"
    
    # 检查端口
    echo "  [2/3] 检查端口..."
    if check_port; then
        echo "  [WARN] 端口 $PORT 已被占用，尝试清理..."
        local OLD_PID=$(lsof -ti :$PORT 2>/dev/null)
        if [ -n "$OLD_PID" ]; then
            kill -9 $OLD_PID 2>/dev/null || true
            sleep 1
        fi
    fi
    echo "    ✓ 端口检查通过"
    
    # 启动服务
    echo "  [3/3] 启动服务..."
    
    # 后台运行并记录日志
    nohup python3 main.py > $LOG_FILE 2>&1 &
    local PID=$!
    
    # 保存 PID
    echo $PID > $PID_FILE
    
    # 等待服务启动
    echo "  等待服务启动..."
    for i in {1..10}; do
        sleep 1
        if curl -s http://localhost:$PORT/health >/dev/null 2>&1; then
            break
        fi
        echo -n "."
    done
    
    echo ""
    echo "=================================="
    echo "  服务已成功启动!"
    echo "=================================="
    echo "  地址: http://localhost:$PORT"
    echo "  PID: $PID"
    echo "  日志: tail -f $LOG_FILE"
    echo "=================================="
}

# 重启服务
restart_service() {
    echo "=================================="
    echo "  正在重启服务..."
    echo "=================================="
    stop_service
    sleep 1
    start_service
}

# 显示状态
show_status() {
    echo "=================================="
    echo "  服务状态检查"
    echo "=================================="
    
    local PID=$(get_pid)
    if [ -n "$PID" ]; then
        echo "  ✓ 服务正在运行"
        echo "    PID: $PID"
        echo "    端口: $PORT"
        echo "    日志文件: $LOG_FILE"
        
        if command -v lsof >/dev/null 2>&1; then
            echo ""
            echo "  进程信息:"
            ps -p $PID -o pid,ppid,command 2>/dev/null || echo "  无法获取进程详情"
        fi
    else
        echo "  ✗ 服务未运行"
        echo ""
        if check_port; then
            echo "  警告: 端口 $PORT 被占用，但进程不在 $PID_FILE 中!"
        fi
    fi
    echo "=================================="
}

# 显示使用说明
show_help() {
    echo "=================================="
    echo "  Dear Diary - 管理脚本"
    echo "=================================="
    echo ""
    echo "  用法:"
    echo "    bash start.sh          - 启动服务"
    echo "    bash start.sh restart  - 重启服务"
    echo "    bash start.sh stop     - 停止服务"
    echo "    bash start.sh status   - 检查状态"
    echo "    bash start.sh help     - 显示帮助"
    echo ""
}

# ============================================
#  主逻辑
# ============================================

case "${1:-start}" in
    start)
        start_service
        ;;
    stop)
        stop_service
        ;;
    restart)
        restart_service
        ;;
    status)
        show_status
        ;;
    help)
        show_help
        ;;
    *)
        echo "  [错误] 未知命令: $1"
        echo ""
        show_help
        exit 1
        ;;
esac