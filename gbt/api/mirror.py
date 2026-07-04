"""GBT Pro · gbt/api/mirror.py · 由 desktop_app.py 机械拆分
──────────────────────────────────────────────
蓝图归属：mirror
所有 @app.route 已改写为 @bp.route，函数体保持原样。
"""

# 开发者: 自由的风
from flask import Blueprint, jsonify, request, render_template_string
import os, json, time
bp = Blueprint("mirror", __name__)


@bp.route("/api/mirror/status")
def api_mirror_status():
    try:
        from gbt.mirror_space import status as _ms, active_skill_doc
        info = _ms()
        info["doc"] = active_skill_doc()
        return jsonify({"ok": True, "info": info})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)[:200]})



@bp.route("/api/mirror/skills")
def api_mirror_skills():
    """列出可用主动技能 + 模块清单 + 最新 review 报告"""
    try:
        from gbt.mirror_space import list_modules, latest_report, status as _ms
        return jsonify({
            "ok": True,
            "skills": _ms().get("skills", []),
            "modules": list_modules(),
            "latest_report": latest_report(),
        })
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)[:200]})



@bp.route("/api/mirror/invoke", methods=["POST"])
def api_mirror_invoke():
    """执行某个 mirror skill（full/evolve/canary/rollback/...）。所有动作默认 dry-run=true"""
    payload = request.json or {}
    skill = (payload.get("skill") or "status").strip()
    project = payload.get("project")
    dry_run = bool(payload.get("dry_run", True))
    extra = payload.get("extra", payload.get("params", {})) or {}
    try:
        from gbt.mirror_space import (
            invoke_skill, build_module_registry, evolve, pipeline,
            safe_dry_run, status as _ms,
        )
        if skill == "status":
            return jsonify({"ok": True, "result": _ms()})
        if skill == "build-registry":
            r = build_module_registry(project)
        elif skill == "evolve":
            r = evolve(project, dry_run=dry_run, rounds=int(extra.get("rounds", 1)))
        elif skill == "pipeline":
            r = pipeline(project, dry_run=dry_run)
        elif skill == "dry-run":
            r = safe_dry_run(project)
        elif skill in {"full", "canary", "rollback", "monitor", "validate", "rollback-drill"}:
            opts = dict(extra)
            if dry_run:
                opts["dry_run"] = True
            r = invoke_skill(skill, project, **opts)
        else:
            return jsonify({"ok": False, "error": "unknown skill: " + skill}), 400
        body = {"ok": bool(getattr(r, "ok", False)), "skill": skill, "dry_run": dry_run, "result": r.to_dict()}
        if not body["ok"]:
            body["error"] = body["result"].get("logs") or body["result"].get("result", {}).get("reason") or "mirror invoke failed"
        return jsonify(body)
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)[:200]})

# ── 部署面板（原子替换的"回滚触发开关"对外暴露） ──
