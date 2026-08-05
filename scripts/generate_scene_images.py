#!/usr/bin/env python3
"""Tạo ảnh AI riêng cho từng cảnh bằng OpenAI GPT Image 2.

Luồng xử lý:
1. Đọc các cảnh trong assets/story.json.
2. Tạo prompt ảnh từ nội dung từng cảnh và mẫu video đã chọn.
3. Gọi OpenAI Images API để sinh ảnh dọc 1024x1536.
4. Ghi đường dẫn ảnh và thông tin model vào story.json + output/image-manifest.json.

Tệp này không sửa và không phụ thuộc vào VieNeu-TTS.
"""
from __future__ import annotations

import base64
import hashlib
import json
import os
import re
import time
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

OPENAI_IMAGE_MODEL = os.getenv("OPENAI_IMAGE_MODEL", "gpt-image-2")
OPENAI_IMAGE_QUALITY = os.getenv("OPENAI_IMAGE_QUALITY", "low")

STYLES = {
    "prompt-to-video": "cinematic realistic photography, dramatic natural light, emotional storytelling",
    "kinetic-captions": "modern editorial visual, high contrast, bold composition, clean negative space",
    "smooth-transitions": "cinematic dreamy scene, layered depth, soft light, elegant atmosphere",
    "paper-sketch": "hand-drawn pencil sketch on warm ivory textured paper, vintage book illustration",
    "business-motivation": "premium business documentary photography, professional, charcoal and warm gold lighting",
    "paper-cut": "layered paper-cut illustration, handmade edges, tactile paper texture and soft shadows",
}


def clean(value: str) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def build_prompt(scene: dict, title: str, template: str, index: int, total: int) -> str:
    narration = clean(scene.get("narration") or scene.get("loi_dan") or title)
    headline = clean(scene.get("headline") or title)
    style = STYLES.get(template, STYLES["prompt-to-video"])
    return (
        f"Create scene {index} of {total} for a vertical Vietnamese motivational short video. "
        f"Main message: {narration}. Core idea: {headline}. "
        f"Visual style: {style}. Vertical 9:16 composition, strong subject, clear story, "
        "natural human anatomy, professional lighting, suitable for subtle camera movement. "
        "Do not include any text, letters, captions, logos, watermarks, user interface, borders, or mockups."
    )


def create_image(prompt: str, target: Path, api_key: str) -> dict:
    if not api_key:
        raise RuntimeError(
            "Thiếu OPENAI_API_KEY. Hãy thêm Secret OPENAI_API_KEY trong Settings → Secrets and variables → Actions."
        )

    endpoint = "https://api.openai.com/v1/images/generations"
    payload = {
        "model": OPENAI_IMAGE_MODEL,
        "prompt": prompt,
        "size": "1024x1536",
        "quality": OPENAI_IMAGE_QUALITY,
        "output_format": "jpeg",
        "n": 1,
    }
    request_body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    last_error: Exception | None = None

    for attempt in range(4):
        try:
            request = Request(
                endpoint,
                data=request_body,
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                    "User-Agent": "Premium-StickTalk/3.0",
                },
                method="POST",
            )
            with urlopen(request, timeout=420) as response:
                data = json.loads(response.read().decode("utf-8"))

            item = data.get("data", [{}])[0]
            image_b64 = item.get("b64_json")
            if not image_b64:
                raise RuntimeError(f"OpenAI không trả về dữ liệu ảnh: {str(data)[:500]}")

            image_bytes = base64.b64decode(image_b64)
            if len(image_bytes) < 8_000:
                raise RuntimeError(f"Ảnh trả về quá nhỏ: {len(image_bytes)} byte")
            target.write_bytes(image_bytes)
            return {
                "model": OPENAI_IMAGE_MODEL,
                "quality": OPENAI_IMAGE_QUALITY,
                "size": "1024x1536",
                "revised_prompt": item.get("revised_prompt", ""),
            }
        except HTTPError as error:
            body = error.read().decode("utf-8", errors="replace")[:800]
            last_error = RuntimeError(f"OpenAI HTTP {error.code}: {body}")
            print(f"OpenAI tạo ảnh lần {attempt + 1} chưa thành công: {last_error}")
            if error.code in {400, 401, 403}:
                break
            time.sleep(8 * (attempt + 1))
        except Exception as error:  # noqa: BLE001
            last_error = error
            print(f"OpenAI tạo ảnh lần {attempt + 1} chưa thành công: {error}")
            time.sleep(8 * (attempt + 1))

    raise RuntimeError(f"Không tạo được ảnh bằng OpenAI sau các lần thử: {last_error}")


def main() -> None:
    story_path = Path("assets/story.json")
    if not story_path.is_file():
        raise SystemExit("Không tìm thấy assets/story.json")

    story = json.loads(story_path.read_text(encoding="utf-8"))
    scenes = story.get("scenes") or story.get("canh") or []
    if not scenes:
        raise SystemExit("Kịch bản không có cảnh để tạo ảnh")

    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    template = os.getenv("VIDEO_TEMPLATE", story.get("template") or "prompt-to-video")
    title = clean(story.get("title") or "Video truyền cảm hứng")

    out_dir = Path("assets/generated-images")
    out_dir.mkdir(parents=True, exist_ok=True)
    manifest = []

    for index, scene in enumerate(scenes, start=1):
        prompt = build_prompt(scene, title, template, index, len(scenes))
        filename = f"scene-{index:02d}.jpg"
        target = out_dir / filename
        seed = int(hashlib.sha256(f"{title}|{index}|{template}".encode()).hexdigest()[:8], 16)
        print(f"Đang tạo ảnh OpenAI cho cảnh {index}/{len(scenes)}: {filename}")
        info = create_image(prompt, target, api_key)

        public_path = f"assets/generated-images/{filename}"
        scene["image"] = public_path
        scene["imagePrompt"] = prompt
        manifest.append(
            {
                "scene": index,
                "file": public_path,
                "prompt": prompt,
                "imageProvider": info["model"],
                "quality": info["quality"],
                "size": info["size"],
                "revisedPrompt": info.get("revised_prompt", ""),
                "seedReference": seed,
            }
        )

    story["scenes"] = scenes
    story["imagePromptProvider"] = "local-scene-prompt"
    story["imageProvider"] = OPENAI_IMAGE_MODEL
    story["aiImageCount"] = len(scenes)
    story["fallbackImageCount"] = 0
    story_path.write_text(json.dumps(story, ensure_ascii=False, indent=2), encoding="utf-8")

    Path("output").mkdir(exist_ok=True)
    Path("output/image-manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"Hoàn tất: OpenAI {OPENAI_IMAGE_MODEL} đã tạo {len(scenes)} ảnh AI.")


if __name__ == "__main__":
    main()
