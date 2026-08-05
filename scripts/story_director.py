#!/usr/bin/env python3
"""AI Story Director V3.6: phân loại và đạo diễn video người que.

Mặc định module chạy hoàn toàn cục bộ. Giao diện ``NhaCungCapAI`` là điểm
mở rộng cho OpenAI/Gemini; khóa và lời gọi mạng luôn thuộc ứng dụng tích hợp,
không được lưu trong kho mã nguồn này.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import random
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

try:
    from .script_writer import NhaCungCapVietKichBan, tao_ban_thao, viet_lai_tu_nhien
    from .cham_diem_kich_ban import cham_diem
    from .story_similarity import too_similar
    from .story_timing import fit_scene_narrations_to_duration
    from .visual_planner import apply_visual_plans
except ImportError:
    from script_writer import NhaCungCapVietKichBan, tao_ban_thao, viet_lai_tu_nhien
    from cham_diem_kich_ban import cham_diem
    from story_similarity import too_similar
    from story_timing import fit_scene_narrations_to_duration
    from visual_planner import apply_visual_plans

LOAI_NOI_DUNG = (
    "danh sách", "giải thích", "câu chuyện", "đối thoại", "so sánh",
    "hướng dẫn", "tin tức", "phân tích", "trích dẫn hoặc quan điểm",
    "hài tình huống", "kể chuyện kết hợp giải thích",
)

TU_KHOA_PHAN_LOAI = {
    "danh sách": (r"\b\d+\s+", "dấu hiệu", "sai lầm", "mẹo"),
    "đối thoại": ("hai người", "tranh luận", "nói chuyện", "sếp và", "đối thoại"),
    "so sánh": ("khác nhau", "so sánh", " hay ", "và người nghèo", "làm thuê và"),
    "hướng dẫn": ("cách ", "các bước", "hướng dẫn", "làm thế nào"),
    "tin tức": ("hôm nay", "tin mới", "chuẩn bị ra", "vừa công bố", "cập nhật"),
    "hài tình huống": ("khi ", "gặp sếp", "người yêu hỏi", "trớ trêu", "dở khóc"),
    "câu chuyện": ("câu chuyện", "một bài học", "lịch sử", "hành trình", "ngày ấy"),
    "phân tích": ("tác động", "thất bại", "phân tích", "hệ quả", "xu hướng"),
    "giải thích": ("vì sao", "tại sao", "nguyên nhân", "do đâu"),
    "trích dẫn hoặc quan điểm": ("đôi khi", "không cần", "quan điểm", "sức mạnh", "trưởng thành"),
}

CAU_TRUC = {
    "danh sách": ["Mở đầu gây chú ý", "Giới thiệu danh sách", "Các mục thực hành", "Tóm tắt", "Lời kêu gọi"],
    "giải thích": ["Câu hỏi mở đầu", "Hiện tượng", "Nguyên nhân", "Ví dụ", "Góc nhìn ngược", "Bài học", "Kết luận"],
    "câu chuyện": ["Mở cảnh", "Nhân vật", "Vấn đề", "Xung đột", "Quyết định", "Cao trào", "Kết quả", "Bài học"],
    "đối thoại": ["Tình huống", "Lượt nói A", "Phản hồi B", "Tranh luận", "Hiểu lầm", "Chuyển biến", "Kết luận"],
    "so sánh": ["Nêu hai đối tượng", "Khác biệt thứ nhất", "Khác biệt thứ hai", "Ví dụ", "Ưu điểm", "Nhược điểm", "Kết luận"],
    "hướng dẫn": ["Đích đến", "Chuẩn bị", "Các bước", "Kiểm tra", "Lỗi cần tránh", "Duy trì", "Kêu gọi thực hành"],
    "tin tức": ["Tiêu điểm", "Sự kiện", "Bối cảnh", "Dữ kiện", "Ảnh hưởng", "Phản ứng", "Điều cần theo dõi"],
    "phân tích": ["Luận đề", "Dấu hiệu", "Dữ kiện", "Nguyên nhân gốc", "Hệ quả", "Phản biện", "Kịch bản", "Kết luận"],
    "trích dẫn hoặc quan điểm": ["Mệnh đề", "Tình huống", "Lập luận", "Đối chiếu", "Chiêm nghiệm", "Thông điệp"],
    "hài tình huống": ["Gài tình huống", "Kỳ vọng", "Va chạm", "Hiểu nhầm", "Cú bẻ", "Phản ứng", "Chốt hài"],
    "kể chuyện kết hợp giải thích": ["Mở nút thắt", "Nhân vật", "Hiện tượng", "Nguyên nhân", "Bước ngoặt", "Giải nghĩa", "Bài học"],
}

STORY_ARC = [
    ("Hook", "Móc câu", "Mở một chi tiết lạ để tạo tò mò ngay lập tức", 88),
    ("Context", "Bối cảnh", "Giới thiệu nhân vật hoặc nơi câu chuyện bắt đầu", 35),
    ("Conflict", "Xung đột", "Đặt vấn đề cụ thể khiến nhân vật bị kẹt", 62),
    ("Development", "Phát triển", "Cho nhân vật thử một hành động làm câu chuyện tiến lên", 72),
    ("Turning Point", "Bước ngoặt", "Một sự kiện hoặc nhận ra làm đổi hướng diễn biến", 95),
    ("Ending", "Kết thúc", "Khép lại kết quả của câu chuyện", 58),
    ("Lesson", "Bài học", "Chốt lại 1–2 câu ngắn, không triết lý dài", 42),
]
IMAGE_FOCUS_BY_ROLE = {
    "Hook": ["unexpected close-up object", "empty chair under spotlight", "door half open"],
    "Context": ["small room with desk", "street corner morning", "workshop table with notebook"],
    "Conflict": ["messy desk and warning note", "split path with obstacle", "tense conversation at table"],
    "Development": ["hands arranging notes", "person walking along path", "calendar with marked deadline"],
    "Turning Point": ["key falling onto table", "light through window", "arrow changing direction"],
    "Ending": ["quiet room after decision", "completed checklist", "person leaving doorway"],
    "Lesson": ["simple icon of compass", "single highlighted note", "path toward sunrise"],
}
HOOK_BANNED = ("hôm nay", "bạn có biết", "hãy")

def _story_arc_role(index: int, count: int) -> tuple[str, str, str, int]:
    if count <= 1:
        return STORY_ARC[-1]
    pos = round(index * (len(STORY_ARC) - 1) / (count - 1))
    base_role, progress, note, dramatic = STORY_ARC[min(pos, len(STORY_ARC) - 1)]
    if count <= len(STORY_ARC):
        return base_role, progress, note, dramatic
    previous_positions = [round(i * (len(STORY_ARC) - 1) / (count - 1)) for i in range(index)]
    occurrence = previous_positions.count(pos) + 1
    role = base_role if occurrence == 1 else f"{base_role} {occurrence}"
    return role, progress, note, dramatic

def _sanitize_hook(text: str, idea: str) -> str:
    stripped = text.strip()
    low = stripped.casefold()
    if any(low.startswith(bad) for bad in HOOK_BANNED):
        subject = idea.strip(" .?!") or "câu chuyện này"
        return f"Một chi tiết nhỏ trong {subject} đã đổi mọi thứ."
    return stripped

def _rewrite_for_role(text: str, role: str, idea: str, previous: list[str]) -> str:
    subject = idea.strip(" .?!") or "chuyện này"
    variant = len(previous) + 1
    templates = {
        "Hook": f"Một dấu hiệu nhỏ xuất hiện trước khi {subject} trở nên nghiêm trọng.",
        "Context": f"Nhân vật bắt đầu ở cảnh {variant}: một bối cảnh đời thường quanh {subject}.",
        "Conflict": f"Rắc rối ở cảnh {variant} không nằm ở khẩu hiệu, mà ở một lựa chọn đang chặn đường tiến lên.",
        "Development": f"Ở cảnh {variant}, nhân vật thử đổi cách làm: quan sát dữ kiện, ghi lại phản ứng, rồi hành động từng bước.",
        "Turning Point": f"Bước ngoặt ở cảnh {variant}: nhân vật nhận ra câu hỏi đúng không phải là cố thêm, mà là đổi hướng đúng chỗ.",
        "Ending": f"Kết quả khép lại ở cảnh {variant} bằng một hành động rõ ràng, không phải một lời hô hào lặp lại.",
        "Lesson": f"Bài học ngắn: đừng lặp khẩu hiệu. Tìm nút thắt và xử lý nó.",
    }
    candidate = text.strip()
    if role == "Hook":
        candidate = _sanitize_hook(candidate, idea)
    for prior in previous:
        if too_similar(candidate, prior):
            candidate = templates[_base_role(role)]
            break
    while any(too_similar(candidate, prior) for prior in previous):
        base_role = _base_role(role)
        candidate = f"{candidate} Chi tiết riêng của cảnh {variant}: {IMAGE_FOCUS_BY_ROLE[base_role][variant % len(IMAGE_FOCUS_BY_ROLE[base_role])]}."
        break
    return candidate

def _base_role(role: str) -> str:
    return re.sub(r"\s+\d+$", "", role)

def _image_focus(role: str, index: int) -> str:
    options = IMAGE_FOCUS_BY_ROLE[_base_role(role)]
    return options[index % len(options)]

class NhaCungCapAI(Protocol):
    """Hợp đồng tương thích cho nhà cung cấp tạo toàn bộ story.json."""
    def tao_cau_chuyen(self, yeu_cau: dict) -> dict: ...


def phan_loai_chu_de(y_tuong: str) -> str:
    """Chọn loại nội dung; chỉ quyết định cấu trúc, không viết lời dẫn."""
    text = y_tuong.casefold().strip()
    scores = {
        kind: sum(bool(re.search(key, text) if key.startswith(r"\b") else key in text) for key in keys)
        for kind, keys in TU_KHOA_PHAN_LOAI.items()
    }
    best = max(scores, key=scores.get)
    return best if scores[best] else "kể chuyện kết hợp giải thích"

def _so_canh(kind: str, duration: int, idea: str) -> int:
    ranges = {30: (5, 7), 45: (7, 10), 60: (9, 13), 90: (12, 16), 180: (24, 32)}
    low, high = ranges[duration]
    if kind == "danh sách":
        match = re.search(r"\b(\d+)\b", idea)
        return min(high, max(low, (int(match.group(1)) if match else low - 2) + 2))
    preferred = {"câu chuyện": low + 1, "đối thoại": low + 2, "phân tích": high,
                 "giải thích": low + 1, "hài tình huống": low + 2}.get(kind, low)
    return min(high, preferred)


def _thoi_luong_canh(total: int, count: int, seed: int) -> list[float]:
    weights = [1 + (((seed >> (i % 12)) & 3) - 1.5) * .055 for i in range(count)]
    values = [round(total * w / sum(weights), 2) for w in weights]
    values[-1] = round(values[-1] + total - sum(values), 2)
    return values


@dataclass
class CauHinh:
    y_tuong: str
    thoi_luong: int = 45
    giong_dieu: str = "sâu sắc"
    dinh_dang: str = "tự động"
    phong_cach: str = "dark_neon"
    giong_doc: str = "Nam miền Bắc Nội lực Plus"
    muc_chuyen_dong: str = "medium"
    che_do: str = "tu_dong"
    phong_cach_viet: str = "tu_dong_theo_chu_de"


def tao_cau_chuyen(c: CauHinh, nha_cung_cap: NhaCungCapAI | None = None,
                   nha_viet: NhaCungCapVietKichBan | None = None) -> dict:
    if c.thoi_luong not in (30, 45, 60, 90, 180):
        raise ValueError("Thời lượng chỉ nhận 30, 45, 60, 90 hoặc 180 giây")
    override = {"mot_nguoi": None, "Một người dẫn chuyện": None,
                "doi_thoai": "đối thoại", "Hai nhân vật đối thoại": "đối thoại",
                "ke_chuyen": "câu chuyện", "Kể chuyện": "câu chuyện",
                "danh_sach": "danh sách", "Danh sách": "danh sách",
                "phan_tich": "phân tích", "Phân tích": "phân tích"}
    kind = override.get(c.che_do) or phan_loai_chu_de(c.y_tuong)
    force_single = c.che_do in {"mot_nguoi", "Một người dẫn chuyện"}
    if nha_cung_cap:
        return nha_cung_cap.tao_cau_chuyen({"cau_hinh": c.__dict__, "loai_noi_dung": kind})

    seed = int(hashlib.sha256(f"{c.y_tuong}|{kind}|{c.giong_dieu}".encode()).hexdigest()[:12], 16)
    rng = random.Random(seed)
    count = _so_canh(kind, c.thoi_luong, c.y_tuong)
    ban_thao, linh_vuc, phong_cach_mac_dinh = tao_ban_thao(c.y_tuong, count, kind, nha_viet)
    phong_cach_viet = PHONG_CACH_VI.get(c.phong_cach_viet) or phong_cach_mac_dinh
    roles = CAU_TRUC[kind]
    durations = _thoi_luong_canh(c.thoi_luong, count, seed)
    actions = ["suy nghĩ", "chỉ tay", "dùng laptop", "gật đầu", "khoanh tay", "đi bộ", "giơ tay", "lắc đầu", "dùng điện thoại", "vui mừng"]
    emotions = ["suy nghĩ", "tự tin", "bình thường", "bất ngờ", "lo lắng", "nghiêm túc", "phấn khích", "bối rối", "vui", "thất vọng"]
    backgrounds = ["văn phòng", "bảng trình bày", "quán cà phê", "đường phố", "lớp học", "nền tối", "phòng họp", "công viên", "sân khấu", "không gian tối giản"]
    layouts = ["câu hỏi lớn", "nhân vật và bảng", "một nhân vật bên trái", "nhân vật và số liệu lớn", "màn hình chia đôi", "hai nhân vật đối diện", "trước và sau", "trích dẫn", "một nhân vật ở giữa", "kết luận"]
    cameras = ["zoom-in", "pan-right", "push", "zoom-out", "pan-left", "pull", "dolly", "parallax", "handheld", "orbit"]
    transitions = ["fade", "slide", "blur", "whip", "flash", "camera-cut", "scale"]
    gesture_map = {"suy nghĩ":"think", "chỉ tay":"point-right", "dùng laptop":"use-laptop", "gật đầu":"idle", "khoanh tay":"cross-arms", "đi bộ":"walk", "giơ tay":"hands-up", "lắc đầu":"angry", "dùng điện thoại":"use-phone", "vui mừng":"wave"}
    emotion_map = {"suy nghĩ":"thinking", "tự tin":"smile", "bình thường":"neutral", "bất ngờ":"excited", "lo lắng":"scared", "nghiêm túc":"serious", "phấn khích":"excited", "bối rối":"confused", "vui":"happy", "thất vọng":"sad"}
    style_map = {"người_que_triết_lý":"philosophy", "người_que_tiktok":"tiktok", "người_que_doanh_nhân":"entrepreneur", "người_que_kể_chuyện":"storytelling", "tin_tức_ai":"news"}
    strength = {"light": .45, "medium": .75, "high": 1.05, "viral": 1.35}.get(c.muc_chuyen_dong, .75)
    scenes = []
    for i in range(count):
        # Các độ lệch phụ thuộc chủ đề khiến chuỗi đạo diễn khác nhau nhưng vẫn tái lập được.
        offset = (seed % 7 + i * (2 if kind in {"câu chuyện", "hài tình huống"} else 3))
        action, emotion = actions[offset % len(actions)], emotions[(offset + i) % len(emotions)]
        two_people = not force_single and (kind in {"đối thoại", "hài tình huống"} or (kind == "câu chuyện" and 1 < i < count - 2))
        chars = [{"ten":"A", "vi_tri":"trai" if two_people else "giữa", "hanh_dong":action,
                  "cam_xuc":emotion, "huong_nhin":"nhân vật B" if two_people else "khán giả",
                  "name":"A", "position":"left" if two_people else "center", "action":action,
                  "gesture":gesture_map[action], "emotion":emotion_map[emotion]}]
        if two_people:
            second_action = actions[(offset + 4) % len(actions)]
            chars.append({"ten":"B", "vi_tri":"phải", "hanh_dong":second_action, "cam_xuc":emotions[(offset+3)%len(emotions)],
                          "huong_nhin":"nhân vật A", "name":"B", "position":"right", "action":second_action,
                          "gesture":gesture_map[second_action], "emotion":emotion_map[emotions[(offset+3)%len(emotions)]]})
        arc_role, story_progress, role_note, dramatic_level = _story_arc_role(i, count)
        previous_narrations = [scene["narration"] for scene in scenes]
        narration = _rewrite_for_role(ban_thao.canh[min(i, len(ban_thao.canh)-1)], arc_role, c.y_tuong, previous_narrations)
        camera = cameras[offset % len(cameras)]
        transition = transitions[(offset + i) % len(transitions)]
        layout = layouts[(offset + 2*i) % len(layouts)]
        background = backgrounds[(offset + (seed % 3)*i) % len(backgrounds)]
        role = arc_role
        scene = {
            "id": i + 1, "loai_canh": "mở đầu" if i == 0 else "kết" if i == count-1 else kind,
            "vai_tro": role, "thoi_luong": durations[i], "loi_dan": narration,
            "hoi_thoai": ([ban_thao.hoi_thoai[i-1]] if kind == "đối thoại" and 0 < i <= len(ban_thao.hoi_thoai) else []),
            "tieu_de_canh": role, "tu_khoa": [w for w in re.findall(r"\w+", c.y_tuong.lower()) if len(w)>3][:3],
            "sceneRole": arc_role, "storyProgress": story_progress, "imageFocus": _image_focus(arc_role, i), "dramaticLevel": dramatic_level,
            "boi_canh": background, "bo_cuc": layout, "camera": {"type":camera, "speed":round(rng.uniform(.88,1.12),2), "easing":"ease-in-out", "strength":strength, "duration":durations[i]},
            "chuyen_canh": {"type":transition, "strength":strength, "duration":round(rng.uniform(.3,.7),2)},
            "hoat_anh_phu_de": ["pop","fade","slide","word","karaoke"][offset % 5], "nhan_vat": chars,
            # Trường kỹ thuật tương thích Remotion V3.
            "type":"intro" if i==0 else "outro" if i==count-1 else "dialogue" if two_people else "explanation",
            "duration":durations[i], "narration":narration,
            "dialogue":([{"character":ban_thao.hoi_thoai[i-1]["nhan_vat"],"text":ban_thao.hoi_thoai[i-1]["noi_dung"]}] if kind == "đối thoại" and 0 < i <= len(ban_thao.hoi_thoai) else []), "background":"dark",
            "transition":{"type":transition, "strength":strength, "duration":round(rng.uniform(.3,.7),2)},
            "emotion":chars[0]["emotion"], "gesture":chars[0]["gesture"], "zoom":round(rng.uniform(.06,.14),2),
            "subtitleAnimation":["pop","fade","slide","word","karaoke"][offset % 5],
            "keywords":[w for w in re.findall(r"\w+", c.y_tuong.lower()) if len(w)>3][:3], "characters":chars,
            "seed":rng.randrange(1, 1_000_000), "layout":layout, "roleNote": role_note,
        }
        scenes.append(scene)
    timing = fit_scene_narrations_to_duration(scenes, c.thoi_luong)
    summary = f"Video {kind} về {c.y_tuong}, được đạo diễn theo giọng {c.giong_dieu}."
    structure = " → ".join(CAU_TRUC[kind])
    story = {
        "phien_ban":"3.7", "tieu_de":c.y_tuong, "loai_noi_dung":kind, "cau_truc_kich_ban":structure,
        "linh_vuc":linh_vuc, "phong_cach_viet":phong_cach_viet,
        "thoi_luong":c.thoi_luong, "phong_cach":c.phong_cach, "giong_doc":c.giong_doc,
        "tom_tat":summary, "thong_diep_chinh":f"Hiểu và hành động phù hợp với {c.y_tuong}.", "canh":scenes,
        "version":3, "title":c.y_tuong, "hook":ban_thao.hook, "cao_trao":ban_thao.cao_trao,
        "ket_luan":ban_thao.ket_luan, "message":f"Hiểu rõ {c.y_tuong} trước khi hành động.",
        "cta":scenes[-1]["narration"], "duration":c.thoi_luong, "style":style_map.get(c.phong_cach,c.phong_cach),
        "motionLevel":c.muc_chuyen_dong, "voice":c.giong_doc, "audio":"assets/narration.mp3", "scenes":scenes,
        "timing": timing, "targetWordCount": timing["targetWordCount"], "estimatedDuration": timing["estimatedDuration"],
    }
    apply_visual_plans(story)
    for _ in range(3):
        score = cham_diem(story)
        if score["tong_diem"] >= 75:
            break
        for scene in scenes:
            scene["loi_dan"] = scene["narration"] = viet_lai_tu_nhien(scene["loi_dan"])
    story["chat_luong_kich_ban"] = score
    return story


PHONG_CACH_VI = {
    "tu_dong_theo_chu_de":"", "Tự động theo chủ đề":"",
    "ngan_gon_tiktok":"ngắn gọn TikTok", "Ngắn gọn TikTok":"ngắn gọn TikTok",
    "ke_chuyen_cam_xuc":"kể chuyện cảm xúc", "Kể chuyện cảm xúc":"kể chuyện cảm xúc",
    "thuc_te_kinh_doanh":"thực tế kinh doanh", "Thực tế kinh doanh":"thực tế kinh doanh",
    "giai_thich_de_hieu":"giải thích dễ hiểu", "Giải thích dễ hiểu":"giải thích dễ hiểu",
    "doi_thoai_tu_nhien":"đối thoại tự nhiên", "Đối thoại tự nhiên":"đối thoại tự nhiên",
    "tin_tuc_ro_rang":"tin tức rõ ràng", "Tin tức rõ ràng":"tin tức rõ ràng",
}


def _parser() -> argparse.ArgumentParser:
    p=argparse.ArgumentParser(description="Tạo kịch bản bằng AI Story Director và AI Script Writer Pro V3.6")
    p.add_argument('--idea','--y-tuong','--ý-tưởng',required=True); p.add_argument('--duration','--thoi-luong','--thời-lượng',type=int,default=45)
    p.add_argument('--tone','--giong-dieu','--giọng-điệu',default='sâu sắc'); p.add_argument('--format','--content-format','--dinh-dang','--định-dạng',dest='content_format',default='hybrid')
    p.add_argument('--style','--phong-cach','--phong-cách',default='dark_neon'); p.add_argument('--voice','--giong-doc','--giọng-đọc',default='Nam miền Bắc Nội lực Plus')
    p.add_argument('--motion-level','--muc-do-chuyen-dong','--mức-độ-chuyển-động',default='medium'); p.add_argument('--script-mode','--che-do-viet-kich-ban',default='tu_dong')
    p.add_argument('--writing-style','--phong-cach-viet',default='tu_dong_theo_chu_de',choices=PHONG_CACH_VI)
    p.add_argument('--output',default='assets/story.json',help='Đường dẫn story.json')
    return p


def main() -> None:
    p=_parser(); a=p.parse_args()
    motion={'nhẹ':'light','trung_bình':'medium','nhiều':'high','viral_tiktok':'viral'}.get(a.motion_level,a.motion_level)
    if motion not in {'light','medium','high','viral'}: p.error('Mức chuyển động không hợp lệ')
    config=CauHinh(a.idea,a.duration,a.tone,a.content_format,a.style,a.voice,motion,a.script_mode,a.writing_style)
    try: story=tao_cau_chuyen(config)
    except ValueError as exc: p.error(str(exc))
    output=Path(a.output); output.parent.mkdir(parents=True,exist_ok=True); Path('output').mkdir(exist_ok=True)
    output.write_text(json.dumps(story,ensure_ascii=False,indent=2),encoding='utf-8')
    Path('output/script.txt').write_text('\n'.join(s['loi_dan'] for s in story['canh']),encoding='utf-8')
    print(f"Đã phân loại: {story['loai_noi_dung']}")
    print(f"Đã tạo {len(story['canh'])} cảnh, tổng thời lượng scene {sum(s['thoi_luong'] for s in story['canh']):.1f} giây, ước lượng đọc {story['estimatedDuration']:.1f} giây")
    print(f"Điểm chất lượng kịch bản: {story['chat_luong_kich_ban']['tong_diem']}/100")
    for warning in story['chat_luong_kich_ban']['canh_bao']: print(f"Cảnh báo: {warning}")


if __name__=='__main__': main()
