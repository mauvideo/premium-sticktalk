import {Scene,Story} from '../../engine/types';
export type CameraPreset='push-in'|'pan-left'|'pan-right'|'floating'|'parallax'|'rotate';
export type PaperTransitionPreset='paper-slide'|'paper-reveal'|'card-stack'|'mask-wipe'|'hard-cut';
export type VisualPlan={background?:string;mainCharacter?:string;secondaryObjects?:string[];icons?:string[];paperElements?:string[];camera?:CameraPreset;transition?:PaperTransitionPreset;highlight?:string;mood?:string;composition?:string};
export type VoxSceneProps={scene:Scene;story:Story;sceneIndex:number};
