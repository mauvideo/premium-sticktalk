import React from 'react';
import {interpolate, useCurrentFrame} from 'remotion';
import {C, tear} from './shared';

/** One compact context clipping in a reserved zone so it never stacks over icons. */
export const ContextEvidence: React.FC<{labels: string[]; index: number; travel: number}> = ({labels, index, travel}) => {
  const frame = useCurrentFrame();
  const reveal = interpolate(frame, [12, 28], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});
  const label = labels[0];
  if (!label) return null;
  return <div data-layer="context-evidence" style={{position:'absolute',top:1215,right:62,width:330,opacity:reveal,transform:`translateX(${travel * -0.18}px) rotate(2deg)`,zIndex:8}}>
    <div style={{minHeight:118,padding:'20px 22px',background:index%2 ? C.red : C.yellow,color:index%2 ? C.paper : C.ink,clipPath:tear(index+21),boxShadow:'12px 15px 0 rgba(23,23,17,.9)'}}>
      <div style={{font:'900 16px Arial',letterSpacing:2,marginBottom:8}}>TƯ LIỆU 01</div>
      <div style={{font:'900 25px Arial',lineHeight:1.08,textTransform:'uppercase'}}>{label}</div>
      <div style={{height:5,background:index%2 ? C.yellow : C.ink,marginTop:14,width:'72%'}}/>
    </div>
  </div>;
};
