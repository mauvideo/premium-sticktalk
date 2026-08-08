import React from 'react';
import {AbsoluteFill,Img,interpolate,spring,useCurrentFrame,useVideoConfig} from 'remotion';
import {PaperBackground} from './PaperBackground';
import {GridOverlay} from './GridOverlay';
import {NewspaperLayer} from './NewspaperLayer';
import {YellowShape} from './YellowShape';
import {CutoutSubject} from './CutoutSubject';
import {SketchIcon} from './SketchIcon';
import {HandDrawnArrow} from './HandDrawnArrow';
import {EditorialTitle} from './EditorialTitle';
import {SubtitleBlock} from './SubtitleBlock';
import {PaperTransition} from './PaperTransition';
import {assetUrl,plan,tear} from './shared';
import {VoxSceneProps} from './types';
import {EvidencePanel} from './EvidencePanel';
import {ContextEvidence} from './ContextEvidence';

const pop=(frame:number,delay:number,fps:number)=>spring({frame:Math.max(0,frame-delay),fps,config:{damping:12,mass:.58,stiffness:155}});
const SupportingPhotos:React.FC<{items:string[];index:number;travel:number;landscape:boolean}>=({items,index,travel,landscape})=>{
 const f=useCurrentFrame(),{fps}=useVideoConfig(); const photos=items.slice(0,2); if(!photos.length)return null;
 return <div style={landscape?{position:'absolute',top:310,left:720,width:320,display:'grid',gridTemplateColumns:'1fr 1fr',gap:18,zIndex:7,transform:`translateX(${travel*.08}px)`}:{position:'absolute',top:405,right:48,width:270,display:'grid',gap:22,zIndex:7,transform:`translateX(${travel*.08}px)`}}>{photos.map((src,i)=>{const s=pop(f,10+i*7,fps);return <div key={`${src}-${i}`} style={{height:landscape?210:180,background:'#fffdf5',padding:9,clipPath:tear(index+i+40),boxShadow:`9px 10px 0 ${i?'#d62b22':'#ffd400'}`,transform:`rotate(${i?2.5:-2.5}deg) scale(${.72+.28*s}) translateY(${(1-s)*18}px)`}}><Img src={assetUrl(src)} style={{width:'100%',height:'100%',objectFit:'cover',filter:'saturate(.82) contrast(1.05)',clipPath:tear(index+i+43)}}/></div>})}</div>;
};

export const VoxScene:React.FC<VoxSceneProps>=({scene,story,sceneIndex})=>{
 const f=useCurrentFrame(); const {durationInFrames:d,width,height,fps}=useVideoConfig(); const landscape=width>height;
 const p=plan(scene.visualPlan,sceneIndex); const all=[scene.image,...(scene.assets||[])].filter(Boolean) as string[];
 const sf=Math.floor(f/2.5)*2.5;
 const travel=interpolate(sf,[0,Math.max(1,d-1)],[-16,16],{extrapolateLeft:'clamp',extrapolateRight:'clamp'});
 const entrance=pop(f,0,fps); const subjectPop=pop(f,3,fps); const graphicPop=pop(f,13,fps);
 const camera=p.camera; const scale=(camera==='push-in'?interpolate(sf,[0,Math.max(1,d-1)],[1.015,1.065],{extrapolateRight:'clamp'}):1.035)*(.985+.015*entrance);
 const tx=camera==='pan-left'?-travel:camera==='pan-right'?travel:camera==='parallax'?travel*.45:Math.sin(sf/30)*5;
 const ty=(1-entrance)*(sceneIndex%2===0?18:-18); const rot=camera==='rotate'?interpolate(sf,[0,Math.max(1,d-1)],[-.65,.65],{extrapolateRight:'clamp'}):Math.sin(sf/50)*.18;
 const title=scene.headline||String(story.title||scene.keywords?.join(' ')||'');
 const iconSlots=landscape?[{left:90,top:690,rotate:-5},{left:500,top:690,rotate:2},{left:910,top:690,rotate:6}]:[{left:55,top:1110,rotate:-5},{left:405,top:1180,rotate:2},{left:755,top:1110,rotate:6}]; const icons=p.icons.slice(0,3);
 return <AbsoluteFill style={{overflow:'hidden',background:'#d8c7a2'}}>
  <div style={{position:'absolute',inset:landscape?-24:-45,transform:`translate3d(${tx}px,${ty}px,0) scale(${scale}) rotate(${rot}deg)`,transformOrigin:'50% 50%'}}>
   <PaperBackground index={sceneIndex} background={p.background}/><GridOverlay offset={-tx*.6}/><NewspaperLayer index={sceneIndex} text={p.paperElements.join(' • ')}/><YellowShape index={sceneIndex} elements={p.decorativeElements}/>
   <div style={{transform:`scale(${.88+.12*subjectPop})`}}><CutoutSubject src={all[0]} label={p.mainCharacter} index={sceneIndex}/></div>
   <SupportingPhotos items={all.slice(1)} index={sceneIndex} travel={travel} landscape={landscape}/>
   <div style={{transform:`scale(${.9+.1*graphicPop})`}}><div style={landscape?{position:'absolute',left:85,width:870,top:430,height:250,zIndex:8,pointerEvents:'none'}:{position:'absolute',left:40,right:40,top:720,height:330,zIndex:8,pointerEvents:'none'}}>{sceneIndex%2===0?<EvidencePanel items={p.dataLayers.slice(0,2)} index={sceneIndex} location={p.location}/>:<ContextEvidence labels={p.secondaryObjects.slice(0,2)} index={sceneIndex} travel={travel}/>}</div></div>
   {icons.map((icon,i)=>{const slot=iconSlots[i];return <SketchIcon key={`${icon}-${i}`} kind={icon} index={i} style={{left:slot.left,top:slot.top,zIndex:9}}/>})}
   <HandDrawnArrow flip={sceneIndex%2===1}/><EditorialTitle title={title} highlight={p.highlight||scene.keywords?.[0]||''} index={sceneIndex}/><SubtitleBlock text={scene.narration} index={sceneIndex}/>
  </div><PaperTransition preset={p.transition} index={sceneIndex}/>
 </AbsoluteFill>;
};
