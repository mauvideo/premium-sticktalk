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

const SupportingPhotos:React.FC<{items:string[];index:number;travel:number;landscape:boolean}>=({items,index,travel,landscape})=>{
  const photos=items.slice(0,2); if(!photos.length)return null;
  return <div style={landscape?{position:'absolute',top:310,left:720,width:320,display:'grid',gridTemplateColumns:'1fr 1fr',gap:18,zIndex:7,transform:`translateX(${travel*.08}px)`}:{position:'absolute',top:405,right:48,width:270,display:'grid',gap:22,zIndex:7,transform:`translateX(${travel*.08}px)`}}>
    {photos.map((src,i)=><div key={`${src}-${i}`} style={{height:landscape?210:180,background:'#fffdf5',padding:9,clipPath:tear(index+i+40),boxShadow:`9px 10px 0 ${i?'#d62b22':'#ffd400'}`,transform:`rotate(${i?2.5:-2.5}deg)`}}><Img src={assetUrl(src)} style={{width:'100%',height:'100%',objectFit:'cover',filter:'saturate(.82) contrast(1.05)',clipPath:tear(index+i+43)}}/></div>)}
  </div>;
};

export const VoxScene:React.FC<VoxSceneProps>=({scene,story,sceneIndex})=>{
  const f=useCurrentFrame(); const {durationInFrames:d,width,height,fps}=useVideoConfig(); const landscape=width>height;
  const p=plan(scene.visualPlan,sceneIndex); const all=[scene.image,...(scene.assets||[])].filter(Boolean) as string[];
  const travel=interpolate(f,[0,Math.max(1,d-1)],[-16,16],{extrapolateLeft:'clamp',extrapolateRight:'clamp'});
  const entrance=spring({frame:f,fps,config:{damping:18,mass:.75,stiffness:95}});
  const camera=p.camera; const scale=(camera==='push-in'?interpolate(f,[0,Math.max(1,d-1)],[1.015,1.065],{extrapolateRight:'clamp'}):1.035)*(.985+.015*entrance);
  const tx=camera==='pan-left'?-travel:camera==='pan-right'?travel:camera==='parallax'?travel*.45:Math.sin(f/30)*5;
  const ty=(1-entrance)*(sceneIndex%2===0?18:-18); const rot=camera==='rotate'?interpolate(f,[0,Math.max(1,d-1)],[-.65,.65],{extrapolateRight:'clamp'}):Math.sin(f/50)*.18;
  const title=scene.headline||String(story.title||scene.keywords?.join(' ')||'');
  const iconSlots=landscape?[{left:140,top:690,rotate:-6},{left:870,top:700,rotate:6}]:[{left:70,top:1120,rotate:-6},{left:770,top:1115,rotate:6}];
  const icons=p.icons.slice(0,2);
  return <AbsoluteFill style={{overflow:'hidden',background:'#d8c7a2'}}>
    <div style={{position:'absolute',inset:landscape?-24:-45,transform:`translate3d(${tx}px,${ty}px,0) scale(${scale}) rotate(${rot}deg)`,transformOrigin:'50% 50%'}}>
      <PaperBackground index={sceneIndex} background={p.background}/><GridOverlay offset={-tx*.6}/><NewspaperLayer index={sceneIndex} text={p.paperElements.join(' • ')}/><YellowShape index={sceneIndex}/>
      <CutoutSubject src={all[0]} label={p.mainCharacter} index={sceneIndex}/><SupportingPhotos items={all.slice(1)} index={sceneIndex} travel={travel} landscape={landscape}/>
      <div style={landscape?{position:'absolute',left:85,width:870,top:430,height:250,zIndex:8,pointerEvents:'none'}:{position:'absolute',left:40,right:40,top:720,height:330,zIndex:8,pointerEvents:'none'}}>{sceneIndex%2===0?<EvidencePanel items={p.dataLayers.slice(0,2)} index={sceneIndex} location={p.location}/>:<ContextEvidence labels={p.secondaryObjects.slice(0,2)} index={sceneIndex} travel={travel}/>}</div>
      {icons.map((icon,i)=>{const slot=iconSlots[i];return <SketchIcon key={`${icon}-${i}`} kind={icon} index={i} style={{left:slot.left,top:slot.top,transform:`rotate(${slot.rotate}deg) translateX(${travel*(i+1)*.04}px)`,zIndex:9}}/>})}
      <HandDrawnArrow flip={sceneIndex%2===1}/><EditorialTitle title={title} highlight={p.highlight||scene.keywords?.[0]||''} index={sceneIndex}/><SubtitleBlock text={scene.narration} index={sceneIndex}/>
    </div><PaperTransition preset={p.transition} index={sceneIndex}/>
  </AbsoluteFill>;
};
