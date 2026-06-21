#!/usr/bin/env bash
# ============================================================
# Mini-OpenClaw macOS Startup Script
# ============================================================
# 功能：
#   1. 检测 / 自动创建 Conda 虚拟环境 (miniclaw, Python 3.12)
#   2. 安装后端 Python 依赖
#   3. 安装前端 npm 依赖
#   4. 后台启动后端 (uvicorn, port 8002)
#   5. 后台启动前端 (Next.js, port 3000)
#   6. 自动打开浏览器
#   7. Ctrl+C 优雅关闭所有服务
# ============================================================

set -euo pipefail

# ---- 颜色输出 ----
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

info()  { echo -e "${GREEN}[INFO]${NC}  $*"; }
warn()  { echo -e "${YELLOW}[WARN]${NC}  $*"; }
error() { echo -e "${RED}[ERROR]${NC} $*"; }
step()  { echo -e "${CYAN}[STEP]${NC} $*"; }

# ---- 项目根目录 ----
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo ""
echo -e "${CYAN}========================================${NC}"
echo -e "${CYAN}  Mini-OpenClaw macOS Launcher${NC}"
echo -e "${CYAN}========================================${NC}"
echo ""

# ============================================================
# 1. 检测 Conda
# ============================================================
step "1/5  检测 Conda 环境..."

# macOS 常见 Conda 安装路径
CONDA_PATHS=(
    "/opt/miniconda3"
    "/opt/anaconda3"
    "$HOME/miniconda3"
    "$HOME/anaconda3"
    "/usr/local/miniconda3"
    "/usr/local/anaconda3"
)

CONDA_BASE=""
for p in "${CONDA_PATHS[@]}"; do
    if [ -f "$p/etc/profile.d/conda.sh" ]; then
        CONDA_BASE="$p"
        break
    fi
done

if [ -z "$CONDA_BASE" ]; then
    # 尝试通过 which 查找
    if command -v conda &>/dev/null; then
        CONDA_EXE="$(command -v conda)"
        CONDA_BASE="$(dirname "$(dirname "$CONDA_EXE")")"
        if [ ! -f "$CONDA_BASE/etc/profile.d/conda.sh" ]; then
            error "找不到 Conda 安装路径，请确认 Anaconda/Miniconda 已正确安装"
            echo ""
            echo "  macOS 安装 Miniconda："
            echo "    brew install miniconda"
            echo "    conda init zsh"
            echo ""
            exit 1
        fi
    else
        error "未找到 Conda，请先安装 Anaconda 或 Miniconda"
        echo ""
        echo "  macOS 安装 Miniconda（推荐）："
        echo "    brew install miniconda"
        echo "    conda init zsh"
        echo ""
        exit 1
    fi
fi

# 加载 conda
# shellcheck disable=SC1090
. "$CONDA_BASE/etc/profile.d/conda.sh"
info "Conda 路径: $CONDA_BASE"

MINICLAW_ENV="miniclaw"

# 检查 / 创建 miniclaw 环境
if conda env list | awk '!/^#/ && NF {print $1}' | grep -qx "$MINICLAW_ENV"; then
    info "Conda 环境 '$MINICLAW_ENV' 已存在"
else
    warn "Conda 环境 '$MINICLAW_ENV' 未找到，正在创建..."
    conda create -n "$MINICLAW_ENV" python=3.12 -y
    info "环境 '$MINICLAW_ENV' 创建完成"
fi

# 激活环境
conda activate "$MINICLAW_ENV"
info "已激活 Conda 环境: $MINICLAW_ENV ($(python --version 2>&1))"

# ============================================================
# 2. 检测 Node.js
# ============================================================
step "2/5  检测 Node.js..."

if ! command -v node &>/dev/null; then
    error "未找到 Node.js，请先安装 Node.js 18+"
    echo ""
    echo "  macOS 安装 Node.js："
    echo "    brew install node"
    echo ""
    exit 1
fi
info "Node.js $(node --version)"

# ============================================================
# 3. 后端环境检查 & 依赖安装
# ============================================================
step "3/5  配置后端环境..."

cd "$SCRIPT_DIR/backend"

# 自动创建 .env（如果不存在）
if [ ! -f .env ]; then
    if [ -f .env.example ]; then
        warn ".env 文件不存在，已从 .env.example 自动创建"
        warn "请编辑 backend/.env 填入你的 API Keys 后重新启动！"
        cp .env.example .env
        echo ""
        echo -e "  ${YELLOW}必须配置的 API Keys:${NC}"
        echo "    - DEEPSEEK_API_KEY    (Agent 主模型)"
        echo "    - OPENAI_API_KEY      (Embedding 模型)"
        echo ""
    else
        error ".env.example 文件也不存在，请手动创建 backend/.env"
        exit 1
    fi
else
    info ".env 文件已存在"
fi

# 安装 Python 依赖
info "检查 Python 依赖..."
if python -c "import fastapi" 2>/dev/null; then
    info "后端依赖已安装 (fastapi 已检测到)"
else
    info "正在安装后端依赖 (pip install -r requirements.txt)..."
    pip install -r requirements.txt -q
    info "后端依赖安装完成"
fi

# ============================================================
# 4. 前端依赖安装
# ============================================================
step "4/5  安装前端依赖..."

cd "$SCRIPT_DIR/frontend"

if [ -d node_modules ]; then
    info "前端依赖已安装 (node_modules 已存在)"
else
    info "正在安装前端依赖 (npm install)..."
    npm install
    info "前端依赖安装完成"
fi

# ============================================================
# 5. 启动服务
# ============================================================
step "5/5  启动前后端服务..."

echo ""
echo -e "${CYAN}========================================${NC}"
echo -e "  后端:  ${GREEN}http://localhost:8002${NC}"
echo -e "  前端:  ${GREEN}http://localhost:3000${NC}"
echo -e "  API:   ${GREEN}http://localhost:8002/docs${NC}"
echo -e "${CYAN}========================================${NC}"
echo ""
echo -e "  按 ${YELLOW}Ctrl+C${NC} 停止所有服务"
echo ""

# ---- 清理函数 ----
cleanup() {
    echo ""
    echo -e "${YELLOW}正在关闭服务...${NC}"
    if [ -n "${BACKEND_PID:-}" ] && kill -0 "$BACKEND_PID" 2>/dev/null; then
        kill "$BACKEND_PID" 2>/dev/null || true
        wait "$BACKEND_PID" 2>/dev/null || true
        info "后端已停止"
    fi
    if [ -n "${FRONTEND_PID:-}" ] && kill -0 "$FRONTEND_PID" 2>/dev/null; then
        kill "$FRONTEND_PID" 2>/dev/null || true
        wait "$FRONTEND_PID" 2>/dev/null || true
        info "前端已停止"
    fi
    # 清理可能残留的子进程
    if [ -n "${FRONTEND_PID:-}" ]; then
        # 杀掉 npm run dev 可能产生的 next dev 子进程
        pkill -P "$FRONTEND_PID" 2>/dev/null || true
    fi
    echo -e "${GREEN}所有服务已关闭，再见！${NC}"
    exit 0
}

trap cleanup INT TERM

# ---- 启动后端 ----
cd "$SCRIPT_DIR/backend"
conda activate "$MINICLAW_ENV"

# 创建必要的目录
mkdir -p sessions/archive storage/memory_index

info "正在启动后端服务 (uvicorn, port 8002)..."
python -m uvicorn app:app --port 8002 --host 0.0.0.0 --reload &
BACKEND_PID=$!

# 等待后端启动
sleep 2
if kill -0 "$BACKEND_PID" 2>/dev/null; then
    info "后端启动成功 (PID: $BACKEND_PID)"
else
    error "后端启动失败，请检查 backend/.env 配置是否正确"
    exit 1
fi

# ---- 启动前端 ----
cd "$SCRIPT_DIR/frontend"
info "正在启动前端服务 (Next.js, port 3000)..."
npm run dev &
FRONTEND_PID=$!

sleep 3
if kill -0 "$FRONTEND_PID" 2>/dev/null; then
    info "前端启动成功 (PID: $FRONTEND_PID)"
else
    error "前端启动失败，请检查 frontend/ 目录是否正确"
    # 杀掉后端
    kill "$BACKEND_PID" 2>/dev/null || true
    exit 1
fi

# ---- 自动打开浏览器 ----
sleep 1
if command -v open &>/dev/null; then
    info "正在打开浏览器..."
    open "http://localhost:3000" 2>/dev/null || true
fi

echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}  🚀 启动成功！${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo -e "  本机访问:   ${CYAN}http://localhost:3000${NC}"
LAN_IP=$(ipconfig getifaddr en0 2>/dev/null || echo 'YOUR_IP')
echo -e "  局域网访问: ${CYAN}http://${LAN_IP}:3000${NC}"
echo -e "  API 文档:   ${CYAN}http://localhost:8002/docs${NC}"
echo ""

# ---- 等待进程 ----
wait $BACKEND_PID $FRONTEND_PID 2>/dev/null || true
