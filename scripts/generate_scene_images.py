#!/usr/bin/env python3
"""Tạo một ảnh AI riêng cho từng cảnh và ghi đường dẫn vào story.json.

Dùng API hình ảnh mã nguồn mở Pollinations. Khóa API là tùy chọn qua
POLLINATIONS_API_KEY; tuyệt đối không lưu khóa trong kho mã nguồn.
"""
from __future__ import annotations

import json
import os
import re
import time
from pathlib import Path
from urllib.parse import quote
from urllib.request import Request, urlopen

STYLES = {
    "prompt-to-video": "cinematic motivational photography, dramatic natural light, realistic, emotional, vertical composition",
    "kinetic-captions": "bold editorial poster background, high contrast, clean negative space, modern motivational visual, vertical composition",
    "smooth-transitions": "cinematic dreamy scene, layered depth, soft light, elegant gradients, realistic, vertical composition",
    "paper-sketch": "hand-drawn pencil sketch on warm ivory textured paper, graphite shading, vintage book illustration, handmade, vertical composition",
    "business-motivation": "premium business documentary photography, confident professional atmosphere, dark charcoal and warm gold lighting, realistic, vertical composition",
    "paper-cut": "layered paper-cut illustration, handmade cut paper edges, soft paper shadows, tactile craft texture, vertical composition",
}


def clean(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def prompt_for(scene: dict, title: str, template: str) -> str:
    narration = clean(scene.get("narration") or scene.get("loi_dan") or title)
    headline = clean(scene.get("headline") or title)
    style = STYLES.get(template, STYLES["prompt-to-video"])
    return (
        f"Create a visual scene illustrating this Vietnamese motivational message: {narration}. "
        f"Core idea: {headline}. {style}. No text, no letters, no logo, no watermark. "
        "Strong subject, clear storytelling, suitable for a 9:16 short video."
    )


def download_image(prompt: str, target: Path, seed: int, api_key: str) -> None:
    encoded = quote(prompt, safe="")
    url = f"https://gen.pollinations.ai/image/{encoded}?width=1080&height=1920&seed={seed}&model=flux"
    if api_key:
        url += f"&key={quote(api_key, safe='')}"
    request = Request(url, headers={"User-Agent": "Premium-StickTalk/1.0"})
    last_error: Exception | None = None
    for attempt in range(3):
        try:
            with urlopen(request, timeout=180) as response:
                data = response.read()
                content_type = response.headers.get("Content-Type", "")
            if len(data) < 10_000 or "image" not in content_type:
                raise RuntimeError(f"Phản hồi tạo ảnh không hợp lệ: {content_type}, {len(data)} byte")
            target.write_bytes(data)
            return
        except Exception as error:  # noqa: BLE001
            last_error = error
            if attempt < 2:
                time.sleep(5 * (attempt + 1))
    raise RuntimeError(f"Không tạo được ảnh {target.name}: {last_error}")


def main() -> None:
    story_path = Path("assets/story.json")
    if not story_path.is_file():
        raise SystemExit("Không tìm thấy assets/story.json")

    story = json.loads(story_path.read_text(encoding="utf-8"))
    scenes = story.get("scenes") or story.get("canh") or []
    if not scenes:
        raise SystemExit("Kịch bản không có cảnh để tạo ảnh")

    title = clean(story.get("title") or "Video truyền cảm hứng")
    template = os.getenv("VIDEO_TEMPLATE", story.get("template") or "prompt-to-video")
    api_key = os.getenv("POLLINATIONS_API_KEY", "").strip()
    out_dir = Path("assets/generated-images")
    out_dir.mkdir(parents=True, exist_ok=True)

    manifest = []
    for index, scene in enumerate(scenes, start=1):
        prompt = prompt_for(scene, title, template)
        filename = f"scene-{index:02d}.jpg"
        target = out_dir / filename
        seed = abs(hash(f"{title}|{index}|{template}")) % 2_147_483_647
        print(f"Đang tạo ảnh AI cho cảnh {index}/{len(scenes)}: {filename}")
        download_image(prompt, target, seed, api_key)
        public_path = f"assets/generated-images/{filename}"
        scene["image"] = public_path
        scene["imagePrompt"] = prompt
        manifest.append({"scene": index, "file": public_path, "prompt": prompt})

    story["scenes"] = scenes
    story["imageProvider"] = "pollinations-flux"
    story_path.write_text(json.dumps(story, ensure_ascii=False, indent=2), encoding="utf-8")
    Path("output").mkdir(exist_ok=True)
    Path("output/image-manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"Đã tạo {len(scenes)} ảnh AI, mỗi cảnh một ảnh riêng.")


if __name__ == "__main__":
    main()
