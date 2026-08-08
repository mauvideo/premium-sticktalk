import React from 'react';
import {spring,useCurrentFrame,useVideoConfig} from 'remotion';
import {Fan,Wind,Snowflake,Zap,Gauge,Cpu,Rocket,Car,Map,Shield,Dumbbell,Droplets,Moon,BatteryFull,Brain,Plane,Ship} from 'lucide-react';
import {C} from './shared';

type Props={index:number;elements?:string[]};

const Tank:React.FC=()=> <svg width="190" height="130" viewBox="0 0 190 130" fill="none" stroke="#171711" strokeWidth="8" strokeLinecap="round" strokeLinejoin="round"><rect x="35" y="52" width="112" height="42" rx="8" fill="#FFE600"/><path d="M76 52V35h42l12 17M130 39l43-14"/><path d="M28 96h130"/><circle cx="48" cy="103" r="13" fill="#fffdf5"/><circle cx="82" cy="103" r="13" fill="#fffdf5"/><circle cx="116" cy="103" r="13" fill="#fffdf5"/><circle cx="150" cy="103" r="13" fill="#fffdf5"/></svg>;
const SunMoon:React.FC=()=> <div style={{display:'flex',gap:16,alignItems:'center'}}><div style={{width:76,height:76,borderRadius:'50%',background:'#FFE600',border:'7px solid #171711'}}/><Moon size={92} strokeWidth={2.8}/></div>;

const iconFor=(kind:string):React.FC<any>=>{
 const k=kind.toLowerCase();
 if(k.includes('fan'))return Fan;if(k.includes('airflow'))return Wind;if(k.includes('snowflake'))return Snowflake;
 if(k.includes('electricity'))return Zap;if(k.includes('gauge'))return Gauge;if(k.includes('chip'))return Cpu;if(k==='ai')return Brain;
 if(k.includes('rocket'))return Rocket;if(k.includes('electric-car'))return Car;if(k.includes('map'))return Map;if(k.includes('military'))return Shield;
 if(k.includes('dumbbell'))return Dumbbell;if(k.includes('water'))return Droplets;if(k.includes('battery'))return BatteryFull;
 if(k.includes('brain'))return Brain;if(k.includes('airplane'))return Plane;if(k.includes('ship'))return Ship;return Zap;
};

export const YellowShape:React.FC<Props>=({index,elements=[]})=>{
 const f=useCurrentFrame(),{fps}=useVideoConfig();
 const s=spring({frame:Math.max(0,f-3),fps,config:{damping:13,mass:.6,stiffness:155}});
 const items=elements.slice(0,2);
 if(!items.length)return null;
 return <div data-layer="semantic-topic-elements" style={{position:'absolute',left:index%2?500:65,top:index%3===1?420:330,zIndex:4,display:'flex',gap:18,alignItems:'center',transform:`scale(${.82+.18*s}) rotate(${index%2?2:-2}deg)`,transformOrigin:'center'}}>
  {items.map((kind,i)=>{const local=Math.max(0,f-8-i*7);const pop=spring({frame:local,fps,config:{damping:10,mass:.5,stiffness:190}});const float=Math.sin((f+i*17)*.07)*6;const rot=Math.sin((f+i*23)*.05)*2.2;return <div key={`${kind}-${i}`} style={{minWidth:170,minHeight:150,padding:18,display:'flex',alignItems:'center',justifyContent:'center',background:C.yellow,border:'5px solid #171711',boxShadow:'10px 12px 0 #171711',clipPath:'polygon(3% 0,97% 3%,100% 18%,97% 37%,100% 55%,97% 76%,100% 98%,3% 100%,0 82%,3% 63%,0 43%,3% 22%,0 7%)',transform:`translateY(${float}px) rotate(${rot}deg) scale(${Math.min(1.08,.7+.3*pop)})`}}>
   {kind==='tank'?<Tank/>:kind==='sun-moon'?<SunMoon/>:React.createElement(iconFor(kind),{size:145,strokeWidth:2.8,color:'#171711'})}
  </div>})}
 </div>;
};
