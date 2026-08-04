import React from 'react';
import {AbsoluteFill,Audio,Sequence,interpolate,spring,staticFile,useCurrentFrame,useVideoConfig} from 'remotion';
import {CameraEngine} from './engine/CameraEngine';
import {Stickman} from './engine/Stickman';
import {TransitionEngine} from './engine/TransitionEngine';
import {getStylePreset} from './engine/styles';
import {Scene,Story} from './engine/types';
export type {Character,Scene,Story} from './engine/types';

const Caption:React.FC<{scene:Scene;accent:string;foreground:string}>=({scene,accent,foreground})=>{const frame=useCurrentFrame(),{fps}=useVideoConfig(),cfg=scene.subtitle??{},animation=scene.subtitleAnimation??cfg.animation??'pop',progress=spring({frame,fps,config:{damping:14}}),words=scene.narration.split(/\s+/);let transform='',opacity=1;if(animation==='pop')transform=`scale(${.88+.12*progress})`;if(animation==='slide')transform=`translateY(${(1-progress)*70}px)`;if(animation==='fade')opacity=interpolate(frame,[0,fps*.4],[0,1],{extrapolateRight:'clamp'});
 return <div style={{position:'absolute',left:65,right:65,bottom:115,textAlign:'center',fontFamily:'Arial,sans-serif',fontWeight:900,fontSize:cfg.size??60,lineHeight:1.2,textTransform:'uppercase',transform,opacity,color:cfg.color??foreground,textShadow:'0 6px 18px #000'}}>{words.map((word,i)=>{const keyword=scene.keywords.some(k=>word.toLowerCase().includes(k.toLowerCase())),revealed=animation!=='word'&&animation!=='karaoke'||frame>i*3;return <span key={`${word}-${i}`} style={{display:'inline-block',margin:'0 7px',padding:keyword?'4px 10px':0,background:keyword?(cfg.background??accent):'transparent',borderRadius:9,opacity:revealed?1:.18,transform:animation==='karaoke'&&frame>=i*3&&frame<(i+1)*3?'scale(1.12)':'none'}}>{word}</span>})}</div>};

const SceneView:React.FC<{scene:Scene;style:string}>=({scene,style})=>{const preset=getStylePreset(style),{fps}=useVideoConfig(),frames=Math.max(1,Math.round(scene.duration*fps)),camera=scene.camera||{...preset.camera,zoom:scene.zoom},transition=scene.transition||preset.transition;return <TransitionEngine config={transition}><CameraEngine config={camera} durationInFrames={frames} seed={scene.seed??scene.id}><AbsoluteFill style={{background:scene.background&&scene.background!=='dark'?scene.background:preset.background,color:preset.colors.foreground,overflow:'hidden'}}>
 <div style={{position:'absolute',inset:0,background:'linear-gradient(120deg,transparent 45%,rgba(255,255,255,.035) 50%,transparent 55%)'}}/>
 {scene.characters.map((character,i)=><Stickman key={`${character.name}-${i}`} character={{...character,gesture:character.gesture??scene.gesture,emotion:character.emotion??scene.emotion??'neutral'}} accent={preset.colors.accent}/>)}
 <Caption scene={{...scene,subtitle:{...preset.subtitle,...scene.subtitle}}} accent={preset.colors.accent} foreground={preset.colors.foreground}/>
 </AbsoluteFill></CameraEngine></TransitionEngine>};

export const StickTalkVideo:React.FC<Story>=(story)=>{let start=0;return <AbsoluteFill style={{background:'#050711'}}>{story.audio&&<Audio src={staticFile(story.audio)}/>} {story.scenes.map(scene=>{const from=Math.round(start*30),durationInFrames=Math.max(1,Math.round(scene.duration*30));start+=scene.duration;return <Sequence key={scene.id} from={from} durationInFrames={durationInFrames}><SceneView scene={scene} style={story.style}/></Sequence>})}</AbsoluteFill>};
