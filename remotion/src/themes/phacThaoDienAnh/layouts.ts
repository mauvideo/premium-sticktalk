import {SketchLayout,SketchTransitionType} from './types';
export const SKETCH_LAYOUTS:SketchLayout[]=['tieu_de','laptop','bang','doi_thoai','suy_nghi','trich_dan','so_lieu','truoc_sau','cac_buoc','ket_luan'];
export const SKETCH_TRANSITIONS:SketchTransitionType[]=['lat_trang','giay_truot','pencil_wipe','fade_giay','mo_chi','zoom_minh_hoa','net_but','bong_giay'];
export const sceneLayout=(id:number,requested?:SketchLayout)=>requested??SKETCH_LAYOUTS[(id-1)%SKETCH_LAYOUTS.length];
export const sceneTransition=(id:number)=>SKETCH_TRANSITIONS[(id-1)%SKETCH_TRANSITIONS.length];
