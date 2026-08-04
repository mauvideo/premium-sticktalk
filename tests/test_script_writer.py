from scripts.cham_diem_kich_ban import cham_diem
from scripts.kiem_tra_do_khac_nhau import so_sanh
from scripts.script_writer import HOOK_THEO_NHOM, kiem_tra_do_dai_cau, kiem_tra_van_mau
from scripts.story_director import CauHinh, tao_cau_chuyen

CHU_DE_MAU = [
    "Người trưởng thành không cần thắng mọi cuộc tranh luận.",
    "5 sai lầm khiến cửa hàng nhỏ khó phát triển.",
    "Vì sao bầu trời có màu xanh?",
    "Lịch sử hình thành Internet.",
    "Một ông chủ và nhân viên tranh luận về tăng lương.",
]

def test_co_it_nhat_sau_muoi_cong_thuc_hook():
    assert len(HOOK_THEO_NHOM) == 12
    assert sum(map(len, HOOK_THEO_NHOM.values())) >= 60

def test_nam_kich_ban_dat_chat_luong_va_khac_nhau():
    stories=[tao_cau_chuyen(CauHinh(x,45)) for x in CHU_DE_MAU]
    assert len({x["hook"] for x in stories}) == 5
    assert all(cham_diem(x)["tong_diem"] >= 75 for x in stories)
    assert all(not kiem_tra_van_mau(" ".join(s["loi_dan"] for s in x["canh"])) for x in stories)
    assert all(so_sanh(stories[i],stories[j])["câu chữ"] < .2 for i in range(5) for j in range(i+1,5))

def test_danh_sach_du_nam_muc_va_doi_thoai_that():
    listed=tao_cau_chuyen(CauHinh(CHU_DE_MAU[1],45))
    assert sum("Sai lầm" in x["loi_dan"] for x in listed["canh"]) == 5
    dialogue=tao_cau_chuyen(CauHinh(CHU_DE_MAU[4],45))
    turns=[x["hoi_thoai"][0] for x in dialogue["canh"] if x["hoi_thoai"]]
    assert {x["nhan_vat"] for x in turns} == {"A","B"}
    assert len({x["noi_dung"] for x in turns}) == len(turns)
