import React from 'react';
import {interpolate,useCurrentFrame,useVideoConfig} from 'remotion';
import {C,noise,tear} from './shared';
import {PaperTransitionPreset} from './types';

export const PaperTransition:React.FC<{preset:PaperTransitionPreset;index:number}>=({preset,index})=>{
  const f=useCurrentFrame();
  const {durationInFrames:d}=useVideoConfig();
  if(preset==='hard-cut')return null;
  const edgeFrames=Math.max(6,Math.min(12,Math.round(d*.08)));
  const enter=interpolate(f,[0,edgeFrames],[1,0],{extrapolateLeft:'clamp',extrapolateRight:'clamp'});
  const exit=interpolate(f,[Math.max(0,d-edgeFrames),d],[0,1],{extrapolateLeft:'clamp',extrapolateRight:'clamp'});
  const active=Math.max(enter,exit);
  if(active<.001)return null;
  const fromLeft=(index+(exit>enter?1:0))%2===0;
  const maxWidth=preset==='card-stack'?150:preset==='mask-wipe'?125:105;
  const width=interpolate(active,[0,1],[0,maxWidth],{extrapolateLeft:'clamp',extrapolateRight:'clamp'});
  const rotate=(fromLeft?-1:1)*interpolate(active,[0,1],[0,1.4]);
  return <div data-layer="paper-transition-edge" style={{
    position:'absolute',top:-35,bottom:-35,[fromLeft?'left':'right']:-24,width,
    pointerEvents:'none',zIndex:50,background:C.paper,backgroundImage:`url(${noise})`,
    clipPath:tear(index+70),opacity:.72,transform:`rotate(${rotate}deg)`,
    boxShadow:fromLeft?'10px 0 18px rgba(23,23,17,.12)':'-10px 0 18px rgba(23,23,17,.12)'
  }}/>
};
