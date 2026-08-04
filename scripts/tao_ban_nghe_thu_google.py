#!/usr/bin/env python3
"""Tạo bộ MP3 để người dùng tự nghe, không gắn nhãn vùng miền đã xác nhận."""
import asyncio,json
from pathlib import Path
from scripts.generate_tts import synthesize

TEXT="""Xin chào. Đây là bản thử giọng tiếng Việt.
Hà Nội hôm nay có tiết trời dịu mát.
Người làm việc lớn cần bình tĩnh, rõ ràng và quyết đoán.
Mười hai triệu năm trăm nghìn đồng.
Tốc độ tăng trưởng đạt mười tám phần trăm."""
VOICES=["google_nam_neural2","google_nam_wavenet","google_nam_chirp_tram","google_nam_chirp_noi_luc"]
async def main():
    folder=Path("output/ban-nghe-thu-google");folder.mkdir(parents=True,exist_ok=True);info=[]
    for code in VOICES:
        target=folder/f"{code}.mp3";voice=await synthesize(TEXT,target,code,"google");info.append({"ma_preset":code,"voice_id":voice,"tep":target.name})
    (folder/"thong_tin_giong.json").write_text(json.dumps({"luu_y":"Hãy tự nghe và chọn; dự án không khẳng định vùng miền khi chưa kiểm thử.","cac_giong":info},ensure_ascii=False,indent=2),encoding="utf-8")
if __name__=="__main__":asyncio.run(main())
