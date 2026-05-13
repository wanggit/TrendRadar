#!/bin/bash
#
# TrendRadar SaaS 一键启动脚本
# 用法: ./start-all.sh [选项]
#

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$SCRIPT_DIR"
VENV_DIR="$PROJECT_ROOT/.venv"
PID_FILE="$PROJECT_ROOT/.start-all.pids"

# 获取 Python 路径
get_venv_python() {
    if [ -f "$VENV_DIR/bin/python3" ]; then
        echo "$VENV_DIR/bin/python3"
    elif [ -f "$VENV_DIR/bin/python" ]; then
        echo "$VENV_DIR/bin/python"
    else
        echo "python3"
    fi
}

PYTHON_CMD=$(get_venv_python)

# 打印信息
log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[OK]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# 停止所有服务
stop_all() {
    log_info "停止所有服务..."
    if [ -f "$PID_FILE" ]; then
        while IFS= read -r line; do
            pid=$(echo "$line" | cut -d: -f2 | tr -d ' ')
            name=$(echo "$line" | cut -d: -f1)
            if [ -n "$pid" ] && kill -0 "$pid" 2>/dev/null; then
                kill "$pid" 2>/dev/null && log_success "已停止 $name (PID: $pid)"
            fi
        done < "$PID_FILE"
        rm -f "$PID_FILE"
    else
        log_warn "未找到运行中的服务"
    fi
    exit 0
}

# 检查并安装依赖
check_deps() {
    # 后端依赖
    if [ ! -f "$VENV_DIR/bin/activate" ]; then
        log_info "创建虚拟环境..."
        python3 -m venv "$VENV_DIR" --without-pip 2>/dev/null || python3 -m venv "$VENV_DIR"
        curl -sS https://bootstrap.pypa.io/get-pip.py | "$VENV_DIR/bin/python3" > /dev/null 2>&1
    fi

    if ! $PYTHON_CMD -c "import fastapi" 2>/dev/null; then
        log_info "安装后端依赖..."
        "$VENV_DIR/bin/pip" install -r "$PROJECT_ROOT/backend/requirements.txt" -q
    fi

    # 前端依赖
    if [ ! -d "$PROJECT_ROOT/frontend/node_modules" ]; then
        log_info "安装前端依赖..."
        cd "$PROJECT_ROOT/frontend" && npm install
    fi
}

# 启动后端
start_backend() {
    log_info "启动后端 (Port: 8000)..."
    cd "$PROJECT_ROOT/backend"
    source "$VENV_DIR/bin/activate"
    
    # 初始化数据库（首次运行）
    if [ ! -f "$PROJECT_ROOT/backend/trendradar.db" ]; then
        alembic upgrade head 2>/dev/null || true
        python -m app.db.init_db 2>/dev/null || true
    fi

    nohup uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload > /tmp/trendradar-backend.log 2>&1 &
    BACKEND_PID=$!
    echo "backend:$BACKEND_PID" >> "$PID_FILE"
    log_success "后端已启动 (PID: $BACKEND_PID)"
}

# 启动前端
start_frontend() {
    log_info "启动前端 (Port: 5173)..."
    cd "$PROJECT_ROOT/frontend"
    nohup npm run dev > /tmp/trendradar-frontend.log 2>&1 &
    FRONTEND_PID=$!
    echo "frontend:$FRONTEND_PID" >> "$PID_FILE"
    log_success "前端已启动 (PID: $FRONTEND_PID)"
}

# 等待服务就绪
wait_for_services() {
    log_info "等待服务启动..."
    for i in $(seq 1 10); do
        if curl -s http://127.0.0.1:8000/health > /dev/null 2>&1; then
            log_success "后端就绪"
            return 0
        fi
        sleep 1
    done
    log_warn "后端启动较慢，请稍后查看日志: tail -f /tmp/trendradar-backend.log"
}

# 显示帮助
show_help() {
    echo -e "${BLUE}TrendRadar SaaS 一键启动脚本${NC}"
    echo ""
    echo "用法: $0 [选项]"
    echo ""
    echo "选项:"
    echo "  --start     启动所有服务（默认）"
    echo "  --stop      停止所有服务"
    echo "  --status    查看服务状态"
    echo "  --help      显示此帮助信息"
}

# 主逻辑
main() {
    case "${1:---start}" in
        --stop)
            stop_all
            ;;
        --status)
            if [ -f "$PID_FILE" ]; then
                while IFS= read -r line; do
                    pid=$(echo "$line" | cut -d: -f2 | tr -d ' ')
                    name=$(echo "$line" | cut -d: -f1)
                    if kill -0 "$pid" 2>/dev/null; then
                        log_success "$name 运行中 (PID: $pid)"
                    else
                        log_error "$name 已停止 (PID: $pid)"
                    fi
                done < "$PID_FILE"
            else
                log_warn "没有运行中的服务"
            fi
            ;;
        --start|"")
            # 检查端口占用
            if command -v lsof &> /dev/null; then
                if lsof -i :8000 > /dev/null 2>&1; then
                    log_error "端口 8000 已被占用，请先运行: $0 --stop"
                    exit 1
                fi
                if lsof -i :5173 > /dev/null 2>&1; then
                    log_error "端口 5173 已被占用，请先运行: $0 --stop"
                    exit 1
                fi
            fi

            check_deps
            > "$PID_FILE"  # 清空 PID 文件
            start_backend
            start_frontend
            wait_for_services
            
            echo ""
            echo -e "${GREEN}========================================${NC}"
            echo -e "${GREEN}  TrendRadar SaaS 启动成功！${NC}"
            echo -e "${GREEN}========================================${NC}"
            echo ""
            echo "  前端地址: http://localhost:5173"
            echo "  后端地址: http://127.0.0.1:8000"
            echo "  API 文档: http://127.0.0.1:8000/docs"
            echo ""
            echo "  停止服务: ./start-all.sh --stop"
            echo "  查看日志: tail -f /tmp/trendradar-backend.log"
            echo ""
            ;;
        --help|-h)
            show_help
            ;;
        *)
            log_error "未知选项: $1"
            show_help
            exit 1
            ;;
    esac
}

main "$@"
