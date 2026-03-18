"""技能目录扫描器"""
from pathlib import Path
from typing import List, Dict
import re


def scan_skills(base_dir: Path) -> List[Dict[str, str]]:
    """扫描 skills 目录下的所有技能
    
    Args:
        base_dir: 项目根目录
        
    Returns:
        技能列表，每个技能包含 name, description, location
    """
    skills_dir = base_dir / "skills"
    if not skills_dir.exists():
        return []
    
    skills = []
    
    # 遍历所有子目录，查找 SKILL.md
    for skill_file in skills_dir.glob("**/SKILL.md"):
        try:
            # 读取文件内容
            with open(skill_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 解析 frontmatter
            frontmatter = _parse_frontmatter(content)
            
            if frontmatter and 'name' in frontmatter:
                # 计算相对路径
                relative_path = skill_file.relative_to(base_dir).as_posix()
                
                skills.append({
                    'name': frontmatter.get('name', '未命名技能'),
                    'description': frontmatter.get('description', '无描述'),
                    'location': f"./{relative_path}",
                })
        except Exception as e:
            print(f"警告：读取技能文件失败 {skill_file}: {e}")
    
    return skills


def _parse_frontmatter(content: str) -> Dict[str, str]:
    """解析 YAML frontmatter
    
    Args:
        content: Markdown 文件内容
        
    Returns:
        frontmatter 字典
    """
    # 匹配 YAML frontmatter（--- ... ---）
    match = re.match(r'^---\s*\n(.*?)\n---\s*\n', content, re.DOTALL)
    if not match:
        return {}
    
    yaml_content = match.group(1)
    frontmatter = {}
    
    # 简单的 YAML 解析（只支持 key: value 格式）
    for line in yaml_content.split('\n'):
        line = line.strip()
        if ':' in line:
            key, value = line.split(':', 1)
            frontmatter[key.strip()] = value.strip()
    
    return frontmatter


def generate_skills_snapshot(base_dir: Path) -> str:
    """生成技能快照文件
    
    Args:
        base_dir: 项目根目录
        
    Returns:
        快照内容
    """
    skills = scan_skills(base_dir)
    
    if not skills:
        return "<available_skills>\n  <!-- 暂无可用技能 -->\n</available_skills>"
    
    # 生成 XML 格式的快照
    lines = ["<available_skills>"]
    
    for skill in skills:
        lines.append("  <skill>")
        lines.append(f"    <name>{_escape_xml(skill['name'])}</name>")
        lines.append(f"    <description>{_escape_xml(skill['description'])}</description>")
        lines.append(f"    <location>{_escape_xml(skill['location'])}</location>")
        lines.append("  </skill>")
    
    lines.append("</available_skills>")
    
    return '\n'.join(lines)


def _escape_xml(text: str) -> str:
    """转义 XML 特殊字符"""
    text = text.replace('&', '&amp;')
    text = text.replace('<', '&lt;')
    text = text.replace('>', '&gt;')
    text = text.replace('"', '&quot;')
    text = text.replace("'", '&apos;')
    return text


def update_skills_snapshot(base_dir: Path) -> None:
    """更新 SKILLS_SNAPSHOT.md 文件
    
    Args:
        base_dir: 项目根目录
    """
    snapshot_content = generate_skills_snapshot(base_dir)
    snapshot_file = base_dir / "SKILLS_SNAPSHOT.md"
    
    with open(snapshot_file, 'w', encoding='utf-8') as f:
        f.write(snapshot_content)
    
    print(f"✓ 技能快照已更新: {snapshot_file}")
