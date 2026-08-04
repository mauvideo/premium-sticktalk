import React from 'react';
import {Easing, interpolate, useCurrentFrame, useVideoConfig} from 'remotion';
import {CameraConfig, CameraMovement, EasingName} from './types';

const aliases: Record<string, CameraMovement> = {zoom_in:'zoom-in',zoom_out:'zoom-out',punch_in:'push',pan_left:'pan-left',pan_right:'pan-right'};
const ease = (name:EasingName='ease-in-out') => name==='linear'?Easing.linear:name==='ease-in'?Easing.in(Easing.cubic):name==='ease-out'?Easing.out(Easing.cubic):Easing.inOut(Easing.cubic);
export const normalizeCamera=(value:string|CameraConfig):CameraConfig => typeof value==='string'?{type:aliases[value]??value as CameraMovement}:{...value,type:aliases[value.type]??value.type};

export const CameraEngine:React.FC<{config:string|CameraConfig; durationInFrames:number; seed?:number; children:React.ReactNode}>=({config,durationInFrames,seed=1,children})=>{
 const frame=useCurrentFrame(); const {fps}=useVideoConfig(); const c=normalizeCamera(config);
 const strength=c.strength??1, speed=c.speed??1, active=Math.min(durationInFrames,Math.max(1,(c.duration??durationInFrames/fps)*fps));
 const p=interpolate(Math.min(frame*speed,active),[0,active],[0,1],{easing:ease(c.easing),extrapolateRight:'clamp'});
 let x=0,y=0,scale=1,rotate=0; const amount=55*strength;
 switch(c.type){
  case 'zoom-in': case 'push': scale=1+(c.zoom??.12)*strength*p; break;
  case 'zoom-out': case 'pull': scale=1+(c.zoom??.12)*strength*(1-p); break;
  case 'dolly': x=-amount/2+amount*p; scale=1+.05*p; break;
  case 'pan-left': x=amount*p; break; case 'pan-right':x=-amount*p;break;
  case 'tilt-up':y=amount*p;break; case 'tilt-down':y=-amount*p;break;
  case 'orbit':x=Math.sin(p*Math.PI*2)*amount;rotate=Math.sin(p*Math.PI*2)*2*strength;break;
  case 'handheld':x=Math.sin((frame+seed)*1.7)*4*strength;y=Math.cos((frame+seed)*1.31)*3*strength;rotate=Math.sin(frame*.83)*.35*strength;break;
  case 'parallax':x=-amount*p;scale=1+.04*p;break;
 }
 return <div style={{position:'absolute',inset:-80,transform:`translate3d(${x}px,${y}px,0) scale(${scale}) rotate(${rotate}deg)`,transformOrigin:'center'}}>{children}</div>;
};
