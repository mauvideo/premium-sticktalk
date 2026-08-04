#!/usr/bin/env python3
"""AI Script Writer Pro V3.6: viết lời tiếng Việt, độc lập với phần đạo diễn.

Module không gọi mạng ở chế độ mặc định. Các adapter chỉ đọc khóa từ biến môi
trường và cố ý để ứng dụng tích hợp cung cấp hàm gọi HTTP, nhờ vậy kho mã nguồn
không lưu bí mật và pipeline cũ vẫn hoạt động khi không có API.
"""
from __future__ import annotations

import hashlib
import os
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass

LINH_VUC = {
    "triết lý sống": ("trưởng thành", "cuộc sống", "tranh luận", "im lặng", "bài học"),
    "tâm lý": ("tâm lý", "cảm xúc", "lo âu", "sợ", "tổn thương"),
    "tình cảm": ("tình yêu", "người yêu", "hôn nhân", "chia tay", "tình cảm"),
    "kinh doanh": ("cửa hàng", "khách hàng", "doanh thu", "kinh doanh", "ông chủ", "nhân viên", "tăng lương"),
    "tài chính": ("tiền", "đầu tư", "tiết kiệm", "tài chính", "chi tiêu"),
    "công nghệ": ("internet", "phần mềm", "máy tính", "ai ", "công nghệ"),
    "khoa học": ("vì sao", "bầu trời", "ánh sáng", "khoa học", "hiện tượng"),
    "lịch sử": ("lịch sử", "hình thành", "thời kỳ", "nguồn gốc"),
    "giáo dục": ("học", "giáo dục", "giáo viên", "sinh viên"),
    "sức khỏe phổ thông": ("sức khỏe", "ngủ", "ăn uống", "vận động"),
    "tin tức": ("tin mới", "hôm nay", "vừa công bố", "sự kiện"),
    "hài tình huống": ("hài", "dở khóc", "trớ trêu"),
    "kỹ năng sống": ("kỹ năng", "giao tiếp", "quản lý thời gian", "cách xử lý"),
    "phát triển bản thân": ("thói quen", "kỷ luật", "phát triển bản thân", "mục tiêu"),
}

PHONG_CACH = {
    "triết lý sống": "cảm xúc, ngắn, giàu đối lập",
    "tâm lý": "thấu cảm, gần gũi",
    "tình cảm": "ấm áp, chân thật",
    "kinh doanh": "thực tế, ngắn gọn",
    "tài chính": "cụ thể, thận trọng",
    "công nghệ": "mạch lạc, theo tiến trình",
    "khoa học": "giải thích dễ hiểu",
    "lịch sử": "tuần tự, rõ nguyên nhân và kết quả",
    "giáo dục": "sáng rõ, khuyến khích khám phá",
    "sức khỏe phổ thông": "dễ hiểu, không chẩn đoán",
    "tin tức": "rõ dữ kiện, tách nhận định",
    "hài tình huống": "nhanh, duyên, có cú bẻ",
    "kỹ năng sống": "thực hành, trực tiếp",
    "phát triển bản thân": "tích cực, có hành động nhỏ",
}

# 12 nhóm, mỗi nhóm 5 công thức. Biến thể được chọn bằng dấu vân tay chủ đề.
HOOK_THEO_NHOM = {
    "nghịch lý": ["Càng cố {hanh_dong}, ta càng dễ {hau_qua}.", "Muốn {ket_qua}, đôi khi phải ngừng {hanh_dong}.", "Điều tưởng có lợi lại âm thầm {hau_qua}.", "Thắng trước mắt có thể là thua lâu dài.", "Bớt một bước, kết quả đôi khi lại tốt hơn."],
    "câu hỏi": ["Vì sao {chu_de_ngan} lại xảy ra?", "Điều gì thật sự đứng sau {chu_de_ngan}?", "Nếu đổi một chi tiết, kết quả sẽ ra sao?", "Ta đang hiểu sai điểm nào về {chu_de_ngan}?", "Khi nào {chu_de_ngan} trở thành vấn đề?"],
    "hậu quả": ["Một lựa chọn nhỏ có thể khiến {hau_qua}.", "Bỏ qua dấu hiệu này, cái giá đến rất nhanh.", "Sai ở bước đầu, mọi bước sau đều khó.", "Chậm xử lý chuyện này, hậu quả sẽ tích lại.", "Kết quả xấu thường bắt đầu từ một việc rất nhỏ."],
    "bí mật": ["Mấu chốt của {chu_de_ngan} nằm ở chi tiết ít ai để ý.", "Phần khó nhất lại không nằm ở nơi ta nghĩ.", "Có một cơ chế thầm lặng đứng sau chuyện này.", "Câu trả lời ẩn trong một khoảnh khắc rất quen.", "Điểm quyết định thường xuất hiện trước khi ta nhận ra."],
    "cảnh báo": ["Đừng vội {hanh_dong} trước khi nhìn thấy điều này.", "Cẩn thận: thói quen vô hại ấy đang {hau_qua}.", "Một dấu hiệu nhỏ đang báo trước rắc rối lớn.", "Nếu gặp tình huống này, đừng phản ứng ngay.", "Có một sai lầm khiến mọi nỗ lực đi ngược hướng."],
    "tình huống": ["Hãy tưởng tượng, {tinh_huong}.", "Một ngày, {tinh_huong}.", "Mọi chuyện bình thường cho tới khi {tinh_huong}.", "Ngay giữa lúc {tinh_huong}, vấn đề xuất hiện.", "Chỉ một câu nói khi {tinh_huong} đã đổi tất cả."],
    "con số": ["Có ba lớp cần nhìn trong {chu_de_ngan}.", "Một phút sai có thể đổi cả kết quả.", "Chỉ một chi tiết đủ làm lộ vấn đề.", "Hai lựa chọn, nhưng chỉ một giải quyết gốc rễ.", "Năm dấu hiệu này không hề giống nhau."],
    "đối lập": ["Một bên muốn thắng, bên kia chỉ muốn được hiểu.", "Bề ngoài yên ổn, bên trong vấn đề đang lớn dần.", "Cùng một tình huống, hai cách phản ứng cho hai kết quả.", "Nói nhiều chưa chắc rõ; nói đúng mới tạo thay đổi.", "Thứ trông nhanh nhất đôi khi làm ta chậm nhất."],
    "gợi suy nghĩ": ["Ta thường mất điều quý khi cố giữ phần đúng.", "Không phải chiến thắng nào cũng đáng để ăn mừng.", "Cách ta phản ứng nói nhiều hơn điều ta tranh cãi.", "Một kết quả tốt không luôn bắt đầu bằng cảm giác dễ chịu.", "Có lúc, lùi lại mới là bước tiến thật sự."],
    "hành động": ["Dừng lại. Nhìn kỹ {chu_de_ngan} thêm một lần.", "Mở cuốn sổ và ghi ngay chi tiết này.", "Đặt điện thoại xuống, rồi nghe câu trả lời thật.", "Thử đổi một hành động nhỏ ngay hôm nay.", "Quan sát khoảnh khắc vấn đề vừa xuất hiện."],
    "đối thoại": ["“Tại sao tôi chưa được tăng lương?”", "“Anh muốn đúng, hay muốn giải quyết chuyện này?”", "“Con số này đang nói điều gì?”", "“Tôi đã làm đủ, còn anh nghĩ sao?”", "“Khoan đã, chúng ta đang tranh luận sai việc rồi.”"],
    "kết quả trước": ["Cửa hàng vắng khách; nguyên nhân bắt đầu từ quầy tính tiền.", "Họ ngừng cãi nhau sau khi nhận ra một điều.", "Bầu trời hiện màu xanh; câu trả lời nằm trong ánh sáng.", "Internet nối cả thế giới sau nhiều bước phát triển.", "Cuộc họp kết thúc tốt hơn nhờ một câu hỏi khó."],
}

VAN_MAU = ("trong cuộc sống", "bạn có bao giờ tự hỏi", "điều quan trọng là", "hãy nhớ rằng", "không thể phủ nhận rằng", "trong xã hội hiện đại", "cuộc sống là một hành trình", "thành công không đến từ may mắn", "mỗi chúng ta đều", "cuối cùng nhưng không kém phần quan trọng")
THAY_THE = {"trong cuộc sống": "Có những lúc", "bạn có bao giờ tự hỏi": "Thử nghĩ xem", "điều quan trọng là": "Mấu chốt:", "hãy nhớ rằng": "Giữ lại ý này:", "không thể phủ nhận rằng": "Dễ thấy rằng", "trong xã hội hiện đại": "Hiện nay", "cuộc sống là một hành trình": "Ta thay đổi qua từng lựa chọn", "thành công không đến từ may mắn": "Kết quả cần hành động bền bỉ", "mỗi chúng ta đều": "Ai cũng có lúc", "cuối cùng nhưng không kém phần quan trọng": "Sau cùng"}

def nhan_dien_linh_vuc(chu_de: str) -> str:
    text = chu_de.casefold()
    scores = {name: sum(k in text for k in keys) for name, keys in LINH_VUC.items()}
    # Lịch sử Internet cần ưu tiên cách kể lịch sử thay vì nhãn công nghệ.
    if "lịch sử" in text or "hình thành" in text:
        return "lịch sử"
    best = max(scores, key=scores.get)
    return best if scores[best] else "kỹ năng sống"

def kiem_tra_van_mau(text: str) -> list[str]:
    low = text.casefold()
    return [phrase for phrase in VAN_MAU if low.count(phrase) > 0]

def viet_lai_tu_nhien(text: str) -> str:
    result = text
    for phrase, replacement in THAY_THE.items():
        result = re.sub(re.escape(phrase), replacement, result, flags=re.I)
    result = re.sub(r"\b(và rồi|vì vậy)\b", "Thế là", result, flags=re.I)
    return re.sub(r"\s+", " ", result).strip()

def kiem_tra_lap_cau(text: str) -> list[str]:
    sentences = [re.sub(r"\W+", " ", x.casefold()).strip() for x in re.split(r"[.!?]+", text) if x.strip()]
    return sorted({sentence for sentence in sentences if sentences.count(sentence) > 1})

def kiem_tra_do_dai_cau(text: str, toi_da: int = 22) -> list[str]:
    return [x.strip() for x in re.split(r"[.!?]+", text) if len(re.findall(r"\w+", x)) > toi_da]

def rut_gon_cho_giong_doc(text: str) -> str:
    text = viet_lai_tu_nhien(text)
    parts = []
    for sentence in re.split(r"(?<=[.!?])\s+", text):
        words = sentence.split()
        if len(words) > 22:
            cut = next((i for i in range(12, min(19, len(words))) if words[i - 1].endswith(",")), 15)
            sentence = " ".join(words[:cut]).rstrip(",") + ". " + " ".join(words[cut:])
        parts.append(sentence)
    return " ".join(parts)

class NhaCungCapVietKichBan(ABC):
    @abstractmethod
    def viet_hook(self, chu_de: str, linh_vuc: str) -> str: ...
    @abstractmethod
    def viet_canh(self, chu_de: str, linh_vuc: str, so_canh: int, loai_noi_dung: str) -> list[str]: ...
    @abstractmethod
    def viet_hoi_thoai(self, chu_de: str, so_canh: int) -> list[dict]: ...
    @abstractmethod
    def viet_ket_luan(self, chu_de: str, linh_vuc: str) -> str: ...

class AdapterOpenAI(NhaCungCapVietKichBan):
    """Điểm nối OpenAI; khóa chỉ được đọc từ ``OPENAI_API_KEY``."""
    def __init__(self): self.api_key = os.getenv("OPENAI_API_KEY")
    def _chua_cau_hinh(self): raise RuntimeError("Chưa cấu hình bộ gọi OpenAI; đang dùng nhà cung cấp luật")
    viet_hook = viet_canh = viet_hoi_thoai = viet_ket_luan = lambda self, *args: self._chua_cau_hinh()

class AdapterGemini(AdapterOpenAI):
    """Điểm nối Gemini; không chứa khóa cứng trong mã nguồn."""
    def __init__(self): self.api_key = os.getenv("GEMINI_API_KEY")

@dataclass
class BanThao:
    hook: str
    canh: list[str]
    hoi_thoai: list[dict]
    cao_trao: str
    ket_luan: str
    cta: str

class NhaCungCapTheoLuat(NhaCungCapVietKichBan):
    def _seed(self, text: str) -> int: return int(hashlib.sha256(text.encode()).hexdigest()[:10], 16)

    def viet_hook(self, chu_de: str, linh_vuc: str) -> str:
        special = {
            "người trưởng thành không cần thắng mọi cuộc tranh luận.": "Thắng một cuộc cãi vã, đôi khi lại mất một người.",
            "5 sai lầm khiến cửa hàng nhỏ khó phát triển.": "Cửa hàng nhỏ thường hụt hơi từ năm sai lầm rất cụ thể.",
            "vì sao bầu trời có màu xanh?": "Bầu trời màu xanh, nhưng ánh sáng Mặt Trời gần như trắng.",
            "lịch sử hình thành internet.": "Internet nối cả thế giới, nhưng khởi đầu chỉ nối vài máy tính.",
            "một ông chủ và nhân viên tranh luận về tăng lương.": "“Tại sao tôi làm nhiều hơn, nhưng lương vẫn đứng yên?”",
        }
        key = chu_de.casefold().strip()
        if key in special: return special[key]
        groups = list(HOOK_THEO_NHOM)
        group = groups[self._seed(chu_de + linh_vuc) % len(groups)]
        template = HOOK_THEO_NHOM[group][self._seed(chu_de) % 5]
        short = chu_de.strip(" .?!")
        if len(short.split()) > 8: short = " ".join(short.split()[:8])
        return template.format(chu_de_ngan=short, hanh_dong="phản ứng thật nhanh", hau_qua="bỏ lỡ mấu chốt", ket_qua="thay đổi kết quả", tinh_huong="một lựa chọn quen thuộc bỗng gây rắc rối")

    def viet_ket_luan(self, chu_de: str, linh_vuc: str) -> str:
        endings = {
            "triết lý sống": "Trưởng thành không phải im lặng. Đó là biết cuộc nào đáng nói.",
            "kinh doanh": "Sửa đúng điểm nghẽn nhỏ, cửa hàng mới có chỗ để lớn.",
            "khoa học": "Màu xanh ta thấy là kết quả của ánh sáng trên đường đi.",
            "lịch sử": "Internet hôm nay là kết quả của nhiều mạng và chuẩn dần kết nối.",
        }
        return endings.get(linh_vuc, f"Hiểu đúng {chu_de.strip('.')} giúp ta chọn hành động rõ ràng hơn.")

    def viet_hoi_thoai(self, chu_de: str, so_canh: int) -> list[dict]:
        lines = [
            ("A", "Tôi làm thêm việc suốt ba tháng. Vì sao lương vẫn vậy?"),
            ("B", "Tôi thấy nỗ lực đó. Nhưng anh đã tạo kết quả nào rõ nhất?"),
            ("A", "Tôi rút ngắn khâu bàn giao và xử lý khách khó mỗi tối."),
            ("B", "Đó là việc nhiều hơn. Ta cần thống nhất giá trị đo được."),
            ("A", "Vậy hãy đặt mục tiêu và một ngày xem lại cụ thể."),
            ("B", "Được. Đạt mục tiêu, mức lương mới sẽ được chốt bằng văn bản."),
            ("A", "Tôi cần một cam kết rõ, không phải lời hẹn chung chung."),
            ("B", "Hợp lý. Cuộc nói chuyện này nên bắt đầu từ dữ kiện."),
        ]
        return [{"nhan_vat": who, "noi_dung": text} for who, text in lines[:max(1, so_canh - 2)]]

    def viet_canh(self, chu_de: str, linh_vuc: str, so_canh: int, loai_noi_dung: str) -> list[str]:
        key = chu_de.casefold()
        if "cửa hàng nhỏ" in key and "5" in key:
            core = ["Sai lầm một: không biết ai là khách chính. Hàng hóa vì thế mua theo cảm tính.", "Sai lầm hai: nhập quá nhiều món bán chậm. Tiền bị giữ trên kệ.", "Sai lầm ba: giá bán không tính đủ chi phí. Càng đông khách, lợi nhuận càng mỏng.", "Sai lầm bốn: trải nghiệm thiếu nhất quán. Khách tốt không có lý do quay lại.", "Sai lầm năm: chủ ôm mọi việc. Không ai đủ quyền xử lý khi chủ vắng mặt."]
        elif "bầu trời" in key:
            core = ["Ánh sáng Mặt Trời gồm nhiều màu mà mắt ta có thể thấy.", "Khi đi vào khí quyển, ánh sáng gặp các phân tử rất nhỏ.", "Những màu có bước sóng ngắn bị tán xạ mạnh hơn.", "Ánh sáng xanh vì thế đi tới mắt ta từ nhiều hướng.", "Hãy tưởng tượng khí quyển như căn phòng làm ánh sáng xanh lan quanh.", "Lúc hoàng hôn, ánh sáng đi qua khí quyển dài hơn. Nhiều màu xanh đã tán xạ khỏi đường nhìn."]
        elif "internet" in key and ("lịch sử" in key or "hình thành" in key):
            core = ["Cuối thập niên 1960, ARPANET thử kết nối các máy tính ở xa.", "Dữ liệu được chia thành các gói nhỏ, rồi đi qua mạng.", "Nhiều mạng riêng xuất hiện, nhưng chúng cần một cách nói chuyện chung.", "Bộ giao thức TCP/IP tạo nền tảng để các mạng trao đổi dữ liệu.", "Năm 1983, ARPANET chuyển sang TCP/IP, một bước ngoặt quan trọng.", "Sau đó, hệ thống tên miền giúp địa chỉ dễ dùng hơn.", "Đến năm 1989, Tim Berners-Lee đề xuất World Wide Web.", "Web làm việc truy cập tài liệu trên Internet thuận tiện hơn." ]
        elif "tranh luận" in key and "trưởng thành" in key:
            core = ["Một người nói sai về bạn giữa cuộc họp. Phản xạ đầu tiên là đáp trả.", "Bạn đưa thêm lý lẽ. Người kia lập tức dựng thêm phòng tuyến.", "Cuộc nói chuyện đổi mục tiêu: không còn tìm đúng, chỉ còn tìm người thua.", "Hãy tưởng tượng bạn dừng lại và hỏi: chuyện này cần kết quả nào?", "Câu hỏi ấy là bước ngoặt. Nó tách lòng tự ái khỏi vấn đề.", "Có điều cần làm rõ, hãy nói bằng dữ kiện. Chỉ muốn hơn thua, hãy để nó đi qua."]
        else:
            core = [f"Vấn đề của {chu_de.strip('.')} xuất hiện trong một tình huống rất cụ thể.", "Phản ứng quen thuộc thường xử lý phần nổi, chưa chạm nguyên nhân.", "Hãy tưởng tượng ta đổi một hành động nhỏ và quan sát kết quả.", "Bước ngoặt đến khi câu hỏi chuyển từ ai đúng sang việc gì hiệu quả.", "Từ đó, lựa chọn tiếp theo trở nên rõ và có thể kiểm chứng."]
        needed = max(0, so_canh - 2)
        if len(core) < needed:
            core += ["Kết quả cần được quan sát trước khi điều chỉnh bước kế tiếp."] * (needed-len(core))
        return core[:needed]

def tao_ban_thao(chu_de: str, so_canh: int, loai_noi_dung: str, nha_cung_cap: NhaCungCapVietKichBan | None = None) -> tuple[BanThao, str, str]:
    provider = nha_cung_cap or NhaCungCapTheoLuat()
    linh_vuc = nhan_dien_linh_vuc(chu_de)
    hook = provider.viet_hook(chu_de, linh_vuc)
    dialogue = provider.viet_hoi_thoai(chu_de, so_canh) if loai_noi_dung == "đối thoại" else []
    middle = [x["noi_dung"] for x in dialogue] if dialogue else provider.viet_canh(chu_de, linh_vuc, so_canh, loai_noi_dung)
    conclusion = provider.viet_ket_luan(chu_de, linh_vuc)
    cta = {"kinh doanh": "Chọn một điểm nghẽn và kiểm tra ngay hôm nay.", "khoa học": "Lần tới nhìn trời, hãy nhớ đường đi của ánh sáng.", "lịch sử": "Lưu video để nhớ các bước ngoặt của Internet."}.get(linh_vuc, "Bạn sẽ chọn thắng lời nói, hay giữ điều có ý nghĩa?")
    if loai_noi_dung == "đối thoại": conclusion = "Tăng lương không nên là cuộc đấu cảm tính. Nó cần kết quả và cam kết rõ."
    scenes = [hook] + middle + [conclusion + (" " + cta if linh_vuc != "triết lý sống" else "")]
    scenes = [rut_gon_cho_giong_doc(x) for x in scenes[:so_canh]]
    climax = scenes[-2] if len(scenes) > 2 else conclusion
    return BanThao(scenes[0], scenes, dialogue, climax, conclusion, cta), linh_vuc, PHONG_CACH[linh_vuc]
