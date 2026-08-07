#!/usr/bin/env python3
"""Topic-driven visual planner for Vox paper-collage scenes."""
from __future__ import annotations

import re

PAPER = ["newspaper", "torn paper", "marker", "highlight", "tape", "stamp"]
CAMERAS = ["push", "pan left", "pan right", "parallax", "soft rotate", "slide"]
TRANSITIONS = ["paper slide", "paper reveal", "card stack", "mask reveal", "wipe", "cut"]
COMPOSITIONS = [
    "subject-left with evidence-right", "subject-right with map-left",
    "center cutout with document stack", "diagonal archival collage",
    "timeline foreground with portrait background", "map route with cutout subject",
]

ICON_RULES = [
    ({"gym", "tạ", "tập", "cơ", "weight"}, "dumbbell"),
    ({"tim", "nhịp", "sức", "khỏe"}, "heart"),
    ({"điện", "thoại", "gọi"}, "phone"),
    ({"đi", "bộ", "chạy", "khởi", "động"}, "walk"),
    ({"nước", "uống"}, "water"),
    ({"ăn", "bữa", "dinh", "dưỡng"}, "food"),
    ({"ngủ", "nghỉ"}, "sleep"),
    ({"bản", "đồ", "địa", "điểm", "quốc", "gia"}, "map"),
    ({"năm", "thời", "giai", "đoạn", "lịch", "sử"}, "timeline"),
    ({"tài", "liệu", "hồ", "sơ", "thư", "báo"}, "document"),
    ({"quân", "đội", "tướng", "chiến", "trận", "binh"}, "military"),
    ({"nhà", "máy", "sản", "xuất", "công", "nghiệp"}, "factory"),
    ({"xe", "ô", "tô"}, "car"),
    ({"tàu", "biển", "đại", "dương"}, "ship"),
    ({"máy", "bay", "hàng", "không"}, "airplane"),
    ({"sách", "học", "giáo", "dục"}, "book"),
    ({"biểu", "đồ", "tăng", "giảm", "số", "liệu"}, "chart"),
    ({"thành", "phố", "đô", "thị", "tòa", "nhà"}, "building"),
    ({"người", "nhân", "vật", "chân", "dung"}, "person"),
]

ALLOWED_ICON_HINTS = {
    "dumbbell","gym","heart","phone","walk","water","food","sleep","brain","computer","laptop",
    "map","timeline","clock","timer","document","military","factory","car","ship","airplane","plane",
    "book","chart","building","landmark","person"
}


def _tokens(text: str) -> set[str]:
    return set(re.findall(r"[\wÀ-ỹ]+", text.casefold()))


def _pick(options: list[str], seed: int) -> str:
    return options[seed % len(options)]


def _semantic_icons(tokens: set[str], evidence: list[str]) -> list[str]:
    joined = tokens | _tokens(" ".join(evidence))
    icons: list[str] = []
    for required, icon in ICON_RULES:
        if required & joined and icon not in icons:
            icons.append(icon)
    return icons[:2]


def _scene_icons(scene: dict, tokens: set[str], evidence: list[str]) -> list[str]:
    ai=[]
    for raw in scene.get("icons") or []:
        v=str(raw).strip().casefold()
        if not v: continue
        # Chỉ giữ keyword có thể ánh xạ sang Lucide; icon lạ bị bỏ thay vì hiện dấu hỏi.
        if any(h in v for h in ALLOWED_ICON_HINTS) and v not in ai:
            ai.append(v)
    return (ai or _semantic_icons(tokens,evidence))[:2]


def create_visual_plan(scene: dict, story: dict, scene_index: int) -> dict:
    narration = str(scene.get("narration") or scene.get("loi_dan") or "")
    text = " ".join(str(scene.get(k, "")) for k in ("narration", "loi_dan", "sceneRole", "storyProgress", "imageFocus", "headline"))
    tokens = _tokens(text + " " + str(story.get("title") or story.get("tieu_de", "")))
    seed = int(scene.get("seed") or (scene_index + 1) * 97)
    entity = scene.get("entityVisualPlan") or {}
    global_entities = story.get("entityVisualPlan") or {}
    evidence = [str(x) for x in (entity.get("visualEvidence") or []) if x]
    maps = list(global_entities.get("mapsNeeded") or [])
    charts = list(global_entities.get("chartsNeeded") or [])
    time_period = str(entity.get("timePeriod") or "")
    event = str(entity.get("event") or "")
    location = str(entity.get("location") or "")

    narration_norm = narration.casefold()
    data_layers = []
    if maps and location and location.casefold() in narration_norm:
        data_layers.append({"type": "map", "label": maps[0]})
    if charts and ({"số", "liệu", "tăng", "giảm", "%", "phần", "trăm"} & tokens):
        data_layers.append({"type": "chart", "label": charts[scene_index % len(charts)]})
    if time_period and time_period in narration:
        data_layers.append({"type": "timeline", "label": time_period})
    if not data_layers and event:
        data_layers.append({"type": "evidence", "label": event})

    secondary = [x for x in [event, location, *evidence] if x]

    return {
        "background": "archival paper collage",
        "mainCharacter": entity.get("mainSubject") or story.get("title") or "documentary subject",
        "secondaryObjects": secondary[:3],
        "icons": _scene_icons(scene,tokens,secondary),
        "paperElements": [_pick(PAPER, seed + scene_index), _pick(PAPER, seed + scene_index + 2)],
        "camera": _pick(CAMERAS, seed + scene_index),
        "transition": _pick(TRANSITIONS, seed + scene_index),
        "highlight": event or scene.get("imageFocus") or scene.get("sceneRole") or "Dữ kiện chính",
        "mood": "documentary",
        "colorPalette": "cream black yellow red",
        "composition": _pick(COMPOSITIONS, seed + scene_index),
        "dataLayers": data_layers[:3],
        "location": location,
        "timePeriod": time_period,
        "layerContract": entity.get("assetRoles") or [
            "paper-background", "print-texture", "main-subject", "context-photo",
            "semantic-icon", "map-chart-timeline", "annotation", "typography",
        ],
    }


def apply_visual_plans(story: dict) -> dict:
    used_compositions: set[str] = set()
    for index, scene in enumerate(story.get("scenes", [])):
        plan = create_visual_plan(scene, story, index)
        base = plan["composition"]
        if base in used_compositions:
            plan["composition"] = f"{base} variant {index + 1}"
        used_compositions.add(plan["composition"])
        scene["visualPlan"] = plan
    return story
