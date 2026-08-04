import {SketchVariant} from './types';
export const PHAC_THAO_STYLE_MAP:Record<SketchVariant,{ten:string;paper:string;ink:string;accent:string;speed:number}>={
 phac_thao_dien_anh_tram:{ten:'Phác thảo điện ảnh — Trầm',paper:'#d8cbb5',ink:'#352c26',accent:'#9b533f',speed:.72},
 phac_thao_sach_ky_nang:{ten:'Phác thảo điện ảnh — Sách kỹ năng',paper:'#f4ead2',ink:'#3d352c',accent:'#c56a3d',speed:.9},
 phac_thao_doanh_nhan:{ten:'Phác thảo điện ảnh — Doanh nhân',paper:'#e9dfca',ink:'#302d29',accent:'#526b72',speed:.82},
};
export const isSketchStyle=(style:string):style is SketchVariant=>style in PHAC_THAO_STYLE_MAP;
