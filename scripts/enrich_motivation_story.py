#!/usr/bin/env python3
from __future__ import annotations
import argparse, hashlib, json, re
from pathlib import Path

def clean_title(value: str) -> str:
    value = re.sub(r"^(làm video|video|chủ đề)\s*[:\-]?\s*", "", value.strip(), flags=re.I)
    return value.rstrip(".!? ")

def build_sentences(topic: str, template: str) -> list[str]:
    short = clean_title(topic)
    seed = int(hashlib.sha256(f"{short}|{template}".encode()).hexdigest()[:8], 16)
    openings = [
        f"{short} không bắt đầu bằng một khoảnh khắc phi thường.",
        f"Khi nghĩ về {short.lower()}, nhiều người chỉ nhìn vào kết quả.",
        f"Điều khó nhất của {short.lower()} không nằm ở bước cuối cùng.",
    ]
    body = [
        "Nó bắt đầu từ lúc bạn vẫn tiếp tục, dù chưa ai nhìn thấy nỗ lực của bạn.",
        "Mỗi bước nhỏ hôm nay đang âm thầm tạo nên con người bạn của ngày mai.",
        "Bạn không cần tiến nhanh hơn tất cả mọi người; bạn chỉ cần đừng quay lại phiên bản từng bỏ cuộc.",
        "Sự tự tin không đến trước hành động. Nó xuất hiện sau khi bạn giữ lời hứa với chính mình đủ nhiều lần.",
        "Có thể hôm nay kết quả chưa xuất hiện, nhưng kỷ luật vẫn đang tích lũy giá trị ở nơi mắt thường chưa nhìn thấy.",
        "Đừng dùng một ngày khó khăn để kết luận về cả hành trình.",
        "Hãy làm việc cần làm, ngay cả khi cảm xúc chưa sẵn sàng.",
        "Một quyết định đúng được lặp lại mỗi ngày sẽ mạnh hơn một lần bùng nổ rồi biến mất.",
        "So sánh khiến bạn quên mất quãng đường mình đã vượt qua; tập trung giúp bạn nhìn thấy bước tiếp theo.",
        "Bạn có quyền nghỉ để lấy lại sức, nhưng đừng từ bỏ điều từng khiến mình bắt đầu.",
    ]
    endings = [
        f"Hôm nay, hãy chọn một hành động nhỏ đưa bạn gần hơn tới {short.lower()}.",
        "Không cần hoàn hảo. Chỉ cần bắt đầu, rồi kiên trì thêm một ngày nữa.",
        "Chính những ngày không muốn làm nhưng vẫn làm sẽ thay đổi cuộc đời bạn.",
    ]
    body = body[seed % len(body):] + body[:seed % len(body)]
    return [openings[seed % len(openings)], *body, endings[(seed // 7) % len(endings)]]

def enrich(path: Path, topic: str, template: str, duration: int) -> None:
    data = json.loads(path.read_text(encoding="utf-8"))
    scenes = data.get("scenes") or []
    if not scenes:
        raise RuntimeError("story.json không có cảnh")
    target_words = {30: 72, 45: 108, 60: 145}.get(duration, 108)
    pool, selected, count = build_sentences(topic, template), [], 0
    for sentence in pool:
        selected.append(sentence); count += len(sentence.split())
        if count >= target_words: break
    chunks = [[] for _ in scenes]
    for i, sentence in enumerate(selected):
        chunks[min(len(chunks)-1, i * len(chunks) // max(1, len(selected)))].append(sentence)
    for i, scene in enumerate(scenes):
        narration = " ".join(chunks[i]).strip() or selected[min(i, len(selected)-1)]
        scene["narration"] = narration
        scene["loi_dan"] = narration
        scene["headline"] = clean_title(topic) if i == 0 else narration.split(".")[0]
        scene["visualTemplate"] = template
        scene["characters"] = []
        scene["nhan_vat"] = []
    data.update({"title": clean_title(topic), "project": "motivation", "template": template, "contentEngine": "motivation-auto-v1"})
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--story", default="assets/story.json")
    p.add_argument("--topic", required=True)
    p.add_argument("--template", required=True)
    p.add_argument("--duration", type=int, required=True)
    a = p.parse_args(); enrich(Path(a.story), a.topic, a.template, a.duration)

if __name__ == "__main__": main()
