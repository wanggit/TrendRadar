#!/bin/bash
#
# TrendRadar 开发启动脚本
# 用法: ./dev.sh [选项]
#

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR" && pwd)"
VENV_DIR="$PROJECT_ROOT/.venv"
CONFIG_DIR="$PROJECT_ROOT/config"
DOCS_DIR="$PROJECT_ROOT/docs"
REQUIREMENTS="$PROJECT_ROOT/requirements.txt"

# 获取 venv 中的 Python 路径
get_venv_python() {
    if [ -f "$VENV_DIR/bin/python3" ]; then
        echo "$VENV_DIR/bin/python3"
    elif [ -f "$VENV_DIR/bin/python" ]; then
        echo "$VENV_DIR/bin/python"
    else
        echo "python3"
    fi
}

# 获取 venv 中的 pip 路径
get_venv_pip() {
    if [ -f "$VENV_DIR/bin/pip3" ]; then
        echo "$VENV_DIR/bin/pip3"
    elif [ -f "$VENV_DIR/bin/pip" ]; then
        echo "$VENV_DIR/bin/pip"
    else
        echo "pip3"
    fi
}

PYTHON_CMD=$(get_venv_python)
PIP_CMD=$(get_venv_pip)

# 帮助信息
show_help() {
    echo -e "${BLUE}TrendRadar 开发启动脚本${NC}"
    echo ""
    echo "用法: $0 [选项]"
    echo ""
    echo "选项:"
    echo "  --install        创建 venv 并安装依赖"
    echo "  --all           启动所有服务（配置编辑器 + TrendRadar CLI）"
    echo "  --editor        启动 HTTP 服务并打开配置编辑器"
    echo "  --editor-port N  指定编辑器 HTTP 服务端口（默认 8080）"
    echo "  --cli           启动 TrendRadar CLI"
    echo "  --preview       生成 HTML 报告预览（当前数据）"
    echo "  --stop          停止 HTTP 编辑器服务"
    echo "  --help          显示此帮助信息"
    echo ""
    echo "示例:"
    echo "  $0 --install    # 首次使用：创建 venv 并安装依赖"
    echo "  $0 --editor     # 启动 HTTP 服务并打开配置编辑器"
    echo "  $0 --editor --editor-port 9000  # 指定端口 9000"
    echo "  $0 --stop       # 停止 HTTP 服务"
    echo "  $0 --cli        # 运行 TrendRadar"
}

# 检查依赖
check_dependencies() {
    echo -e "${BLUE}检查 Python 环境...${NC}"

    if [ ! -f "$VENV_DIR/bin/python3" ]; then
        echo -e "${YELLOW}⚠ venv 不存在，正在创建...${NC}"
        create_venv
    fi

    echo -e "${GREEN}✓ venv Python: $PYTHON_CMD${NC}"

    # 检查核心依赖
    if ! $PYTHON_CMD -c "import yaml, requests, feedparser, pytz" 2>/dev/null; then
        echo -e "${YELLOW}⚠ 缺少 Python 依赖，正在安装...${NC}"
        install_requirements
    fi
    echo -e "${GREEN}✓ Python 依赖检查通过${NC}"
}

# 创建 venv
create_venv() {
    echo -e "${BLUE}创建虚拟环境...${NC}"

    if command -v python3 &> /dev/null; then
        PY_VERSION=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
        REQUIRED_VERSION="3.12"
        if [ "$(printf '%s\n' "$REQUIRED_VERSION" "$PY_VERSION" | sort -V | head -n1)" != "$REQUIRED_VERSION" ]; then
            echo -e "${RED}✗ Python 版本需要 >= 3.12，当前: $PY_VERSION${NC}"
            exit 1
        fi
    fi

    python3 -m venv "$VENV_DIR" --without-pip

    # 引导 pip
    curl -sS https://bootstrap.pypa.io/get-pip.py | "$VENV_DIR/bin/python3" > /dev/null 2>&1

    echo -e "${GREEN}✓ 虚拟环境已创建: $VENV_DIR${NC}"
}

# 安装依赖
install_requirements() {
    echo -e "${BLUE}安装 Python 依赖...${NC}"
    $PIP_CMD install --upgrade pip -q
    $PIP_CMD install -r "$REQUIREMENTS" -q
    echo -e "${GREEN}✓ 依赖安装完成${NC}"
}

# 启动配置编辑器（HTTP 服务）
start_editor() {
    local PORT="${EDITOR_PORT:-8080}"
    
    echo -e "${BLUE}启动配置编辑器 HTTP 服务...${NC}"
    echo -e "${YELLOW}服务目录: $DOCS_DIR${NC}"
    echo -e "${YELLOW}监听端口: $PORT${NC}"
    echo ""

    # 检查端口是否被占用
    if command -v lsof &> /dev/null; then
        if lsof -i :$PORT > /dev/null 2>&1; then
            echo -e "${YELLOW}⚠ 端口 $PORT 已被占用，尝试自动选择可用端口...${NC}"
            PORT=$(python3 -c "
import socket
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.bind(('', 0))
print(s.getsockname()[1])
s.close()
")
            echo -e "${GREEN}✓ 使用可用端口: $PORT${NC}"
        fi
    fi

    # 启动 HTTP 服务（后台运行）
    cd "$DOCS_DIR"
    nohup $PYTHON_CMD -m http.server $PORT --bind 127.0.0.1 > /dev/null 2>&1 &
    HTTP_PID=$!
    
    # 等待服务启动
    sleep 1
    
    # 检查服务是否启动成功
    if kill -0 $HTTP_PID 2>/dev/null; then
        echo -e "${GREEN}✓ HTTP 服务已启动 (PID: $HTTP_PID)${NC}"
        echo -e "${GREEN}访问地址: http://127.0.0.1:$PORT/index.html${NC}"
        echo -e "${YELLOW}提示: 按 Ctrl+C 或运行 'kill $HTTP_PID' 停止服务${NC}"
        echo ""
        
        # 打开浏览器
        if command -v open &> /dev/null; then
            open "http://127.0.0.1:$PORT/index.html"
        elif command -v xdg-open &> /dev/null; then
            xdg-open "http://127.0.0.1:$PORT/index.html"
        elif command -v start &> /dev/null; then
            start "http://127.0.0.1:$PORT/index.html"
        else
            echo -e "${YELLOW}无法自动打开浏览器，请手动访问:${NC}"
            echo -e "${GREEN}http://127.0.0.1:$PORT/index.html${NC}"
        fi
        
        # 保存 PID 到文件，方便后续停止
        echo $HTTP_PID > "$PROJECT_ROOT/.http-server.pid"
    else
        echo -e "${RED}✗ HTTP 服务启动失败${NC}"
        return 1
    fi
}

# 停止 HTTP 服务
stop_editor() {
    local PID_FILE="$PROJECT_ROOT/.http-server.pid"
    if [ -f "$PID_FILE" ]; then
        local PID=$(cat "$PID_FILE")
        if kill -0 $PID 2>/dev/null; then
            echo -e "${BLUE}停止 HTTP 服务 (PID: $PID)...${NC}"
            kill $PID
            rm -f "$PID_FILE"
            echo -e "${GREEN}✓ HTTP 服务已停止${NC}"
        else
            echo -e "${YELLOW}⚠ HTTP 服务未运行${NC}"
            rm -f "$PID_FILE"
        fi
    else
        echo -e "${YELLOW}⚠ 未找到 HTTP 服务 PID 文件${NC}"
    fi
}

# 检查配置文件
check_config() {
    if [ ! -f "$CONFIG_DIR/config.yaml" ]; then
        echo -e "${RED}✗ 配置文件不存在: $CONFIG_DIR/config.yaml${NC}"
        echo -e "${YELLOW}请先配置 config.yaml，或使用配置编辑器生成配置${NC}"
        return 1
    fi
    echo -e "${GREEN}✓ 配置文件存在${NC}"
}

# 启动 TrendRadar CLI
start_cli() {
    check_dependencies
    check_config

    echo -e "${BLUE}启动 TrendRadar CLI...${NC}"
    echo ""

    cd "$PROJECT_ROOT"
    $PYTHON_CMD -m trendradar "$@"
}

# 生成 HTML 报告预览
generate_preview() {
    check_dependencies
    check_config

    echo -e "${BLUE}生成 HTML 报告预览...${NC}"

    cd "$PROJECT_ROOT"

    OUTPUT_DIR="$PROJECT_ROOT/output/preview"
    mkdir -p "$OUTPUT_DIR"

    echo -e "${YELLOW}正在抓取数据并生成报告...${NC}"
    $PYTHON_CMD -m trendradar run --output-dir "$OUTPUT_DIR" --format html 2>&1 | head -30

    HTML_FILE=$(find "$OUTPUT_DIR" -name "*.html" -type f | head -1)

    if [ -n "$HTML_FILE" ]; then
        echo ""
        echo -e "${GREEN}✓ 报告已生成: $HTML_FILE${NC}"

        if command -v open &> /dev/null; then
            open "$HTML_FILE"
        elif command -v xdg-open &> /dev/null; then
            xdg-open "$HTML_FILE"
        else
            echo -e "${YELLOW}请手动打开: file://$HTML_FILE${NC}"
        fi
    else
        echo -e "${RED}✗ 报告生成失败${NC}"
        return 1
    fi
}

# 激活 venv (用于 source)
activate_venv() {
    if [ -f "$VENV_DIR/bin/activate" ]; then
        echo "source $VENV_DIR/bin/activate"
    fi
}

# 主逻辑
main() {
    echo -e "${BLUE}"
    echo "========================================"
    echo "  TrendRadar 开发环境"
    echo "========================================"
    echo -e "${NC}"
    echo ""

    if [ $# -eq 0 ]; then
        show_help
        exit 0
    fi

    # 解析参数
    EDITOR_PORT=8080
    ACTION=""
    
    while [ $# -gt 0 ]; do
        case "$1" in
            --editor-port)
                EDITOR_PORT="$2"
                shift 2
                ;;
            --install|--all|--editor|--cli|--preview|--activate|--stop|--help|-h)
                ACTION="$1"
                shift
                ;;
            *)
                echo -e "${RED}未知选项: $1${NC}"
                show_help
                exit 1
                ;;
        esac
    done

    case "$ACTION" in
        --install)
            create_venv
            install_requirements
            echo ""
            echo -e "${GREEN}✓ 环境配置完成！${NC}"
            echo "  下次使用可直接运行: ./dev.sh --cli"
            ;;
        --all)
            check_dependencies
            start_editor
            echo ""
            start_cli
            ;;
        --editor)
            start_editor
            ;;
        --cli)
            shift
            start_cli "$@"
            ;;
        --preview)
            generate_preview
            ;;
        --stop)
            stop_editor
            ;;
        --activate)
            # 输出激活命令
            if [ -f "$VENV_DIR/bin/activate" ]; then
                echo "source $VENV_DIR/bin/activate"
            else
                echo -e "${RED}venv 不存在，请先运行: ./dev.sh --install${NC}"
                exit 1
            fi
            ;;
        --help|-h)
            show_help
            ;;
        *)
            echo -e "${RED}未知选项: $ACTION${NC}"
            show_help
            exit 1
            ;;
    esac
}

main "$@"
