import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).parents[1]
from scripts.story_director import CauHinh, LOAI_NOI_DUNG, phan_loai_chu_de, tao_cau_chuyen


@pytest.mark.parametrize(("idea", "expected"), [
    ("7 cách tiết kiệm tiền", "danh sách"),
    ("Vì sao người giỏi ít nói?", "giải thích"),
    ("Câu chuyện người bán hàng nghèo", "câu chuyện"),
    ("Hai người tranh luận về tiền", "đối thoại"),
    ("Người giàu và người nghèo khác nhau", "so sánh"),
    ("Các bước xây dựng thói quen", "hướng dẫn"),
    ("Giá vàng hôm nay thay đổi", "tin tức"),
    ("Tác động của mạng xã hội", "phân tích"),
    ("Im lặng đôi khi là sức mạnh", "trích dẫn hoặc quan điểm"),
    ("Khi nhân viên xin nghỉ nhưng gặp sếp", "hài tình huống"),
])
def test_phan_loai_du_muoi_loai(idea, expected):
    assert expected in LOAI_NOI_DUNG
    assert phan_loai_chu_de(idea) == expected


@pytest.mark.parametrize(("duration", "minimum", "maximum"), [(30, 5, 7), (45, 7, 10), (60, 9, 13)])
def test_so_canh_va_thoi_luong_linh_hoat(duration, minimum, maximum):
    story = tao_cau_chuyen(CauHinh("Cách quản lý thời gian", duration))
    assert minimum <= len(story["canh"]) <= maximum
    assert abs(sum(s["thoi_luong"] for s in story["canh"]) - duration) <= 1
    assert story["scenes"] is story["canh"]
    assert all(s["characters"] is s["nhan_vat"] for s in story["canh"])


def test_hai_video_mau_khac_nhau(tmp_path):
    paths=[]
    for name, idea, tone, style, mode in [
        ("a", "7 cách tiết kiệm tiền hiệu quả", "gần gũi", "người_que_doanh_nhân", "mot_nguoi"),
        ("b", "Lịch sử hình thành Internet", "kiến thức", "người_que_kể_chuyện", "tu_dong"),
    ]:
        path=tmp_path/f"{name}.json"; story=tao_cau_chuyen(CauHinh(idea,45,tone,"hybrid",style,che_do=mode))
        path.write_text(json.dumps(story,ensure_ascii=False),encoding="utf-8"); paths.append(path)
    result=subprocess.run([sys.executable,str(ROOT/"scripts/kiem_tra_do_khac_nhau.py"),*map(str,paths)],capture_output=True,text=True)
    assert result.returncode == 0, result.stdout + result.stderr
