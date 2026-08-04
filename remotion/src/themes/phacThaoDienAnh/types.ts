import {Scene} from '../../engine/types';
export type SketchVariant='phac_thao_dien_anh_tram'|'phac_thao_sach_ky_nang'|'phac_thao_doanh_nhan';
export type SketchLayout='tieu_de'|'laptop'|'bang'|'doi_thoai'|'suy_nghi'|'trich_dan'|'so_lieu'|'truoc_sau'|'cac_buoc'|'ket_luan';
export type SketchTransitionType='lat_trang'|'giay_truot'|'pencil_wipe'|'fade_giay'|'mo_chi'|'zoom_minh_hoa'|'net_but'|'bong_giay';
export interface SketchScene extends Scene {phong_cach_minh_hoa?:'phac_thao_but_chi';mo_ta_hinh_anh?:string;bo_cuc_phac_thao?:SketchLayout;mau_nhan?:string;muc_do_chi_tiet?:'thap'|'trung_binh'|'cao'}
