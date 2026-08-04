import React from 'react';
import {useCurrentFrame} from 'remotion';
import {Character,Emotion,Gesture} from './types';

type Pose={body?:number;head?:number;la?:number;ra?:number;lf?:number;rf?:number;ll?:number;rl?:number;y?:number};
const legacy:Record<string,Gesture>={point:'point-right',nod:'idle',shake:'angry'};
const pose=(gesture:Gesture,frame:number):Pose=>{const wave=Math.sin(frame*.5),step=Math.sin(frame*.35);switch(gesture){
 case'walk':return{ll:25*step,rl:-25*step,la:-18*step,ra:18*step,y:Math.abs(step)*-5};case'run':return{ll:42*step,rl:-42*step,la:-35*step,ra:35*step,y:Math.abs(step)*-12};
 case'wave':return{ra:-125,rf:35*wave};case'point-left':return{la:75,lf:0};case'point-right':return{ra:-75,rf:0};case'think':return{ra:-55,rf:-65,head:Math.sin(frame*.08)*5};
 case'laugh':return{la:25,ra:-25,body:Math.sin(frame*.5)*4,y:Math.sin(frame*.5)*-5};case'cry':return{head:12,la:-10,ra:10};case'surprised':case'hands-up':return{la:145,ra:-145,lf:15,rf:-15};
 case'angry':return{la:-55,ra:55,head:Math.sin(frame*.7)*2};case'cross-arms':return{la:-45,ra:45,lf:90,rf:-90};case'sit':return{body:5,ll:-70,rl:70,y:85};
 case'use-phone':return{la:-35,ra:35,lf:75,rf:-75,head:8};case'use-laptop':return{la:-55,ra:55,lf:45,rf:-45,head:10};default:return{body:Math.sin(frame*.08)*1.5,y:Math.sin(frame*.08)*-3};}};
const face=(emotion:Emotion)=>({
 mouth:emotion==='happy'||emotion==='smile'||emotion==='excited'?'M-18 18 Q0 35 18 18':emotion==='sad'||emotion==='scared'?'M-18 30 Q0 12 18 30':emotion==='confused'?'M-15 20 Q0 30 15 20':emotion==='angry'?'M-15 28 L15 20':'M-15 23 L15 23',
 brows:emotion==='angry'?['M-28 68 L-8 76','M8 76 L28 68']:emotion==='sad'?['M-28 74 L-8 68','M8 68 L28 74']:emotion==='confused'?['M-28 68 L-8 73','M8 74 L28 66']:['M-28 68 L-8 68','M8 68 L28 68']});
export const Stickman:React.FC<{character:Character;accent:string}>=({character,accent})=>{const frame=useCurrentFrame(),gesture=character.gesture??legacy[character.action??'']??character.action as Gesture??'idle',p=pose(gesture,frame),f=face(character.emotion??'neutral'),x=character.position==='left'?280:character.position==='right'?800:540,stroke=character.color??accent,blink=frame%95>89?.8:6,expression=Math.sin(frame*.12);
 const limb=(name:string,x1:number,y1:number,len:number,angle:number,child?:{name:string;len:number;angle:number})=><g data-part={name} transform={`translate(${x1} ${y1}) rotate(${angle})`}><line x2="0" y2={len}/>{child&&<g data-part={child.name} transform={`translate(0 ${len}) rotate(${child.angle})`}><line y2={child.len}/>{child.name.includes('leg')&&<line data-part="feet" y1={child.len} y2={child.len} x2="28"/>}</g>}</g>;
 return <svg width="360" height="620" viewBox="0 0 360 620" style={{position:'absolute',left:x-180,top:520+(p.y??0),overflow:'visible'}}><g transform={`rotate(${p.body??0} 180 270)`} stroke={stroke} strokeWidth="18" strokeLinecap="round" fill="none">
  <g data-part="head" transform={`rotate(${p.head??0} 180 105)`}><circle cx="180" cy="105" r="70" fill="#0c1020"/><g transform="translate(180 20)" strokeWidth="8"><ellipse data-part="eyes" cx="-24" cy="78" rx="6" ry={blink} fill={stroke}/><ellipse data-part="eyes" cx="24" cy="78" rx="6" ry={blink} fill={stroke}/><g data-part="eyebrows" transform={`translate(0 ${expression}px)`}><path d={f.brows[0]}/><path d={f.brows[1]}/></g><path data-part="mouth" d={f.mouth} transform={`translate(0 23) scale(1 ${1+expression*.04}) translate(0 -23)`}/></g></g>
  <line data-part="body" x1="180" y1="175" x2="180" y2="390"/>{limb('left-arm',180,225,105,p.la??35,{name:'left-forearm',len:105,angle:p.lf??0})}{limb('right-arm',180,225,105,p.ra??-35,{name:'right-forearm',len:105,angle:p.rf??0})}{limb('left-leg',180,390,115,p.ll??25,{name:'left-lower-leg',len:90,angle:0})}{limb('right-leg',180,390,115,p.rl??-25,{name:'right-lower-leg',len:90,angle:0})}
 </g></svg>};
