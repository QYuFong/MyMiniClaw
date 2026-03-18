"""文件管理 API"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any
from pathlib import Path

from graph.agent import agent_manager


router = APIRouter()


class SaveFileRequest(BaseModel):
    """保存文件请求"""
    path: str
    content: str


# 允许的路径前缀
ALLOWED_PREFIXES = [
    "workspace/",
    "memory/",
    "skills/",
    "knowledge/",
]

# 允许的根目录文件
ALLOWED_ROOT_FILES = [
    "SKILLS_SNAPSHOT.md"
]


def _is_path_allowed(path: str) -> bool:
    """检查路径是否在白名单内"""
    # 路径遍历检测
    if ".." in path:
        return False
    
    # 检查前缀
    for prefix in ALLOWED_PREFIXES:
        if path.startswith(prefix):
            return True
    
    # 检查根文件
    if path in ALLOWED_ROOT_FILES:
        return True
    
    return False


@router.get("/files")
async def read_file(path: str) -> Dict[str, str]:
    """读取文件内容
    
    Query:
        path: 相对于项目根目录的文件路径
    """
    # 安全检查
    if not _is_path_allowed(path):
        raise HTTPException(status_code=403, detail="不允许访问此路径")
    
    file_path = agent_manager.base_dir / path
    
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="文件不存在")
    
    if not file_path.is_file():
        raise HTTPException(status_code=400, detail="路径不是文件")
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        return {"content": content}
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"读取文件失败: {str(e)}")


@router.post("/files")
async def save_file(request: SaveFileRequest) -> Dict[str, str]:
    """保存文件内容"""
    # 安全检查
    if not _is_path_allowed(request.path):
        raise HTTPException(status_code=403, detail="不允许访问此路径")
    
    file_path = agent_manager.base_dir / request.path
    
    # 确保父目录存在
    file_path.parent.mkdir(parents=True, exist_ok=True)
    
    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(request.content)
        
        # 如果是 MEMORY.md，触发重建索引
        if request.path == "memory/MEMORY.md":
            agent_manager.memory_indexer.rebuild_index()
        
        return {"status": "success"}
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"保存文件失败: {str(e)}")


@router.get("/skills")
async def list_skills() -> List[Dict[str, Any]]:
    """列出可用技能"""
    from tools.skills_scanner import scan_skills
    
    skills = scan_skills(agent_manager.base_dir)
    return skills
