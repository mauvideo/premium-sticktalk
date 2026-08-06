import React from 'react';
import {AbsoluteFill,Img,interpolate,useCurrentFrame,useVideoConfig} from 'remotion';
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

const SupportingPhotos:React.FC<{items:string[];index:number;travel:number}>=({items,index,travel})=>{
  const photos=items.slice(0,2);
  if(!photos.length)return null;
  return <div style={{position:'absolute',top:370,right:55,width:300,display:'grid',gap:18,zIndex:7,transform:`translateX(${travel*.12}px)`}}>
    {photos.map((src,i)=><div key={`${src}-${i}`} style={{height:205,background:'#fffdf5',padding:10,clipPath:tear(index+i+40),boxShadow:`10px 12px 0 ${i?'#d62b22':'#ffd400'}`,transform:`rotate(${i?3:-3}deg)`}}><Img src={assetUrl(src)} style={{width:'100%',height:'100%',objectFit:'cover',filter:'grayscale(1) contrast(1.08)',clipPath:tear(index+i+43)}}/></div>)}
  </div>;
};

export const VoxScene:React.FC<VoxSceneProps>=({scene,story,sceneIndex})=>{
  const f=useCurrentFrame();
  const {durationInFrames:d}=useVideoConfig();
  const p=plan(scene.visualPlan,sceneIndex);
  const all=[scene.image,...(scene.assets||[])].filter(Boolean) as string[];
  const camera=p.camera;
  const travel=interpolate(f,[0,d],[-20,20],{extrapolateRight:'clamp'});
  const scale=camera==='push-in'?interpolate(f,[0,d],[1,1.07]):1.025;
  const tx=camera==='pan-left'?-travel:camera==='pan-right'?travel:camera==='parallax'?travel*.5:Math.sin(f/22)*8;
  const rot=camera==='rotate'?interpolate(f,[0,d],[-1.2,1.2]):Math.sin(f/35)*.35;
  const title=scene.headline||String(story.title||scene.keywords?.join(' ')||'');
  const iconSlots=[
    {left:430,top:1290,rotate:-7},
    {left:780,top:1295,rotate:7},
  ];
  return <AbsoluteFill style={{overflow:'hidden',background:'#f4efdf'}}>
    <div style={{position:'absolute',inset:-45,transform:`translateX(${tx}px) scale(${scale}) rotate(${rot}deg)`}}>
      <PaperBackground index={sceneIndex} background={p.background}/>
      <GridOverlay offset={-tx*.6}/>
      <NewspaperLayer index={sceneIndex} text={p.paperElements.join(' • ')}/>
      <YellowShape index={sceneIndex}/>
      <CutoutSubject src={all[0]} label={p.mainCharacter} index={sceneIndex}/>
      <SupportingPhotos items={all.slice(1)} index={sceneIndex} travel={travel}/>
      {sceneIndex%2===0?<EvidencePanel items={p.dataLayers} index={sceneIndex} location={p.location}/>:<ContextEvidence labels={p.secondaryObjects} index={sceneIndex} travel={travel}/>} 
      {p.icons.slice(0,2).map((icon,i)=>{const slot=iconSlots[i];return <SketchIcon key={`${icon}-${i}`} kind={icon} index={i} style={{left:slot.left,top:slot.top,transform:`rotate(${slot.rotate}deg) translateX(${travel*(i+1)*.08}px)`,zIndex:9}}/>})}
      <HandDrawnArrow flip={sceneIndex%2===1}/>
      <EditorialTitle title={title} highlight={p.highlight||scene.keywords?.[0]||''} index={sceneIndex}/>
      <SubtitleBlock text={scene.narration} index={sceneIndex}/>
    </div>
    <PaperTransition preset={p.transition} index={sceneIndex}/>
  </AbsoluteFill>;
};
