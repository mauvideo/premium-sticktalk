import React from 'react';
import {spring,useCurrentFrame,useVideoConfig} from 'remotion';
import {MarkerHighlight} from './MarkerHighlight';
export const EditorialTitle:React.FC<{title:string;highlight:string;index:number}>=({title,highlight,index})=>{
  const f=useCurrentFrame(),{fps,width,height}=useVideoConfig(),s=spring({frame:f,fps,config:{damping:15}}),words=title.split(' '),landscape=width>height;
  return <div data-layer="editorial-title" style={{
    position:'absolute',left:landscape?85:60,right:landscape?760:60,top:landscape?90:(index%3===2?90:120),zIndex:10,
    fontFamily:'Georgia, Times New Roman, serif',fontSize:landscape?82:(index%3===1?88:98),lineHeight:.91,fontWeight:900,
    textTransform:'uppercase',letterSpacing:landscape?-4:-5,transform:`translateY(${(1-s)*-100}px) rotate(${index%2?-1:1}deg)`
  }}>{words.map((w,i)=><React.Fragment key={i}>{i===words.length-1||highlight.toLowerCase().includes(w.toLowerCase())?<MarkerHighlight text={w}/>:w}{' '}</React.Fragment>)}</div>
};
