import React from 'react';
import {interpolate,useCurrentFrame,useVideoConfig} from 'remotion';
export const SubtitleBlock:React.FC<{text:string;index:number}>=({text,index})=>{
  const f=useCurrentFrame(),{fps,width,height}=useVideoConfig(),o=interpolate(f,[fps*.3,fps*.7],[0,1],{extrapolateLeft:'clamp',extrapolateRight:'clamp'}),landscape=width>height;
  return <div data-layer="subtitle" style={{
    position:'absolute',zIndex:20,left:landscape?110:(index%2?90:150),right:landscape?110:(index%2?150:90),bottom:landscape?42:105,
    background:'#171711',color:'#fffdf5',padding:landscape?'18px 28px':'24px 30px',font:`800 ${landscape?30:40}px/1.2 Arial, Helvetica, sans-serif`,
    borderLeft:'14px solid #d62b22',opacity:o,transform:`rotate(${index%2?1:-1}deg)`
  }}>{text}</div>
};
