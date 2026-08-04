#!/usr/bin/env python3
"""So sánh mức trùng lặp của hai tệp story.json."""
import argparse
import json
import re
import sys
from difflib import SequenceMatcher
from pathlib import Path

NGUONG = {"câu chữ": .25, "hành động": .50, "camera": .60, "bố cục": .60, "chuyển cảnh": .60}

def _scenes(data): return data.get("canh") or data.get("scenes") or []
def _value(scene, vi, en):
    value=scene.get(vi,scene.get(en,"")); return value.get("type","") if isinstance(value,dict) else value
def _ratio(a,b): return SequenceMatcher(None,a,b,autojunk=False).ratio() if a or b else 0.0
def _text_ratio(sa, sb):
    """Tỷ lệ câu tương đồng ngữ bề mặt, thay vì phạt các hư từ tiếng Việt chung."""
    normalize=lambda text:" ".join(re.sub(r"[^\w\s]","",text.casefold()).split())
    a=[normalize(_value(s,"loi_dan","narration")) for s in sa]
    b=[normalize(_value(s,"loi_dan","narration")) for s in sb]
    similar=sum(any(SequenceMatcher(None,x,y,autojunk=False).ratio() >= .82 for y in b) for x in a)
    return similar/max(len(a),len(b),1)
def so_sanh(a,b):
    sa,sb=_scenes(a),_scenes(b)
    actions=lambda scenes:[_value(c,"hanh_dong","action") for s in scenes for c in (s.get("nhan_vat") or s.get("characters") or [])]
    return {"câu chữ":_text_ratio(sa,sb), "hành động":_ratio(actions(sa),actions(sb)),
            "camera":_ratio([_value(s,"camera","camera") for s in sa],[_value(s,"camera","camera") for s in sb]),
            "bố cục":_ratio([_value(s,"bo_cuc","layout") for s in sa],[_value(s,"bo_cuc","layout") for s in sb]),
            "chuyển cảnh":_ratio([_value(s,"chuyen_canh","transition") for s in sa],[_value(s,"chuyen_canh","transition") for s in sb])}
def main():
    p=argparse.ArgumentParser(description="Kiểm tra độ khác nhau giữa hai kịch bản"); p.add_argument("tep_a"); p.add_argument("tep_b"); args=p.parse_args()
    try: data=[json.loads(Path(x).read_text(encoding="utf-8")) for x in (args.tep_a,args.tep_b)]
    except (OSError,json.JSONDecodeError) as exc: p.error(f"Không thể đọc kịch bản: {exc}")
    scores=so_sanh(*data); failed=[]
    for name,value in scores.items():
        state="ĐẠT" if value < NGUONG[name] else "KHÔNG ĐẠT"; print(f"{name.capitalize()}: {value:.1%} — {state} (ngưỡng dưới {NGUONG[name]:.0%})")
        if value>=NGUONG[name]: failed.append(name)
    if failed: print("Kiểm tra thất bại: " + ", ".join(failed),file=sys.stderr); return 1
    print("Kiểm tra đạt: hai kịch bản khác nhau rõ rệt."); return 0
if __name__=="__main__": raise SystemExit(main())
