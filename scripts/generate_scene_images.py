#!/usr/bin/env python3
"""Tạo ảnh minh họa riêng cho từng cảnh và ghi đường dẫn vào story.json.

Thứ tự ưu tiên:
1. Hugging Face Inference nếu có HF_TOKEN.
2. Pollinations cổng công khai, thử nhiều kích thước/cổng và nhiều lần.
3. Nếu toàn bộ dịch vụ ảnh đang lỗi, tạo minh họa SVG cục bộ để workflow vẫn render.

Không lưu khóa trong kho mã nguồn và không liên quan tới VieNeu-TTS.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import time
from html import escape
from pathlib import Path
from urllib.error import HTTPError
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


def _download(url: str, headers: dict[str, str], timeout: int = 240) -> tuple[bytes, str, str]:
    request = Request(url, headers=headers)
    with urlopen(request, timeout=timeout) as response:
        data = response.read()
        content_type = response.headers.get("Content-Type", "")
        final_url = response.geturl()
    if len(data) < 8_000 or "image" not in content_type.casefold():
        raise RuntimeError(f"Phản hồi không phải ảnh hợp lệ: {content_type}, {len(data)} byte")
    return data, content_type, final_url


def try_huggingface(prompt: str, target: Path, token: str) -> str | None:
    if not token:
        return None
    models = [
        "black-forest-labs/FLUX.1-schnell",
        "stabilityai/stable-diffusion-xl-base-1.0",
    ]
    payload = json.dumps({"inputs": prompt, "parameters": {"width": 768, "height": 1344}}).encode()
    for model in models:
        url = f"https://router.huggingface.co/hf-inference/models/{model}"
        for attempt in range(3):
            try:
                request = Request(
                    url,
                    data=payload,
                    headers={
                        "Authorization": f"Bearer {token}",
                        "Content-Type": "application/json",
                        "Accept": "image/*",
                        "User-Agent": "Premium-StickTalk/1.0",
                    },
                    method="POST",
                )
                with urlopen(request, timeout=300) as response:
                    data = response.read()
                    content_type = response.headers.get("Content-Type", "")
                if len(data) >= 8_000 and "image" in content_type.casefold():
                    target.write_bytes(data)
                    return url
                raise RuntimeError(f"HF trả về {content_type}, {len(data)} byte")
            except Exception as error:  # noqa: BLE001
                print(f"Hugging Face {model}, lần {attempt + 1} chưa thành công: {error}")
                time.sleep(8 * (attempt + 1))
    return None


def pollinations_urls(prompt: str, seed: int, api_key: str) -> list[str]:
    encoded = quote(prompt, safe="")
    # 768x1344 nhẹ hơn đáng kể so với 1080x1920, giúp giảm lỗi 500.
    queries = [
        f"width=768&height=1344&seed={seed}&model=flux&nologo=true&enhance=true",
        f"width=768&height=1344&seed={seed + 17}&model=flux&nologo=true",
        f"width=640&height=1136&seed={seed + 31}&model=flux&nologo=true",
    ]
    urls: list[str] = []
    if api_key:
        for query in queries:
            urls.append(
                f"https://gen.pollinations.ai/image/{encoded}?{query}&key={quote(api_key, safe='')}"
            )
    for query in queries:
        urls.extend(
            [
                f"https://image.pollinations.ai/prompt/{encoded}?{query}",
                f"https://pollinations.ai/p/{encoded}?{query}",
            ]
        )
    return urls


def try_pollinations(prompt: str, target: Path, seed: int, api_key: str) -> str | None:
    headers = {
        "User-Agent": "Mozilla/5.0 Premium-StickTalk/1.0",
        "Accept": "image/avif,image/webp,image/apng,image/jpeg,image/png,*/*",
        "Referer": "https://pollinations.ai/",
        "Cache-Control": "no-cache",
    }
    for url in pollinations_urls(prompt, seed, api_key):
        for attempt in range(3):
            try:
                data, _, final_url = _download(url, headers)
                target.write_bytes(data)
                return final_url
            except HTTPError as error:
                print(f"Cổng ảnh trả HTTP {error.code}, lần {attempt + 1}: {url.split('?')[0]}")
                if error.code in {401, 403, 404}:
                    break
                time.sleep(7 * (attempt + 1))
            except Exception as error:  # noqa: BLE001
                print(f"Cổng ảnh chưa thành công, lần {attempt + 1}: {error}")
                time.sleep(7 * (attempt + 1))
    return None


def create_local_svg(target: Path, scene: dict, title: str, template: str, seed: int) -> None:
    """Phương án an toàn cuối cùng để video vẫn chạy khi dịch vụ AI bên ngoài ngừng hoạt động."""
    narration = clean(scene.get("narration") or scene.get("loi_dan") or title)
    digest = hashlib.sha256(f"{title}|{narration}|{seed}".encode()).hexdigest()
    hue1 = int(digest[:2], 16) * 360 // 255
    hue2 = (hue1 + 55 + int(digest[2:4], 16) % 90) % 360
    paper = template in {"paper-sketch", "paper-cut"}
    bg1 = "#f4eddf" if paper else f"hsl({hue1} 55% 18%)"
    bg2 = "#d9cbb4" if paper else f"hsl({hue2} 65% 28%)"
    stroke = "#50483d" if paper else "#ffffff"
    fill = "#cab99c" if paper else "#ffffff33"
    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="768" height="1344" viewBox="0 0 768 1344">
<defs><linearGradient id="g" x1="0" y1="0" x2="1" y2="1"><stop stop-color="{bg1}"/><stop offset="1" stop-color="{bg2}"/></linearGradient><filter id="s"><feDropShadow dx="0" dy="18" stdDeviation="22" flood-opacity=".35"/></filter></defs>
<rect width="768" height="1344" fill="url(#g)"/>
<circle cx="590" cy="230" r="115" fill="{fill}" opacity=".55"/>
<path d="M0 980 C150 760 250 930 390 720 S610 560 768 760 V1344 H0Z" fill="{fill}" opacity=".62"/>
<path d="M80 1010 C210 835 310 930 430 775 S625 665 710 805" fill="none" stroke="{stroke}" stroke-width="11" opacity=".8"/>
<g transform="translate(380 650)" stroke="{stroke}" stroke-width="12" stroke-linecap="round" fill="none" filter="url(#s)"><circle cy="-145" r="58" fill="{fill}"/><path d="M0 -85 V155 M0 -10 L-105 85 M0 -10 L105 55 M0 155 L-80 300 M0 155 L95 290"/></g>
<g opacity=".38" stroke="{stroke}" stroke-width="5"><path d="M75 220h250M90 270h180M485 1040h210M520 1090h145"/></g>
<!-- Minh họa dự phòng cục bộ, không chèn chữ để tránh lỗi chữ trong ảnh -->
</svg>'''
    target.with_suffix(".svg").write_text(svg, encoding="utf-8")


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
    pollinations_key = os.getenv("POLLINATIONS_API_KEY", "").strip()
    hf_token = os.getenv("HF_TOKEN", "").strip()
    out_dir = Path("assets/generated-images")
    out_dir.mkdir(parents=True, exist_ok=True)

    manifest = []
    ai_count = 0
    fallback_count = 0
    for index, scene in enumerate(scenes, start=1):
        prompt = prompt_for(scene, title, template)
        filename = f"scene-{index:02d}.jpg"
        target = out_dir / filename
        seed = int(hashlib.sha256(f"{title}|{index}|{template}".encode()).hexdigest()[:8], 16)
        print(f"Đang tạo ảnh cho cảnh {index}/{len(scenes)}: {filename}")

        provider_url = try_huggingface(prompt, target, hf_token)
        provider = "huggingface"
        if not provider_url:
            provider_url = try_pollinations(prompt, target, seed, pollinations_key)
            provider = "pollinations"

        if provider_url:
            public_path = f"assets/generated-images/{filename}"
            ai_count += 1
        else:
            svg_target = target.with_suffix(".svg")
            create_local_svg(target, scene, title, template, seed)
            public_path = f"assets/generated-images/{svg_target.name}"
            provider = "minh-hoa-du-phong-cuc-bo"
            provider_url = "local"
            fallback_count += 1
            print(f"Cảnh {index}: dịch vụ ảnh đang lỗi, dùng minh họa dự phòng để video vẫn chạy.")

        scene["image"] = public_path
        scene["imagePrompt"] = prompt
        manifest.append(
            {
                "scene": index,
                "file": public_path,
                "prompt": prompt,
                "provider": provider,
                "source": provider_url,
            }
        )

    story["scenes"] = scenes
    story["imageProvider"] = "multi-provider"
    story["aiImageCount"] = ai_count
    story["fallbackImageCount"] = fallback_count
    story_path.write_text(json.dumps(story, ensure_ascii=False, indent=2), encoding="utf-8")
    Path("output").mkdir(exist_ok=True)
    Path("output/image-manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"Hoàn tất ảnh: {ai_count} ảnh AI, {fallback_count} ảnh dự phòng. Workflow tiếp tục render.")


if __name__ == "__main__":
    main()
