import {Scene,Story} from '../../engine/types';
export type CameraPreset='push-in'|'pan-left'|'pan-right'|'floating'|'parallax'|'rotate';
export type PaperTransitionPreset='paper-slide'|'paper-reveal'|'card-stack'|'mask-wipe'|'hard-cut';
export type DataLayer={type:'map'|'chart'|'timeline'|'evidence';label:string};
export type VisualPlan={background?:string;mainCharacter?:string;secondaryObjects?:string[];icons?:string[];paperElements?:string[];camera?:CameraPreset;transition?:PaperTransitionPreset;highlight?:string;mood?:string;composition?:string;dataLayers?:DataLayer[];location?:string;timePeriod?:string;layerContract?:string[]};
export type VoxSceneProps={scene:Scene;story:Story;sceneIndex:number};
