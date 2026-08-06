#!/usr/bin/env python3
"""Rule-based Visual Planner Engine for scene-level visual design briefs."""
from __future__ import annotations

import re

BACKGROUNDS = ["office", "city", "mountain", "street", "school", "factory", "library", "coffee shop", "studio", "meeting room", "home"]
CHARACTERS = ["teacher", "engineer", "student", "doctor", "business owner", "worker", "chef", "runner", "designer", "shop owner", "researcher"]
OBJECTS = ["book", "desk", "lamp", "coffee", "window", "clock", "laptop", "notebook", "calendar", "toolbox", "backpack"]
SUCCESS_ICONS = ["target", "arrow", "medal", "graph", "star"]
FAILURE_ICONS = ["warning", "broken chain", "red arrow", "clock", "alert"]
PAPER = ["tape", "sticky note", "paper", "paper tear", "mask", "frame", "marker", "highlight", "arrow"]
CAMERAS = ["push", "pull", "pan left", "pan right", "floating", "parallax", "soft rotate", "slide"]
TRANSITIONS = ["paper slide", "paper reveal", "card stack", "mask reveal", "wipe", "cut"]
PALETTES = ["warm paper", "deep blue gold", "soft green", "charcoal yellow", "cream ink", "muted city"]
COMPOSITIONS = ["foreground character with object cluster", "split foreground and background", "diagonal paper layers", "center subject with side icons", "wide background with lower-third story text", "collage stack with arrow path"]

def _tokens(text: str) -> set[str]:
    return set(re.findall(r"[\wÀ-ỹ]+", text.casefold()))

def _pick(options: list[str], seed: int) -> str:
    return options[seed % len(options)]

def _character(tokens: set[str], seed: int) -> str:
    if {"học", "lớp", "trường"} & tokens: return "student"
    if {"bác", "sức", "khỏe"} & tokens: return "doctor"
    if {"cửa", "hàng", "kinh", "doanh", "khách"} & tokens: return "business owner"
    if {"bếp", "món", "ăn"} & tokens: return "chef"
    if {"chạy", "đường", "đua"} & tokens: return "runner"
    return _pick(CHARACTERS, seed)

def _background(tokens: set[str], seed: int) -> str:
    if {"học", "lớp", "trường"} & tokens: return "school"
    if {"sách", "đọc", "nghiên", "cứu"} & tokens: return "library"
    if {"cửa", "hàng", "họp", "lương"} & tokens: return "meeting room"
    if {"núi", "đường", "hành", "trình"} & tokens: return "mountain"
    return _pick(BACKGROUNDS, seed)

def create_visual_plan(scene: dict, story: dict, scene_index: int) -> dict:
    text = " ".join(str(scene.get(k, "")) for k in ("narration", "loi_dan", "sceneRole", "storyProgress", "imageFocus"))
    tokens = _tokens(text + " " + str(story.get("title") or story.get("tieu_de", "")))
    seed = int(scene.get("seed") or (scene_index + 1) * 97)
    icons = FAILURE_ICONS if {"khó", "thất", "bại", "rắc", "xung", "đột"} & tokens else SUCCESS_ICONS
    entity = scene.get("entityVisualPlan") or {}
    global_entities = story.get("entityVisualPlan") or {}
    evidence = list(entity.get("visualEvidence") or [])
    maps = list(global_entities.get("mapsNeeded") or [])
    charts = list(global_entities.get("chartsNeeded") or [])
    time_period = str(entity.get("timePeriod") or "")
    data_layers = ([{"type": "map", "label": maps[scene_index % len(maps)]}] if maps else [])
    data_layers += ([{"type": "chart", "label": charts[scene_index % len(charts)]}] if charts else [])
    if time_period:
        data_layers.append({"type": "timeline", "label": time_period})
    if not data_layers:
        data_layers.append({"type": "evidence", "label": entity.get("event") or "Dữ kiện chính"})
    plan = {
        "background": _background(tokens, seed + scene_index),
        "mainCharacter": entity.get("mainSubject") or _character(tokens, seed + scene_index * 2),
        "secondaryObjects": (evidence or [_pick(OBJECTS, seed + scene_index), _pick(OBJECTS, seed + scene_index + 3)])[:2],
        "icons": [_pick(icons, seed + scene_index), _pick(icons, seed + scene_index + 2)],
        "paperElements": [_pick(PAPER, seed + scene_index), _pick(PAPER, seed + scene_index + 4)],
        "camera": _pick(CAMERAS, seed + scene_index),
        "transition": _pick(TRANSITIONS, seed + scene_index),
        "highlight": scene.get("imageFocus") or scene.get("sceneRole") or "key story detail",
        "mood": "tense" if int(scene.get("dramaticLevel", 50)) >= 80 else "focused" if int(scene.get("dramaticLevel", 50)) >= 55 else "calm",
        "colorPalette": _pick(PALETTES, seed + scene_index),
        "composition": _pick(COMPOSITIONS, seed + scene_index),
        "dataLayers": data_layers[:3],
        "location": entity.get("location", ""),
        "timePeriod": time_period,
        "layerContract": entity.get("assetRoles") or ["paper-background", "texture", "main-subject", "context-evidence", "data-map-icon", "annotation", "typography"],
    }
    return plan

def apply_visual_plans(story: dict) -> dict:
    used_compositions: set[str] = set()
    for index, scene in enumerate(story.get("scenes", [])):
        plan = create_visual_plan(scene, story, index)
        base_composition = plan["composition"]
        if plan["composition"] in used_compositions:
            plan["composition"] = f"{base_composition} variant {index + 1}"
        while plan["composition"] in used_compositions:
            plan["composition"] = f"{base_composition} variant {index + 1}-{len(used_compositions)}"
        used_compositions.add(plan["composition"])
        scene["visualPlan"] = plan
    return story
