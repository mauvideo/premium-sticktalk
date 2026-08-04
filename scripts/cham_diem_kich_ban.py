#!/usr/bin/env python3
"""Chấm chất lượng kịch bản V3.6 theo thang 100 điểm."""
from __future__ import annotations
import argparse, json, re
from pathlib import Path
try:
    from .script_writer import kiem_tra_do_dai_cau, kiem_tra_lap_cau, kiem_tra_van_mau
except ImportError:
    from script_writer import kiem_tra_do_dai_cau, kiem_tra_lap_cau, kiem_tra_van_mau

def _scenes(story): return story.get("canh") or story.get("scenes") or []
def cham_diem(story: dict) -> dict:
    scenes=_scenes(story); texts=[s.get("loi_dan",s.get("narration","")) for s in scenes]; full=" ".join(texts)
    hook=story.get("hook") or (texts[0] if texts else ""); hook_words=len(hook.split())
    diem_hook=20 if 6 <= hook_words <= 18 and hook.rstrip().endswith((".","?","!”","!","?”","\"")) else 14 if hook else 0
    concrete=sum(bool(re.search(r"\b(một|hai|ba|bốn|năm|\d+|hãy tưởng tượng|ví dụ|khi)\b",x,re.I)) for x in texts)
    diem_cu_the=min(15,8+concrete) if texts else 0
    long=len(kiem_tra_do_dai_cau(full)); diem_tu_nhien=max(0,15-long*3-len(kiem_tra_lap_cau(full))*2)
    roles=[s.get("vai_tro","").casefold() for s in scenes]
    diem_cau_truc=15 if len(scenes)>=5 and story.get("cao_trao") and story.get("ket_luan") else 10
    climax=story.get("cao_trao",""); diem_cao_trao=10 if climax and climax in texts[-2:] else 6 if climax else 0
    starts=[re.findall(r"\w+",x.casefold())[:2] for x in texts]; diem_da_dang=max(0,10-(len(starts)-len({tuple(x) for x in starts}))*2)
    diem_ket=5 if story.get("ket_luan") or story.get("cta") else 0
    diem_van_mau=max(0,10-len(kiem_tra_van_mau(full))*3)
    total=sum((diem_hook,diem_cu_the,diem_tu_nhien,diem_cau_truc,diem_cao_trao,diem_da_dang,diem_ket,diem_van_mau))
    warnings=[]
    if total<75: warnings.append("Kịch bản dưới ngưỡng 75 điểm; cần viết lại.")
    if long: warnings.append(f"Có {long} câu dài quá 22 từ.")
    if kiem_tra_van_mau(full): warnings.append("Kịch bản còn cụm văn mẫu.")
    return {"tong_diem":total,"diem_hook":diem_hook,"diem_cu_the":diem_cu_the,"diem_tu_nhien":diem_tu_nhien,"diem_cau_truc":diem_cau_truc,"diem_cao_trao":diem_cao_trao,"diem_da_dang_cau":diem_da_dang,"diem_ket_thuc":diem_ket,"diem_khong_van_mau":diem_van_mau,"canh_bao":warnings}

def main():
    p=argparse.ArgumentParser(description="Chấm điểm chất lượng kịch bản tiếng Việt"); p.add_argument("tep",nargs="+"); a=p.parse_args(); failed=False
    for name in a.tep:
        try: story=json.loads(Path(name).read_text(encoding="utf-8"))
        except (OSError,json.JSONDecodeError) as exc: p.error(f"Không thể đọc {name}: {exc}")
        score=cham_diem(story); print(f"{name}: {score['tong_diem']}/100")
        for warning in score["canh_bao"]: print(f"  Cảnh báo: {warning}")
        failed |= score["tong_diem"]<75
    return int(failed)
if __name__=="__main__": raise SystemExit(main())
