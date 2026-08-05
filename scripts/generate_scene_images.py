#!/usr/bin/env python3
"""Tạo prompt ảnh bằng Gemini và sinh ảnh từng cảnh bằng FLUX trên Hugging Face.

Luồng xử lý:
1. Đọc toàn bộ cảnh trong assets/story.json.
2. Gửi một yêu cầu duy nhất tới Gemini để tạo prompt ảnh cho từng cảnh.
3. Dùng FLUX.1-schnell tạo ảnh dọc cho từng prompt.
4. Ghi đường dẫn ảnh và prompt vào story.json + output/image-manifest.json.

Tệp này không sửa và không phụ thuộc vào VieNeu-TTS.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import time
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
HF_MODELS = (
    "black-forest-labs/FLUX.1-schnell",
    "stabilityai/stable-diffusion-xl-base-1.0",
)

STYLES = {
    "prompt-to-video": "điện ảnh chân thực, ánh sáng tự nhiên kịch tính, giàu cảm xúc",
    "kinetic-captions": "biên tập hiện đại, tương phản mạnh, khoảng trống sạch để đặt phụ đề",
    "smooth-transitions": "điện ảnh nhẹ nhàng, nhiều lớp chiều sâu, ánh sáng mềm",
    "paper-sketch": "phác thảo chì vẽ tay trên giấy ngà có vân, minh họa sách cổ",
    "business-motivation": "phim tài liệu doanh nhân cao cấp, chuyên nghiệp, tông than và vàng ấm",
    "paper-cut": "minh họa cắt giấy nhiều lớp, mép giấy thủ công, bóng giấy mềm",
}


def clean(value: str) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def request_json(url: str, payload: dict, headers: dict[str, str], timeout: int = 180) -> dict:
    request = Request(
        url,
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers=headers,
        method="POST",
    )
    with urlopen(request, timeout=timeout) as response:
        raw = response.read().decode("utf-8")
    return json.loads(raw)


def gemini_prompts(story: dict, scenes: list[dict], template: str, api_key: str) -> list[str]:
    if not api_key:
        raise RuntimeError(
            "Thiếu GEMINI_API_KEY. Hãy thêm Secret GEMINI_API_KEY trong Settings → Secrets and variables → Actions."
        )

    title = clean(story.get("title") or "Video truyền cảm hứng")
    style = STYLES.get(template, STYLES["prompt-to-video"])
    scene_data = []
    for index, scene in enumerate(scenes, start=1):
        scene_data.append(
            {
                "scene": index,
                "headline": clean(scene.get("headline") or title),
                "narration": clean(scene.get("narration") or scene.get("loi_dan") or title),
            }
        )

    instruction = f"""
Bạn là đạo diễn hình ảnh cho video dọc truyền cảm hứng.
Hãy tạo đúng {len(scene_data)} prompt ảnh, mỗi cảnh một prompt khác nhau và bám sát lời dẫn.

Chủ đề chung: {title}
Phong cách hình ảnh bắt buộc: {style}
Tỷ lệ: dọc 9:16.

Yêu cầu cho từng prompt:
- Viết bằng tiếng Anh để mô hình tạo ảnh hiểu tốt.
- Mô tả rõ chủ thể, bối cảnh, hành động, ánh sáng, góc máy và cảm xúc.
- Hình ảnh phải có câu chuyện và phù hợp cảnh tương ứng.
- Không tạo chữ, ký tự, logo, watermark, giao diện ứng dụng hoặc khung video.
- Không lặp lại cùng một bố cục giữa các cảnh.
- Không nhắc tới tên thương hiệu hay người nổi tiếng.

Dữ liệu cảnh:
{json.dumps(scene_data, ensure_ascii=False)}

Chỉ trả về JSON theo cấu trúc:
{{"prompts":[{{"scene":1,"prompt":"..."}}]}}
""".strip()

    endpoint = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent"
    payload = {
        "contents": [{"parts": [{"text": instruction}]}],
        "generationConfig": {
            "temperature": 0.8,
            "response_mime_type": "application/json",
        },
    }
    headers = {
        "x-goog-api-key": api_key,
        "Content-Type": "application/json",
        "User-Agent": "Premium-StickTalk/2.0",
    }

    last_error: Exception | None = None
    for attempt in range(3):
        try:
            data = request_json(endpoint, payload, headers)
            text = data["candidates"][0]["content"]["parts"][0]["text"]
            parsed = json.loads(text)
            items = parsed.get("prompts", [])
            by_scene = {
                int(item["scene"]): clean(item["prompt"])
                for item in items
                if item.get("scene") and clean(item.get("prompt"))
            }
            prompts = [by_scene.get(i, "") for i in range(1, len(scenes) + 1)]
            if all(prompts):
                return prompts
            raise RuntimeError(f"Gemini trả thiếu prompt: nhận {len(by_scene)}/{len(scenes)} cảnh")
        except Exception as error:  # noqa: BLE001
            last_error = error
            print(f"Gemini tạo prompt chưa thành công, lần {attempt + 1}: {error}")
            time.sleep(5 * (attempt + 1))

    raise RuntimeError(f"Gemini không tạo được prompt ảnh sau 3 lần: {last_error}")


def create_image(prompt: str, target: Path, token: str, seed: int) -> tuple[str, str]:
    if not token:
        raise RuntimeError(
            "Thiếu HF_TOKEN. Hãy thêm Secret HF_TOKEN để FLUX có thể tự sinh ảnh AI."
        )

    payload = json.dumps(
        {
            "inputs": prompt,
            "parameters": {
                "width": 768,
                "height": 1344,
                "seed": seed,
                "num_inference_steps": 4,
            },
        }
    ).encode("utf-8")

    last_error: Exception | None = None
    for model in HF_MODELS:
        endpoint = f"https://router.huggingface.co/hf-inference/models/{model}"
        for attempt in range(4):
            try:
                request = Request(
                    endpoint,
                    data=payload,
                    headers={
                        "Authorization": f"Bearer {token}",
                        "Content-Type": "application/json",
                        "Accept": "image/*",
                        "User-Agent": "Premium-StickTalk/2.0",
                    },
                    method="POST",
                )
                with urlopen(request, timeout=360) as response:
                    data = response.read()
                    content_type = response.headers.get("Content-Type", "")

                if len(data) < 8_000 or "image" not in content_type.casefold():
                    body = data[:300].decode("utf-8", errors="replace")
                    raise RuntimeError(
                        f"Phản hồi không phải ảnh: {content_type}, {len(data)} byte, {body}"
                    )

                target.write_bytes(data)
                return model, endpoint
            except HTTPError as error:
                body = error.read().decode("utf-8", errors="replace")[:400]
                last_error = RuntimeError(f"HTTP {error.code}: {body}")
                print(f"{model}, lần {attempt + 1}: {last_error}")
                if error.code in {401, 403}:
                    break
                time.sleep(8 * (attempt + 1))
            except Exception as error:  # noqa: BLE001
                last_error = error
                print(f"{model}, lần {attempt + 1}: {error}")
                time.sleep(8 * (attempt + 1))

    raise RuntimeError(f"Không tạo được ảnh AI sau khi thử các mô hình FLUX/SDXL: {last_error}")


def main() -> None:
    story_path = Path("assets/story.json")
    if not story_path.is_file():
        raise SystemExit("Không tìm thấy assets/story.json")

    story = json.loads(story_path.read_text(encoding="utf-8"))
    scenes = story.get("scenes") or story.get("canh") or []
    if not scenes:
        raise SystemExit("Kịch bản không có cảnh để tạo ảnh")

    template = os.getenv("VIDEO_TEMPLATE", story.get("template") or "prompt-to-video")
    gemini_key = os.getenv("GEMINI_API_KEY", "").strip()
    hf_token = os.getenv("HF_TOKEN", "").strip()
    title = clean(story.get("title") or "Video truyền cảm hứng")

    print(f"Đang yêu cầu Gemini tạo {len(scenes)} prompt ảnh theo mẫu {template}...")
    prompts = gemini_prompts(story, scenes, template, gemini_key)

    out_dir = Path("assets/generated-images")
    out_dir.mkdir(parents=True, exist_ok=True)
    manifest = []

    for index, (scene, prompt) in enumerate(zip(scenes, prompts, strict=True), start=1):
        filename = f"scene-{index:02d}.jpg"
        target = out_dir / filename
        seed = int(hashlib.sha256(f"{title}|{index}|{template}".encode()).hexdigest()[:8], 16)
        print(f"Đang sinh ảnh AI cảnh {index}/{len(scenes)}: {filename}")
        model, endpoint = create_image(prompt, target, hf_token, seed)

        public_path = f"assets/generated-images/{filename}"
        scene["image"] = public_path
        scene["imagePrompt"] = prompt
        manifest.append(
            {
                "scene": index,
                "file": public_path,
                "prompt": prompt,
                "promptProvider": GEMINI_MODEL,
                "imageProvider": model,
                "source": endpoint,
                "seed": seed,
            }
        )

    story["scenes"] = scenes
    story["imagePromptProvider"] = GEMINI_MODEL
    story["imageProvider"] = "huggingface-flux"
    story["aiImageCount"] = len(scenes)
    story["fallbackImageCount"] = 0
    story_path.write_text(json.dumps(story, ensure_ascii=False, indent=2), encoding="utf-8")

    Path("output").mkdir(exist_ok=True)
    Path("output/image-manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"Hoàn tất: Gemini tạo {len(prompts)} prompt, FLUX tạo {len(scenes)} ảnh AI.")


if __name__ == "__main__":
    main()
