import React from 'react';
import {interpolate,spring,useCurrentFrame,useVideoConfig} from 'remotion';
import {
  Map, Clock3, FileText, User, Building2, Ship, Plane, ChartNoAxesCombined,
  Dumbbell, HeartPulse, Phone, Car, BookOpen, Factory, Shield, Landmark,
  Timer, Droplets, BedDouble, Brain, Laptop, CircleHelp, Sun, Moon,
  BatteryFull, CalendarDays, BriefcaseBusiness, Activity, AlarmClock,
  Banana, Apple, GlassWater, Shirt, RotateCcw, PersonStanding, Footprints,
  BadgeCheck, Check, BicepsFlexed
} from 'lucide-react';

const pickIcon=(kind:string)=>{
  const k=kind.toLowerCase();
  if(k.includes('protein')||k.includes('shake')) return GlassWater;
  if(k.includes('banana')||k.includes('chuối')) return Banana;
  if(k.includes('apple')||k.includes('táo')) return Apple;
  if(k.includes('sports clothes')||k.includes('quần áo')||k.includes('đồ tập')) return Shirt;
  if(k.includes('water bottle')||k.includes('bình nước')) return GlassWater;
  if(k.includes('rotate joint')||k.includes('xoay khớp')) return RotateCcw;
  if(k.includes('stretch')||k.includes('giãn cơ')||k.includes('khởi động')) return PersonStanding;
  if(k.includes('treadmill')||k.includes('máy chạy')) return BicepsFlexed;
  if(k.includes('running shoe')||k.includes('giày chạy')||k.includes('đi bộ')) return Footprints;
  if(k.includes('weight rack')||k.includes('giá tạ')) return Dumbbell;
  if(k.includes('checkmark')||k.includes('đúng vị trí')) return BadgeCheck;
  if(k.includes('circadian')||k.includes('nhịp sinh học')||k.includes('đồng hồ sinh học')) return AlarmClock;
  if(k.includes('sun')||k.includes('mặt trời')) return Sun;
  if(k.includes('moon')||k.includes('mặt trăng')) return Moon;
  if(k.includes('battery')||k.includes('năng lượng')) return BatteryFull;
  if(k.includes('calendar')||k.includes('lịch')||k.includes('consistency')) return CalendarDays;
  if(k.includes('work')||k.includes('công việc')) return BriefcaseBusiness;
  if(k.includes('activity')||k.includes('vận động')) return Activity;
  if(k.includes('gym')||k.includes('dumbbell')||k.includes('tạ')||k.includes('weight')) return Dumbbell;
  if(k.includes('heart')||k.includes('tim')||k.includes('health')) return HeartPulse;
  if(k.includes('phone')||k.includes('điện thoại')) return Phone;
  if(k.includes('water')||k.includes('nước')) return Droplets;
  if(k.includes('sleep')||k.includes('ngủ')||k.includes('bed')) return BedDouble;
  if(k.includes('brain')||k.includes('não')) return Brain;
  if(k.includes('map')||k.includes('bản đồ')) return Map;
  if(k.includes('timeline')||k.includes('clock')||k.includes('thời')) return Clock3;
  if(k.includes('timer')||k.includes('phút')||k.includes('giây')) return Timer;
  if(k.includes('document')||k.includes('tài liệu')) return FileText;
  if(k.includes('military')||k.includes('quân')||k.includes('chiến')) return Shield;
  if(k.includes('factory')||k.includes('nhà máy')) return Factory;
  if(k.includes('car')||k.includes('xe')) return Car;
  if(k.includes('ship')||k.includes('tàu')) return Ship;
  if(k.includes('airplane')||k.includes('plane')||k.includes('máy bay')) return Plane;
  if(k.includes('book')||k.includes('sách')) return BookOpen;
  if(k.includes('chart')||k.includes('biểu đồ')) return ChartNoAxesCombined;
  if(k.includes('building')||k.includes('tòa nhà')) return Building2;
  if(k.includes('landmark')||k.includes('di tích')) return Landmark;
  if(k.includes('person')||k.includes('người')) return User;
  if(k.includes('check')) return Check;
  return CircleHelp;
};

export const SketchIcon:React.FC<{kind:string;index:number;style?:React.CSSProperties}>=({kind,index,style})=>{
  const frame=useCurrentFrame();
  const {fps}=useVideoConfig();
  const start=6+index*7;
  // Pop tuần tự: 0 -> overshoot -> 100%, không thay opacity đột ngột nên không gây chớp.
  const pop=spring({frame:Math.max(0,frame-start),fps,config:{damping:8,mass:.45,stiffness:210},durationInFrames:14});
  const scale=interpolate(pop,[0,.72,1],[0,1.16,1],{extrapolateLeft:'clamp',extrapolateRight:'clamp'});
  const local=Math.max(0,frame-start);
  // Chuyển động nhẹ liên tục, xác định theo frame để render ổn định tuyệt đối.
  const floatY=Math.sin((local+index*13)*0.09)*7;
  const rotate=Math.sin((local+index*17)*0.065)*2.2;
  const Icon=pickIcon(kind);
  return <div data-layer="semantic-lucide-icon" style={{position:'absolute',transformOrigin:'center',transform:`translateY(${floatY}px) rotate(${rotate}deg) scale(${scale})`,...style}}>
    <div style={{background:'#FFE600',padding:16,border:'3px solid #111',borderRadius:18,boxShadow:'7px 8px 0 #111'}}>
      <Icon size={148} strokeWidth={2.7} color="#111" />
    </div>
    <span style={{display:'block',font:'900 16px Arial',color:'#111',background:'#fffdf5',border:'3px solid #111',padding:'5px 8px',textAlign:'center',marginTop:8,textTransform:'uppercase',maxWidth:210,overflow:'hidden'}}>{kind}</span>
  </div>;
};
