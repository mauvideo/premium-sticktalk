import React from 'react';
import {AbsoluteFill, Audio, Sequence, interpolate, spring, staticFile, useCurrentFrame, useVideoConfig} from 'remotion';

export type Character = {name: string; position: 'left'|'right'|'center'; action: string; emotion: string};
export type Scene = {id: number; duration: number; narration: string; background: string; camera: string; transition: string; keywords: string[]; characters: Character[]};
export type Story = {title: string; duration: number; style: string; audio?: string; scenes: Scene[]};

const Stick: React.FC<{character: Character; accent: string}> = ({character, accent}) => {
  const frame = useCurrentFrame();
  const bob = Math.sin(frame / 5) * (character.action === 'walk' ? 18 : 5);
  const nod = character.action === 'nod' ? Math.sin(frame / 3) * 8 : 0;
  const point = character.action === 'point';
  const x = character.position === 'left' ? 280 : character.position === 'right' ? 800 : 540;
  const mouth = character.emotion === 'happy' ? 'M-18 18 Q0 34 18 18' : character.emotion === 'sad' ? 'M-18 28 Q0 10 18 28' : 'M-16 22 L16 22';
  return <svg width="360" height="620" viewBox="0 0 360 620" style={{position:'absolute',left:x-180,top:560+bob,overflow:'visible'}}>
    <g transform={`rotate(${nod} 180 120)`} stroke={accent} strokeWidth="18" strokeLinecap="round" fill="none">
      <circle cx="180" cy="105" r="70" fill="#0c1020"/>
      <line x1="180" y1="175" x2="180" y2="390"/>
      <line x1="180" y1="230" x2={point ? 330 : 80} y2={point ? 190 : 320}/>
      <line x1="180" y1="230" x2="280" y2="320"/>
      <line x1="180" y1="390" x2="90" y2="570"/>
      <line x1="180" y1="390" x2="270" y2="570"/>
      <circle cx="155" cy="92" r="7" fill={accent} stroke="none"/><circle cx="205" cy="92" r="7" fill={accent} stroke="none"/>
      <path d={mouth}/>
    </g>
  </svg>;
};

const Caption: React.FC<{text: string; keywords: string[]; accent: string}> = ({text, keywords, accent}) => {
  const frame = useCurrentFrame();
  const pop = spring({frame,fps:30,config:{damping:14}});
  const words=text.split(/\s+/);
  return <div style={{position:'absolute',left:70,right:70,bottom:120,textAlign:'center',fontFamily:'Arial, sans-serif',fontWeight:900,fontSize:62,lineHeight:1.2,textTransform:'uppercase',transform:`scale(${0.9+0.1*pop})`,textShadow:'0 6px 18px #000'}}>
    {words.map((w,i)=> <span key={i} style={{display:'inline-block',margin:'0 8px',padding:keywords.some(k=>w.toLowerCase().includes(k.toLowerCase()))?'4px 12px':0,background:keywords.some(k=>w.toLowerCase().includes(k.toLowerCase()))?accent:'transparent',borderRadius:10}}>{w}</span>)}
  </div>;
};

const SceneView: React.FC<{scene: Scene; style: string}> = ({scene,style}) => {
  const frame=useCurrentFrame(); const {fps}=useVideoConfig();
  const accent=style==='whiteboard'?'#111111':style==='motivational'?'#ff8a00':'#42f5e9';
  const bg=style==='whiteboard'?'#f6f3ea':style==='motivational'?'linear-gradient(160deg,#ffecd2,#fcb69f)':'radial-gradient(circle at 50% 30%,#192044,#050711 70%)';
  const enter=spring({frame,fps,config:{damping:16}});
  const zoom=interpolate(frame,[0,scene.duration*fps],[1.06,1.0],{extrapolateRight:'clamp'});
  return <AbsoluteFill style={{background:bg,color:style==='whiteboard'?'#111':'white',overflow:'hidden',transform:`scale(${zoom})`,opacity:enter}}>
    <div style={{position:'absolute',top:120,left:70,right:70,fontFamily:'Arial',fontWeight:900,fontSize:66,lineHeight:1.05,textAlign:'center'}}>{scene.id===1?'ĐỪNG CỐ THẮNG MỌI CUỘC TRANH LUẬN':''}</div>
    {scene.characters.map((c,i)=><Stick key={i} character={c} accent={accent}/>)}
    <Caption text={scene.narration} keywords={scene.keywords} accent={accent}/>
  </AbsoluteFill>;
};

export const StickTalkVideo: React.FC<Story> = (story) => {
  let start=0;
  return <AbsoluteFill style={{background:'#050711'}}>
    {story.audio ? <Audio src={staticFile(story.audio)}/> : null}
    {story.scenes.map(scene=>{const from=Math.round(start*30); const dur=Math.max(1,Math.round(scene.duration*30)); start+=scene.duration; return <Sequence key={scene.id} from={from} durationInFrames={dur}><SceneView scene={scene} style={story.style}/></Sequence>;})}
  </AbsoluteFill>;
};
