#!/usr/bin/env python3
"""Điều phối nhà cung cấp TTS; tuyệt đối không chuyển dự phòng ngầm."""

import argparse
import asyncio
import json
import os
import re
from pathlib import Path
from mutagen.mp3 import MP3

from scripts.tts.edge_tts_provider import EdgeTtsProvider
from scripts.tts.google_tts import GoogleTtsProvider
from scripts.tts.presets import DEFAULT_PRESET, PRESETS, resolve_preset

ONES = ["không", "một", "hai", "ba", "bốn", "năm", "sáu", "bảy", "tám", "chín"]

def number_to_vietnamese(n: int) -> str:
    if n == 0: return ONES[0]
    if n < 0: return "âm " + number_to_vietnamese(-n)
    scales, groups = ["", "nghìn", "triệu", "tỷ", "nghìn tỷ", "triệu tỷ"], []
    while n: groups.append(n % 1000); n //= 1000
    def under(x, full=False):
        h, r = divmod(x,100); t,u=divmod(r,10); w=[]
        if h: w += [ONES[h],"trăm"]
        elif full and r: w += ["không","trăm"]
        if t>1: w += [ONES[t],"mươi"]
        elif t==1: w += ["mười"]
        elif u and (h or full): w += ["lẻ"]
        if u: w += ["mốt" if u==1 and t>1 else "lăm" if u==5 and t else "tư" if u==4 and t>1 else ONES[u]]
        return " ".join(w)
    parts=[]
    for i in range(len(groups)-1,-1,-1):
        g=groups[i]
        if g: parts.append(f"{under(g, bool(parts) and g<100)} {scales[i]}".strip())
    return " ".join(parts)

def clean_text(text: str) -> str:
    text=re.sub(r"\s+"," ",text).strip(); text=re.sub(r"(?<=\d)\s*%"," phần trăm",text)
    return re.sub(r"\s+([.!?,:;])",r"\1",text)

def split_long_sentences(text: str, max_words: int=24) -> str:
    out=[]
    for sentence in re.split(r"(?<=[.!?])\s+",text):
        words=sentence.split()
        while len(words)>max_words: out.append(" ".join(words[:max_words]).rstrip(".,:;")+"."); words=words[max_words:]
        if words: out.append(" ".join(words))
    return " ".join(out)

PAUSES_MS={".":560,",":210,":":300,";":330,"?":620,"!":600}
def speech_parts(text: str):
    parts=[]; start=0
    for m in re.finditer(r"[.!?,:;]",text):
        if text[start:m.start()].strip(): parts.append((text[start:m.start()].strip(),PAUSES_MS[m.group()]))
        start=m.end()
    if text[start:].strip(): parts.append((text[start:].strip(),0))
    return parts

async def synthesize(text: str, destination: Path, preset_name: str, provider_name: str|None=None) -> str:
    preset=resolve_preset(preset_name); selected=(provider_name or os.getenv("TTS_PROVIDER") or "google").lower()
    if selected not in {"google","edge"}: raise ValueError(f"Nhà cung cấp không hợp lệ: {selected}")
    if preset.provider != selected: raise RuntimeError(f"Giọng '{preset.name}' thuộc nhà cung cấp {preset.provider}, không phải {selected}. Không chuyển giọng tự động.")
    print("========================================\n"+f"NHÀ CUNG CẤP GIỌNG ĐỌC: {'GOOGLE CLOUD TTS' if selected=='google' else 'MICROSOFT EDGE TTS'}\nTÊN HIỂN THỊ: {preset.name}\nMÃ PRESET: {preset.code}\nVOICE ID THỰC TẾ: {preset.voice}\nLANGUAGE CODE: vi-VN\nTỐC ĐỘ: {preset.speed}\nCAO ĐỘ: {preset.pitch}\nĐỊNH DẠNG: MP3\n========================================")
    provider=GoogleTtsProvider() if selected=="google" else EdgeTtsProvider()
    actual=await provider.synthesize(split_long_sentences(clean_text(text),preset.max_words),destination,preset)
    if actual != preset.voice: raise RuntimeError("Voice ID thực tế không khớp yêu cầu; đã dừng.")
    if not destination.is_file() or destination.stat().st_size<=0: raise RuntimeError("File giọng đọc không tồn tại hoặc rỗng.")
    duration=MP3(destination).info.length
    info={"nha_cung_cap":selected,"ten_hien_thi":preset.name,"ma_preset":preset.code,"voice_id":actual,"language_code":"vi-VN","toc_do":preset.speed,"cao_do":preset.pitch,"dinh_dang":"MP3","thoi_luong_giay":round(duration,3),"dung_luong_byte":destination.stat().st_size}
    Path("output").mkdir(exist_ok=True); Path("output/tts-info.json").write_text(json.dumps(info,ensure_ascii=False,indent=2),encoding="utf-8")
    print(f"Đã tạo giọng đọc: {duration:.2f} giây, {destination.stat().st_size} byte")
    return actual

async def run(preset_name,provider):
    story=json.loads(Path("assets/story.json").read_text(encoding="utf-8")); text=" ".join(s["narration"] for s in story["scenes"])
    await synthesize(text,Path("assets/narration.mp3"),preset_name,provider)

def main():
    p=argparse.ArgumentParser(description="Tạo giọng đọc tiếng Việt"); p.add_argument("--preset",default=os.getenv("GOOGLE_TTS_VOICE",DEFAULT_PRESET)); p.add_argument("--provider",choices=["google","edge"],default=os.getenv("TTS_PROVIDER","google")); a=p.parse_args()
    try: asyncio.run(run(a.preset,a.provider))
    except (ValueError,RuntimeError) as e: p.error(str(e))
if __name__=="__main__": main()

# Tên tương thích cho kiểm thử/tích hợp cũ.
from scripts.tts.presets import NAM_MINH, HOAI_MY
from scripts.tts.audio_postprocess import EDGE_FILTERS as MASTERING_FILTERS, postprocess as _postprocess
def _master_audio(source,destination,preset): _postprocess(source,destination,preset)
