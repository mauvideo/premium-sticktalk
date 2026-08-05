#!/usr/bin/env python3
"""Dùng Gemini tạo prompt và sinh ảnh AI riêng cho từng cảnh.

Chỉ cần GitHub Secret GEMINI_API_KEY. Không dùng Hugging Face hoặc Pollinations.
Tệp này không sửa và không phụ thuộc vào VieNeu-TTS.
"""
from __future__ import annotations

import base64
import json
import os
import re
import time
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

PROMPT_MODEL = os.getenv("GEMINI_PROMPT_MODEL", "gemini-2.5-flash")
IMAGE_MODEL = os.getenv("GEMINI_IMAGE_MODEL", "gemini-2.5-flash-image")

STYLES = {
    "prompt-to-video": "cinematic photorealism, dramatic natural light, emotional visual storytelling",
    "kinetic-captions": "modern editorial visual, bold contrast, clean negative space for captions",
    "smooth-transitions": "dreamy cinematic realism, layered depth, soft natural light",
    "paper-sketch": "hand-drawn graphite pencil sketch on warm ivory textured paper, vintage book illustration",
    "business-motivation": "premium business documentary photography, professional atmosphere, charcoal and warm gold lighting",
    "paper-cut": "layered handmade paper-cut illustration, tactile paper edges, soft paper shadows",
}


def clean(value: object) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def post_json(url: str, payload: dict, api_key: str, timeout: int = 300) -> dict:
    request = Request(
        url,
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={
            "x-goog-api-key": api_key,
            "Content-Type": "application/json",
            "User-Agent": "Premium-StickTalk/3.0",
        },
        method="POST",
    )
    with urlopen(request, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def gemini_prompts(story: dict, scenes: list[dict], template: str, api_key: str) -> list[str]:
    title = clean(story.get("title") or "Video truyền cảm hứng")
    style = STYLES.get(template, STYLES["prompt-to-video"])
    scene_data = [
        {
            "scene": index,
            "headline": clean(scene.get("headline") or title),
            "narration": clean(scene.get("narration") or scene.get("loi_dan") or title),
        }
        for index, scene in enumerate(scenes, start=1)
    ]

    instruction = f"""
Create exactly {len(scene_data)} distinct English image prompts for a vertical motivational video.
Overall topic: {title}
Required visual style: {style}
Aspect ratio: 9:16 vertical.

Each prompt must clearly describe subject, environment, action, camera angle, lighting and emotion.
Every scene must visually match its narration and use a different composition.
Keep a consistent overall art direction across all scenes.
No text, letters, logos, watermark, app interface, border or video player controls.
Do not mention celebrities or trademarks.

Scenes:
{json.dumps(scene_data, ensure_ascii=False)}

Return JSON only in this exact shape:
{{"prompts":[{{"scene":1,"prompt":"..."}}]}}
""".strip()

    endpoint = f"https://generativelanguage.googleapis.com/v1beta/models/{PROMPT_MODEL}:generateContent"
    payload = {
        "contents": [{"parts": [{"text": instruction}]}],
        "generationConfig": {
            "temperature": 0.75,
            "response_mime_type": "application/json",
        },
    }

    last_error: Exception | None = None
    for attempt in range(3):
        try:
            data = post_json(endpoint, payload, api_key, timeout=180)
            text = data["candidates"][0]["content"]["parts"][0]["text"]
            parsed = json.loads(text)
            by_scene = {
                int(item["scene"]): clean(item["prompt"])
                for item in parsed.get("prompts", [])
                if item.get("scene") and clean(item.get("prompt"))
            }
            prompts = [by_scene.get(i, "") for i in range(1, len(scenes) + 1)]
            if all(prompts):
                return prompts
            raise RuntimeError(f"Gemini trả thiếu prompt: {len(by_scene)}/{len(scenes)} cảnh")
        except Exception as error:  # noqa: BLE001
            last_error = error
            print(f"Gemini tạo prompt chưa thành công, lần {attempt + 1}: {error}")
            time.sleep(5 * (attempt + 1))
    raise RuntimeError(f"Gemini không tạo được prompt ảnh: {last_error}")


def extract_image(data: dict) -> tuple[bytes, str]:
    candidates = data.get("candidates") or []
    for candidate in candidates:
        for part in (candidate.get("content") or {}).get("parts") or []:
            inline = part.get("inlineData") or part.get("inline_data")
            if inline and inline.get("data"):
                mime_type = inline.get("mimeType") or inline.get("mime_type") or "image/png"
                return base64.b64decode(inline["data"]), mime_type
    feedback = data.get("promptFeedback") or data.get("prompt_feedback") or {}
    raise RuntimeError(f"Gemini không trả về ảnh. Phản hồi an toàn: {feedback}")


def create_image(prompt: str, target_base: Path, api_key: str) -> tuple[Path, str]:
    endpoint = f"https://generativelanguage.googleapis.com/v1/models/{IMAGE_MODEL}:generateContent"
    full_prompt = (
        f"Generate one high-quality vertical 9:16 image for a short video. {prompt} "
        "Fill the entire vertical frame. No text, no letters, no logo, no watermark, no border."
    )
    payload = {
        "contents": [{"parts": [{"text": full_prompt}]}],
        "generationConfig": {"responseModalities": ["IMAGE"]},
    }

    last_error: Exception | None = None
    for attempt in range(4):
        try:
            data = post_json(endpoint, payload, api_key, timeout=360)
            image_bytes, mime_type = extract_image(data)
            if len(image_bytes) < 8_000:
                raise RuntimeError(f"Ảnh Gemini quá nhỏ: {len(image_bytes)} byte")
            suffix = ".jpg" if "jpeg" in mime_type.casefold() else ".png"
            target = target_base.with_suffix(suffix)
            target.write_bytes(image_bytes)
            return target, mime_type
        except HTTPError as error:
            body = error.read().decode("utf-8", errors="replace")[:500]
            last_error = RuntimeError(f"HTTP {error.code}: {body}")
            print(f"Gemini sinh ảnh, lần {attempt + 1}: {last_error}")
            if error.code in {400, 401, 403}:
                break
        except Exception as error:  # noqa: BLE001
            last_error = error
            print(f"Gemini sinh ảnh, lần {attempt + 1}: {error}")
        time.sleep(8 * (attempt + 1))
    raise RuntimeError(f"Gemini không sinh được ảnh sau các lần thử: {last_error}")


def main() -> None:
    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    if not api_key:
        raise SystemExit(
            "Thiếu GEMINI_API_KEY. Hãy thêm Secret GEMINI_API_KEY trong Settings → Secrets and variables → Actions."
        )

    story_path = Path("assets/story.json")
    if not story_path.is_file():
        raise SystemExit("Không tìm thấy assets/story.json")

    story = json.loads(story_path.read_text(encoding="utf-8"))
    scenes = story.get("scenes") or story.get("canh") or []
    if not scenes:
        raise SystemExit("Kịch bản không có cảnh để tạo ảnh")

    template = os.getenv("VIDEO_TEMPLATE", story.get("template") or "prompt-to-video")
    print(f"Gemini đang tạo prompt cho {len(scenes)} cảnh...")
    prompts = gemini_prompts(story, scenes, template, api_key)

    out_dir = Path("assets/generated-images")
    out_dir.mkdir(parents=True, exist_ok=True)
    manifest = []

    for index, (scene, prompt) in enumerate(zip(scenes, prompts, strict=True), start=1):
        print(f"Gemini đang sinh ảnh cảnh {index}/{len(scenes)}...")
        target, mime_type = create_image(prompt, out_dir / f"scene-{index:02d}", api_key)
        public_path = f"assets/generated-images/{target.name}"
        scene["image"] = public_path
        scene["imagePrompt"] = prompt
        manifest.append(
            {
                "scene": index,
                "file": public_path,
                "prompt": prompt,
                "promptProvider": PROMPT_MODEL,
                "imageProvider": IMAGE_MODEL,
                "mimeType": mime_type,
            }
        )

    story["scenes"] = scenes
    story["imagePromptProvider"] = PROMPT_MODEL
    story["imageProvider"] = IMAGE_MODEL
    story["aiImageCount"] = len(scenes)
    story["fallbackImageCount"] = 0
    story_path.write_text(json.dumps(story, ensure_ascii=False, indent=2), encoding="utf-8")

    Path("output").mkdir(exist_ok=True)
    Path("output/image-manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"Hoàn tất: Gemini đã tạo {len(scenes)} ảnh AI cho video.")


if __name__ == "__main__":
    main()
