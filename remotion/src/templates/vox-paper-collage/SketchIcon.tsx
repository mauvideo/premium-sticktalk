import React from 'react';
import {interpolate,useCurrentFrame} from 'remotion';

const pathFor=(kind:string)=>{
  const k=kind.toLowerCase();
  if(k.includes('map')) return 'M28 35l30-12 32 12 32-12v88l-32 12-32-12-30 12zM58 23v88M90 35v88';
  if(k.includes('timeline')) return 'M22 75h106M38 75v-28M75 75v34M112 75v-22M30 47h16M67 109h16M104 53h16';
  if(k.includes('document')) return 'M40 20h55l20 20v90H40zM95 20v22h20M55 62h45M55 82h45M55 102h32';
  if(k.includes('military')) return 'M75 20l16 31 35 5-25 24 6 35-32-17-32 17 6-35-25-24 35-5z';
  if(k.includes('factory')) return 'M24 126V65l28 16V60l28 18V42l44 22v62zM42 103h14M68 103h14M94 103h14';
  if(k.includes('car')) return 'M28 94l12-31h68l14 31v20H28zM45 114a10 10 0 1 0 0 .1M105 114a10 10 0 1 0 0 .1M49 63l10-18h34l10 18';
  if(k.includes('ship')) return 'M24 91h102l-18 28H45zM50 91V52h45v39M62 52V30h22v22M31 127c18 8 31-8 44 0 14 8 27-8 44 0';
  if(k.includes('airplane')) return 'M20 82l48-13 18-43 13 3-5 39 34 9v10l-35 4-14 34-11-3 3-31-51 2z';
  if(k.includes('book')) return 'M24 35c18-8 35-4 51 7v82c-16-11-33-15-51-7zM126 35c-18-8-35-4-51 7v82c16-11 33-15 51-7z';
  if(k.includes('chart')) return 'M25 124V28M25 124h105M38 103l24-29 22 13 32-45M110 42h15v15';
  if(k.includes('building')) return 'M35 126V42h80v84M55 60h12M83 60h12M55 82h12M83 82h12M69 126v-22h12';
  if(k.includes('person')) return 'M75 24a22 22 0 1 0 0 44 22 22 0 0 0 0-44M35 126c5-35 24-50 40-50s35 15 40 50';
  return 'M42 82l20 20 48-57';
};

export const SketchIcon:React.FC<{kind:string;index:number;style?:React.CSSProperties}>=({kind,index,style})=>{
  const f=useCurrentFrame();
  const draw=interpolate(f,[8+index*3,30+index*3],[0,1],{extrapolateLeft:'clamp',extrapolateRight:'clamp'});
  return <div data-layer="semantic-sketch-icon" style={{position:'absolute',...style}}>
    <div style={{background:'#fffdf5',padding:10,border:'4px solid #171711',boxShadow:'8px 9px 0 #f4c900',transform:`rotate(${index%2?-4:3}deg)`}}>
      <svg width="150" height="150" viewBox="0 0 150 150" style={{overflow:'visible'}}>
        <path d={pathFor(kind)} fill="none" stroke="#171711" strokeWidth="7" strokeLinecap="round" strokeLinejoin="round" strokeDasharray="900" strokeDashoffset={900*(1-draw)}/>
      </svg>
    </div>
    <span style={{display:'block',font:'900 17px Arial',textAlign:'center',marginTop:10,textTransform:'uppercase',maxWidth:170}}>{kind}</span>
  </div>;
};
