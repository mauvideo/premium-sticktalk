#!/usr/bin/env python3
"""Đọc cấu hình Project/Template và xuất biến môi trường cho pipeline."""

from __future__ import annotations

import argparse
import json
import shlex
from pathlib import Path


def load_template(project: str, template_id: str) -> dict:
    path = Path("projects") / project / "templates.json"
    if not path.is_file():
        raise SystemExit(f"Project không tồn tại: {project}")
    data = json.loads(path.read_text(encoding="utf-8"))
    selected = template_id or data.get("default_template", "")
    for item in data.get("templates", []):
        if item.get("id") == selected:
            return item
    available = ", ".join(item.get("id", "") for item in data.get("templates", []))
    raise SystemExit(f"Mẫu '{selected}' không tồn tại trong project '{project}'. Các mẫu: {available}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project", default="motivation")
    parser.add_argument("--template", default="prompt-to-video")
    parser.add_argument("--format", choices=["shell", "json"], default="shell")
    args = parser.parse_args()

    item = load_template(args.project, args.template)
    result = {
        "VIDEO_PROJECT": args.project,
        "VIDEO_TEMPLATE": item["id"],
        "VIDEO_STYLE": item["style"],
        "VIDEO_MOTION_LEVEL": item["motion_level"],
        "VIDEO_SCRIPT_MODE": item["script_mode"],
        "VIDEO_WRITING_STYLE": item["writing_style"],
        "VIDEO_TEMPLATE_SOURCE": item["source"],
        "VIDEO_TEMPLATE_LICENSE": item["license"],
    }
    if args.format == "json":
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        for key, value in result.items():
            print(f"export {key}={shlex.quote(str(value))}")


if __name__ == "__main__":
    main()
