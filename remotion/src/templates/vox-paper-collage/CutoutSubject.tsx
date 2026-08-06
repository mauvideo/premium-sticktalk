import React from 'react';
import {Img,spring,useCurrentFrame,useVideoConfig} from 'remotion';
import {assetUrl,C,tear} from './shared';

export const CutoutSubject:React.FC<{src?:string;label:string;index:number}>=({src,label,index})=>{
  const f=useCurrentFrame();
  const {fps}=useVideoConfig();
  const s=spring({frame:f-7,fps,config:{damping:13,mass:.8}});
  const url=assetUrl(src);
  const rotation=index%2?-3:3;
  return <div data-layer="main-subject" style={{
    position:'absolute',width:650,height:820,left:index%2?55:375,top:index%3===2?380:500,
    transform:`rotate(${rotation}deg) scale(${.75+.25*s})`
  }}>
    <div style={{
      position:'absolute',inset:'22px -22px -22px 22px',background:C.yellow,
      clipPath:tear(index+9),filter:'drop-shadow(18px 20px 0 rgba(23,23,17,.88))'
    }}/>
    <div style={{
      position:'absolute',inset:0,background:'#fffdf4',padding:16,
      clipPath:tear(index+3),boxShadow:'0 0 0 14px #fffdf4'
    }}>
      {url?<Img src={url} style={{
        width:'100%',height:'100%',objectFit:'cover',filter:'grayscale(1) contrast(1.18)',
        clipPath:tear(index)
      }}/>:<div style={{
        height:'100%',display:'grid',placeItems:'center',background:'#d8d3c7',
        font:'900 54px Arial',textAlign:'center',padding:35
      }}>{label}</div>}
      <div style={{
        position:'absolute',inset:7,border:'10px solid #fffdf4',clipPath:tear(index+1),
        pointerEvents:'none'
      }}/>
    </div>
  </div>;
};
