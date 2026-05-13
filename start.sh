#!/bin/bash
#
# TrendRadar SaaS 一键启动脚本
# 用法: ./start.sh [start|stop|status]
#

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

BASE_DIR="$(cd "$(dirname "$0")" && pwd)"
PID_FILE="$BASE_DIR/.services.pid"

log() { echo -e "${BLUE}[INFO]${NC} $1"; }
ok() { echo -e "${GREEN}[OK]${NC} $1"; }
warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
err() { echo -e "${RED}[ERROR]${NC} $1"; }

stop() {
    if [ -f "$PID_FILE" ]; then
        log "停止服务..."
        while IFS=: read -r name pid; do
            # Kill child processes first, then parent
            pkill -P "$pid" 2>/dev/null || true
            sleep 0.5
            kill "$pid" 2>/dev/null && ok "已停止 $name (PID: $pid)" || warn "$name 未运行"
        done < "$PID_FILE"
        rm -f "$PID_FILE"
    else
        warn "没有运行中的服务"
    fi

    # Fallback: force kill anything on our ports
    sleep 1
    if ss -tlnp 2>/dev/null | grep -q ':8000 '; then
        log "强制清理端口 8000..."
        lsof -ti:8000 | xargs kill -9 2>/dev/null || true
    fi
    if ss -tlnp 2>/dev/null | grep -q ':5173 '; then
        log "强制清理端口 5173..."
        lsof -ti:5173 | xargs kill -9 2>/dev/null || true
    fi
}

status() {
    if [ -f "$PID_FILE" ]; then
        while IFS=: read -r name pid; do
            if kill -0 "$pid" 2>/dev/null; then
                ok "$name 运行中 (PID: $pid)"
            else
                err "$name 已停止"
            fi
        done < "$PID_FILE"
    else
        warn "没有运行中的服务"
    fi
}

start() {
    # 检查端口
    if ss -tlnp 2>/dev/null | grep -q ':8000 ' || lsof -i :8000 >/dev/null 2>&1; then
        err "端口 8000 已被占用"
        exit 1
    fi
    if ss -tlnp 2>/dev/null | grep -q ':5173 ' || lsof -i :5173 >/dev/null 2>&1; then
        err "端口 5173 已被占用"
        exit 1
    fi

    # 数据库迁移
    log "执行数据库迁移..."
    cd "$BASE_DIR/backend"
    source "$BASE_DIR/.venv/bin/activate" 2>/dev/null || true
    if alembic upgrade head >> /tmp/tr-alembic.log 2>&1; then
        ok "数据库迁移完成"
    else
        # 如果迁移失败可能是因为表已存在但 alembic_version 未记录
        # 尝试 stamp 到最新版本后重试
        if grep -q "already exists" /tmp/tr-alembic.log; then
            warn "检测到已存在的数据库表，正在同步迁移状态..."
            alembic stamp head >> /tmp/tr-alembic.log 2>&1
            alembic upgrade head >> /tmp/tr-alembic.log 2>&1
            ok "数据库状态同步完成"
        else
            warn "数据库迁移失败，请查看 /tmp/tr-alembic.log"
        fi
    fi

    # 构建前端
    log "构建前端..."
    cd "$BASE_DIR/frontend"
    if [ -d "node_modules" ]; then
        if node node_modules/.bin/vite build >> /tmp/tr-frontend-build.log 2>&1; then
            ok "前端构建完成"
        else
            warn "前端构建失败，请查看 /tmp/tr-frontend-build.log"
        fi
    else
        warn "node_modules 不存在，跳过前端构建"
    fi

    # 清理旧 PID 文件
    rm -f "$PID_FILE"

    # 启动后端
    log "启动后端 (Port: 8000)..."
    cd "$BASE_DIR/backend"
    source "$BASE_DIR/.venv/bin/activate" 2>/dev/null || true
    nohup uvicorn app.main:app --host 127.0.0.1 --port 8000 > /tmp/tr-backend.log 2>&1 &
    echo "backend:$!" >> "$PID_FILE"
    ok "后端已启动 (PID: $!)"

    # 启动 Celery Worker
    log "启动 Celery Worker..."
    cd "$BASE_DIR/backend"
    source "$BASE_DIR/.venv/bin/activate" 2>/dev/null || true
    nohup celery -A app.celery_app worker --loglevel=info --queues=crawl,analyze,push,translate --concurrency=4 > /tmp/tr-celery.log 2>&1 &
    echo "celery:$!" >> "$PID_FILE"
    ok "Celery Worker 已启动 (PID: $!)"

    # 启动前端
    log "启动前端 (Port: 5173)..."
    cd "$BASE_DIR/frontend"
    nohup node node_modules/.bin/vite > /tmp/tr-frontend.log 2>&1 &
    echo "frontend:$!" >> "$PID_FILE"
    ok "前端已启动 (PID: $!)"

    # 等待后端就绪
    log "等待后端就绪..."
    for i in $(seq 1 15); do
        if curl -sf http://127.0.0.1:8000/health >/dev/null 2>&1; then
            ok "后端就绪"
            break
        fi
        sleep 1
    done

    echo ""
    echo -e "${GREEN}========================================${NC}"
    echo -e "${GREEN}  TrendRadar SaaS 启动成功${NC}"
    echo -e "${GREEN}========================================${NC}"
    echo ""
    echo "  前端: http://localhost:5173"
    echo "  后端: http://127.0.0.1:8000"
    echo "  API:  http://127.0.0.1:8000/docs"
    echo ""
    echo "  停止: ./start.sh stop"
    echo "  日志: tail -f /tmp/tr-backend.log"
    echo "  任务: tail -f /tmp/tr-celery.log"
    echo ""
}

case "${1:-start}" in
    start)  start ;;
    stop)   stop ;;
    status) status ;;
    *)
        echo "用法: $0 {start|stop|status}"
        exit 1
        ;;
esac
