"""FastAPI 应用入口"""
import sys
import logging
from contextlib import asynccontextmanager
from pathlib import Path
from datetime import datetime

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
import time

import config as global_config
from graph.agent import agent_manager
from tools.skills_scanner import update_skills_snapshot

from api import chat, sessions, files, tokens, compress, config_api


# 配置日志 - 同时输出到文件和控制台
log_file = Path(__file__).parent / "debug.log"
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file, encoding='utf-8'),
        logging.StreamHandler(sys.stderr)
    ]
)
logger = logging.getLogger(__name__)

# 额外的文件日志函数，直接写入文件确保可见
def log_to_file(msg: str):
    """直接写入日志文件"""
    try:
        with open(log_file, 'a', encoding='utf-8') as f:
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            f.write(f"[{timestamp}] {msg}\n")
            f.flush()
    except:
        pass


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时初始化
    base_dir = Path(__file__).parent
    
    print("=" * 50)
    print("Mini-OpenClaw 正在启动...")
    print("=" * 50)
    
    # 1. 初始化配置
    global_config.init_config(base_dir)
    print("✓ 配置已加载")
    
    # 2. 扫描技能并生成快照
    update_skills_snapshot(base_dir)
    
    # 3. 初始化 Agent
    agent_manager.initialize(base_dir)
    
    # 4. 构建 MEMORY.md 索引
    print("正在构建 MEMORY.md 索引...")
    agent_manager.memory_indexer.rebuild_index()
    
    print("=" * 50)
    print("✓ Mini-OpenClaw 启动完成！")
    print(f"✓ 后端服务运行在: http://localhost:8002")
    print("=" * 50)
    
    yield
    
    # 关闭时清理
    print("Mini-OpenClaw 正在关闭...")


# 创建应用
app = FastAPI(
    title="Mini-OpenClaw",
    description="轻量级全透明 AI Agent 系统",
    version="1.0.0",
    lifespan=lifespan
)

# 配置 CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境应该限制具体域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# 添加请求日志中间件
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """记录所有请求"""
    start_time = time.time()
    
    msg = f"\n{'='*60}\n[REQUEST] {request.method} {request.url.path}\n[REQUEST] Client: {request.client.host if request.client else 'unknown'}\n{'='*60}\n"
    logger.info(msg)
    log_to_file(msg)
    
    response = await call_next(request)
    
    process_time = time.time() - start_time
    result_msg = f"\n[RESPONSE] Status: {response.status_code}, Time: {process_time:.3f}s\n"
    logger.info(result_msg)
    log_to_file(result_msg)
    
    return response

# 注册路由
app.include_router(chat.router, prefix="/api", tags=["Chat"])
app.include_router(sessions.router, prefix="/api", tags=["Sessions"])
app.include_router(files.router, prefix="/api", tags=["Files"])
app.include_router(tokens.router, prefix="/api", tags=["Tokens"])
app.include_router(compress.router, prefix="/api", tags=["Compress"])
app.include_router(config_api.router, prefix="/api", tags=["Config"])


@app.get("/")
async def root():
    """根路径"""
    return {
        "name": "Mini-OpenClaw",
        "version": "1.0.0",
        "status": "running"
    }


@app.get("/health")
async def health():
    """健康检查"""
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app:app",
        host="0.0.0.0",
        port=8002,
        reload=True
    )
