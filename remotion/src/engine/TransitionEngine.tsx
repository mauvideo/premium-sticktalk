import React from 'react';
import {interpolate,useCurrentFrame,useVideoConfig} from 'remotion';
import {TransitionConfig,TransitionName} from './types';
const aliases:Record<string,TransitionName>={zoom:'scale',cut:'camera-cut'};
export const normalizeTransition=(v:string|TransitionConfig):TransitionConfig=>typeof v==='string'?{type:aliases[v]??v as TransitionName}:{...v,type:aliases[v.type]??v.type};
export const TransitionEngine:React.FC<{config:string|TransitionConfig;children:React.ReactNode}>=({config,children})=>{
 const frame=useCurrentFrame(),{fps}=useVideoConfig(),c=normalizeTransition(config),duration=Math.max(1,(c.duration??.45)*fps),strength=c.strength??1,p=interpolate(frame,[0,duration],[0,1],{extrapolateRight:'clamp'});
 let opacity=1,filter='',transform='',clipPath:string|undefined;
 if(c.type==='fade')opacity=p; if(c.type==='flash'){filter=`brightness(${1+(1-p)*3*strength})`;opacity=Math.min(1,p*3)}
 if(c.type==='blur')filter=`blur(${(1-p)*24*strength}px)`;
 if(c.type==='whip')transform=`translateX(${(1-p)*(c.direction==='right'?-1:1)*1080*strength}px) skewX(${(1-p)*-12}deg)`;
 if(c.type==='slide')transform=`translate${c.direction==='up'||c.direction==='down'?'Y':'X'}(${(1-p)*(c.direction==='right'||c.direction==='down'?-1:1)*100}%)`;
 if(c.type==='mask')clipPath=`circle(${p*80}% at 50% 50%)`; if(c.type==='morph')transform=`scale(${.75+.25*p}) rotate(${(1-p)*3}deg)`;
 if(c.type==='glitch'){transform=`translate(${Math.sin(frame*9)*(1-p)*18*strength}px,${Math.cos(frame*7)*(1-p)*8}px)`;filter=`hue-rotate(${(1-p)*120}deg)`}
 if(c.type==='scale')transform=`scale(${.65+.35*p})`; // camera-cut and unknown legacy names intentionally render immediately.
 return <div style={{position:'absolute',inset:0,opacity,filter,transform,clipPath,overflow:'hidden'}}>{children}</div>;
};
