"""
GET /skills —— 列出所有已注册的 Skill
GET /skills/search?q=... —— 关键词搜索 Skill
GET /skills/{name} —— 取单个 Skill 元信息
POST /skills/scan —— 扫描并注册指定目录下的 Skills
POST /skills/register —— 注册单个 Skill 目录
DELETE /skills/{name} —— 取消注册 Skill
POST /skills/{name}/reload —— 重载 SKILL.md
POST /skills/{name}/as-tool —— 把 Skill 注册为可调用的 Tool
DELETE /skills/{name}/as-tool —— 取消注册 Skill-as-tool
"""

from __future__ import annotations

from pathlib import Path
from typing import List

import dumplingsAI
from fastapi import APIRouter, HTTPException

from ..models import (
    SkillInfo,
    SkillListResponse,
    SkillRegisterRequest,
    SkillScanRequest,
)

router = APIRouter(prefix="/skills", tags=["skills"])


def _skill_to_info(skill) -> SkillInfo:
    """从 Skill 对象提取元信息，返回 SkillInfo"""
    d = skill.to_dict() if hasattr(skill, "to_dict") else {}
    return SkillInfo(
        name=getattr(skill, "name", "") or d.get("name", ""),
        description=getattr(skill, "description", "") or d.get("description"),
        path=d.get("skill_dir"),
        tags=[],  # 暂无 tag 字段
    )


@router.get("", response_model=SkillListResponse)
async def list_skills() -> SkillListResponse:
    """列出全部已注册的 Skill"""
    raw = dumplingsAI.skill_registry.list_skills() or []
    items = [_skill_to_info(s) for s in raw]
    return SkillListResponse(skills=items, total=len(items))


@router.get("/search", response_model=SkillListResponse)
async def search_skills(q: str = "") -> SkillListResponse:
    """关键词搜索 Skill（在 name / description / context 中匹配）"""
    raw = dumplingsAI.skill_registry.search_skills(q) or []
    items = [_skill_to_info(s) for s in raw]
    return SkillListResponse(skills=items, total=len(items))


@router.get("/{name}")
async def get_skill(name: str) -> dict:
    skill = dumplingsAI.skill_registry.get_skill(name)
    if skill is None:
        raise HTTPException(status_code=404, detail=f"Skill 不存在：{name!r}")
    return skill.to_dict() if hasattr(skill, "to_dict") else {}


@router.post("/scan", response_model=SkillListResponse)
async def scan_skills(req: SkillScanRequest) -> SkillListResponse:
    """扫描指定目录列表，注册其中所有 Skills"""
    paths = [Path(p) for p in req.paths]
    dumplingsAI.skill_registry.scan_and_register(paths, auto_watch=False)
    raw = dumplingsAI.skill_registry.list_skills() or []
    items = [_skill_to_info(s) for s in raw]
    return SkillListResponse(skills=items, total=len(items))


@router.post("/register", response_model=SkillListResponse)
async def register_skill(req: SkillRegisterRequest) -> SkillListResponse:
    """注册单个 Skill 目录"""
    path = Path(req.path)
    if not path.exists():
        raise HTTPException(status_code=400, detail=f"路径不存在：{path}")
    skill = dumplingsAI.skill_registry.register_skill(path)
    if skill is None:
        raise HTTPException(status_code=400, detail=f"注册失败：{path}（目录里没 SKILL.md？）")
    raw = dumplingsAI.skill_registry.list_skills() or []
    items = [_skill_to_info(s) for s in raw]
    return SkillListResponse(skills=items, total=len(items))


@router.delete("/{name}")
async def unregister_skill(name: str) -> dict:
    """取消注册 Skill"""
    dumplingsAI.skill_registry.unregister_skill(name)
    return {"status": "ok", "name": name}


@router.post("/{name}/reload")
async def reload_skill(name: str) -> dict:
    """重载 SKILL.md"""
    skill = dumplingsAI.skill_registry.get_skill(name)
    if skill is None:
        raise HTTPException(status_code=404, detail=f"Skill 不存在：{name!r}")
    skill.reload()
    return {"status": "ok", "name": name}


@router.post("/{name}/as-tool")
async def register_skill_as_tool(name: str) -> dict:
    """把 Skill 注册为可调用的 Tool（让 Agent 可以 function-call 它）"""
    try:
        dumplingsAI.register_skill_as_tool(name)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    return {"status": "ok", "name": name}


@router.delete("/{name}/as-tool")
async def unregister_skill_as_tool(name: str) -> dict:
    """取消 Skill-as-tool"""
    try:
        dumplingsAI.unregister_skill_from_tool(name)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    return {"status": "ok", "name": name}