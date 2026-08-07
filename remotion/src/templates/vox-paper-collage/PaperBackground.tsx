import React from 'react';
import {AbsoluteFill} from 'remotion';
import {noise} from './shared';

export const PaperBackground:React.FC<{index:number;background:string}>=({index,background})=>{
  const angle=index%2?88:2;
  return <AbsoluteFill data-layer="paper-background" style={{
    background:'#d8c7a2',
    backgroundImage:[
      `url(${noise})`,
      'radial-gradient(circle at 18% 22%, rgba(104,70,37,.18), transparent 28%)',
      'radial-gradient(circle at 82% 74%, rgba(89,58,32,.16), transparent 30%)',
      'linear-gradient(180deg, rgba(255,247,218,.50), rgba(169,135,87,.16))',
      `repeating-linear-gradient(${angle}deg, rgba(72,54,32,.035) 0 1px, transparent 1px 30px)`
    ].join(','),
    backgroundBlendMode:'multiply,normal,normal,normal,normal',
    color:'#211a12'
  }}>
    <div style={{position:'absolute',inset:0,boxShadow:'inset 0 0 150px rgba(72,42,20,.28)',pointerEvents:'none'}}/>
    <div style={{position:'absolute',inset:28,border:'2px solid rgba(70,45,25,.18)',pointerEvents:'none'}}/>
    <div style={{position:'absolute',left:50,top:35,font:'700 17px Georgia,serif',letterSpacing:4,opacity:.20,textTransform:'uppercase'}}>{background}</div>
  </AbsoluteFill>;
};
