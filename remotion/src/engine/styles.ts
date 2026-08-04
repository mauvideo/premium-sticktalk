import {CameraConfig,SubtitleConfig,TransitionConfig} from './types';
export interface StylePreset{camera:CameraConfig;subtitle:SubtitleConfig;colors:{background:string;foreground:string;accent:string};background:string;transition:TransitionConfig;animation:string}
export const STYLE_PRESETS:Record<string,StylePreset>={
 philosophy:{camera:{type:'pull',strength:.65,easing:'ease-in-out'},subtitle:{animation:'fade',size:58},colors:{background:'#070b18',foreground:'#f8fafc',accent:'#d6ad60'},background:'radial-gradient(circle at 50% 25%,#1e293b,#050711 72%)',transition:{type:'fade',duration:.7},animation:'contemplative'},
 news:{camera:{type:'push',strength:.55},subtitle:{animation:'slide',size:54,background:'#c1121f'},colors:{background:'#08111e',foreground:'#fff',accent:'#ef233c'},background:'linear-gradient(145deg,#14213d,#030712)',transition:{type:'camera-cut'},animation:'precise'},
 tiktok:{camera:{type:'handheld',strength:.75},subtitle:{animation:'pop',size:64},colors:{background:'#070312',foreground:'#fff',accent:'#00f5d4'},background:'radial-gradient(circle at 25% 20%,#301064,#070312 65%)',transition:{type:'whip',duration:.3},animation:'energetic'},
 entrepreneur:{camera:{type:'dolly',strength:.55},subtitle:{animation:'word',size:57},colors:{background:'#11100d',foreground:'#fff',accent:'#e9c46a'},background:'linear-gradient(155deg,#25231d,#080807)',transition:{type:'scale',duration:.45},animation:'confident'},
 storytelling:{camera:{type:'parallax',strength:.6},subtitle:{animation:'karaoke',size:58},colors:{background:'#171026',foreground:'#fff',accent:'#f4a261'},background:'linear-gradient(160deg,#312044,#10101a)',transition:{type:'mask',duration:.65},animation:'cinematic'},
};
const aliases:Record<string,string>={dark_neon:'tiktok',whiteboard:'philosophy',motivational:'entrepreneur','triết_lý':'philosophy','tin_tức':'news','kể_chuyện':'storytelling','người_que_triết_lý':'philosophy','người_que_tiktok':'tiktok','người_que_doanh_nhân':'entrepreneur','người_que_kể_chuyện':'storytelling','tin_tức_ai':'news'};
export const getStylePreset=(name:string)=>STYLE_PRESETS[aliases[name]??name]??STYLE_PRESETS.philosophy;
