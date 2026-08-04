export type EasingName = 'linear' | 'ease-in' | 'ease-out' | 'ease-in-out' | 'spring';
export type CameraMovement = 'none' | 'zoom-in' | 'zoom-out' | 'dolly' | 'push' | 'pull' | 'pan-left' | 'pan-right' | 'tilt-up' | 'tilt-down' | 'orbit' | 'handheld' | 'parallax';
export type TransitionName = 'fade' | 'flash' | 'blur' | 'whip' | 'slide' | 'mask' | 'morph' | 'glitch' | 'scale' | 'camera-cut';
export type Gesture = 'idle' | 'walk' | 'run' | 'wave' | 'point-left' | 'point-right' | 'think' | 'laugh' | 'cry' | 'surprised' | 'angry' | 'cross-arms' | 'hands-up' | 'sit' | 'stand' | 'use-phone' | 'use-laptop';
export type Emotion = 'neutral' | 'happy' | 'sad' | 'angry' | 'confused' | 'thinking' | 'excited' | 'scared' | 'serious' | 'smile';
export type MotionLevel = 'light' | 'medium' | 'high' | 'viral';

export interface MotionConfig {speed?: number; easing?: EasingName; strength?: number; duration?: number}
export interface CameraConfig extends MotionConfig {type: CameraMovement; zoom?: number}
export interface TransitionConfig extends MotionConfig {type: TransitionName; direction?: 'left'|'right'|'up'|'down'; color?: string}
export interface SubtitleConfig {animation?: 'pop'|'fade'|'slide'|'word'|'karaoke'; color?: string; background?: string; size?: number}
export interface Character {name: string; position: 'left'|'right'|'center'; action?: string; gesture?: Gesture; emotion: Emotion; color?: string}
export interface Scene {id:number; duration:number; narration:string; background:string; camera:string|CameraConfig; transition:string|TransitionConfig; emotion?:Emotion; gesture?:Gesture; zoom?:number; subtitleAnimation?:SubtitleConfig['animation']; subtitle?:SubtitleConfig; keywords:string[]; characters:Character[]; seed?:number;phong_cach_minh_hoa?:'phac_thao_but_chi';mo_ta_hinh_anh?:string;bo_cuc_phac_thao?:any;mau_nhan?:string;muc_do_chi_tiet?:'thap'|'trung_binh'|'cao'}
export interface Story extends Record<string,unknown> {title:string; duration:number; style:string; motionLevel?:MotionLevel; audio?:string; scenes:Scene[]}
