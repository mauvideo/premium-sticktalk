import React from 'react';
import {interpolate, useCurrentFrame} from 'remotion';
import {C, tear} from './shared';
import {DataLayer} from './types';

const Graphic: React.FC<{item: DataLayer; index: number}> = ({item, index}) => {
  if (item.type === 'map') return <svg viewBox="0 0 300 150"><path d="M25 112 58 38l47 22 42-34 48 42 73-24-25 77-91-9-62 24Z" fill="none" stroke={C.ink} strokeWidth="7" strokeLinejoin="round"/><path d="m47 112 58-31 45 26 83-49" fill="none" stroke={C.red} strokeWidth="6" strokeDasharray="10 8"/><circle cx="233" cy="58" r="9" fill={C.yellow}/></svg>;
  if (item.type === 'chart') return <svg viewBox="0 0 300 150"><path d="M25 125V18M25 125h255" stroke={C.ink} strokeWidth="6"/><path d="m35 110 58-36 49 17 53-51 70-20" fill="none" stroke={index % 2 ? C.red : C.yellow} strokeWidth="10"/><circle cx="265" cy="20" r="9" fill={C.ink}/></svg>;
  return <svg viewBox="0 0 300 90"><path d="M20 45h260" stroke={C.ink} strokeWidth="6"/><circle cx="55" cy="45" r="15" fill={C.red}/><circle cx="155" cy="45" r="15" fill={C.yellow}/><circle cx="255" cy="45" r="15" fill={C.ink}/></svg>;
};

export const EvidencePanel: React.FC<{items: DataLayer[]; index: number; location?: string}> = ({items, index, location}) => {
  const frame = useCurrentFrame();
  const enter = interpolate(frame, [8, 22], [60, 0], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});
  const item = items[0];
  if (!item) return null;
  return <div data-layer="data-map-chart-timeline" style={{position:'absolute',left:64,top:1215,width:330,transform:`translateY(${enter}px) rotate(-2deg)`,zIndex:8}}>
    <div style={{background:C.paper,padding:'12px 16px 14px',clipPath:tear(index+8),border:`5px solid ${C.ink}`,boxShadow:`10px 12px 0 ${C.yellow}`}}>
      <Graphic item={item} index={index}/>
      <div style={{font:'900 23px Arial',textTransform:'uppercase'}}>{item.label}</div>
      {location ? <div style={{font:'700 18px Arial',marginTop:4,color:'#555'}}>{location}</div>:null}
    </div>
  </div>;
};
