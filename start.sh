#!/bin/bash

echo "========================================"
echo "Mini-OpenClaw 启动脚本"
echo "========================================"
echo ""

# 检查 Python
if ! command -v python3 &> /dev/null; then
    echo "[错误] 未找到 Python，请先安装 Python 3.10+"
    exit 1
fi

# 检查 Node.js
if ! command -v node &> /dev/null; then
    echo "[错误] 未找到 Node.js，请先安装 Node.js 18+"
    exit 1
fi

echo "[1/4] 检查后端环境..."
cd backend
if [ ! -f .env ]; then
    echo "[警告] 未找到 .env 文件，请先配置环境变量"
    echo "运行: cp .env.example .env"
    echo "然后编辑 .env 文件填入你的 API Keys"
    exit 1
fi

echo "[2/4] 安装后端依赖（如需要）..."
pip3 install -r requirements.txt

echo "[3/4] 安装前端依赖（如需要）..."
cd ../frontend
if [ ! -d node_modules ]; then
    echo "正在安装前端依赖..."
    npm install
fi

echo "[4/4] 启动服务..."
echo ""
echo "========================================"
echo "后端将在端口 8002 启动"
echo "前端将在端口 3000 启动"
echo "========================================"
echo ""

# 启动后端（后台）
cd ../backend
python3 -m uvicorn app:app --port 8002 --host 0.0.0.0 --reload &
BACKEND_PID=$!

# 等待 2 秒
sleep 2

# 启动前端（后台）
cd ../frontend
npm run dev &
FRONTEND_PID=$!

echo ""
echo "========================================"
echo "启动完成！"
echo ""
echo "本机访问: http://localhost:3000"
echo "局域网访问: http://你的IP:3000"
echo ""
echo "按 Ctrl+C 停止服务"
echo "========================================"

# 等待任意进程结束
wait $BACKEND_PID $FRONTEND_PID
