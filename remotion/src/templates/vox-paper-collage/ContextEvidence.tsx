import React from 'react';
import {interpolate, useCurrentFrame} from 'remotion';
import {C, tear} from './shared';

/** Editorial evidence clippings derived from the scene plan, not random icons. */
export const ContextEvidence: React.FC<{labels: string[]; index: number; travel: number}> = ({labels, index, travel}) => {
  const frame = useCurrentFrame();
  const reveal = interpolate(frame, [12, 28], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});
  return <div data-layer="context-evidence" style={{position:'absolute',top:790,left:index%2 ? 610 : 55,width:370,display:'grid',gap:22,opacity:reveal,transform:`translateX(${travel * -0.35}px)`}}>
    {labels.slice(0,2).map((label, i)=><div key={`${label}-${i}`} style={{minHeight:105,padding:'22px 24px',background:i ? C.red : C.yellow,color:i ? C.paper : C.ink,clipPath:tear(index+i+21),boxShadow:'12px 15px 0 rgba(23,23,17,.9)',transform:`rotate(${i ? 3 : -4}deg)`}}>
      <div style={{font:'900 17px Arial',letterSpacing:2,marginBottom:8}}>TƯ LIỆU {String(i+1).padStart(2,'0')}</div>
      <div style={{font:'900 27px Arial',lineHeight:1.05,textTransform:'uppercase'}}>{label}</div>
      <div style={{height:5,background:i ? C.yellow : C.ink,marginTop:15,width:`${65+i*20}%`}}/>
    </div>)}
  </div>;
};
