import React from 'react';
import {interpolate,useCurrentFrame,useVideoConfig} from 'remotion';
import {C,noise,tear} from './shared';
import {PaperTransitionPreset} from './types';

export const PaperTransition:React.FC<{preset:PaperTransitionPreset;index:number}>=({preset,index})=>{
  const f=useCurrentFrame();
  const {durationInFrames:d}=useVideoConfig();
  if(preset==='hard-cut')return null;

  // Trước đây transition phủ toàn màn hình ở cuối scene, tạo các frame trắng/đen
  // rất gắt khi ghép scene. Giờ chỉ dùng một dải giấy nhỏ ở mép để giữ chất Vox
  // nhưng tuyệt đối không che full-frame.
  const enter=interpolate(f,[0,10],[0,1],{extrapolateLeft:'clamp',extrapolateRight:'clamp'});
  const exit=interpolate(f,[Math.max(0,d-10),d],[0,1],{extrapolateLeft:'clamp',extrapolateRight:'clamp'});
  const active=Math.max(1-enter,exit);
  if(active<=0.001)return null;
  const fromLeft=index%2===0;
  const width=interpolate(active,[0,1],[0,92],{extrapolateLeft:'clamp',extrapolateRight:'clamp'});
  return <div data-layer="paper-transition-edge" style={{
    position:'absolute',top:-20,bottom:-20,[fromLeft?'left':'right']:-10,width,
    pointerEvents:'none',zIndex:50,background:C.paper,backgroundImage:`url(${noise})`,
    clipPath:tear(index+70),opacity:Math.min(.55,active*.55),
    boxShadow:fromLeft?'8px 0 0 rgba(23,23,17,.08)':'-8px 0 0 rgba(23,23,17,.08)'
  }}/>
};
