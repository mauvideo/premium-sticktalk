import React from 'react';
import {interpolate,useCurrentFrame} from 'remotion';
import {
  Map, Clock3, FileText, User, Building2, Ship, Plane, ChartNoAxesCombined,
  Dumbbell, HeartPulse, Phone, Car, BookOpen, Factory, Shield, Landmark,
  Footprints, Timer, Droplets, Utensils, BedDouble, Brain, Laptop, CircleHelp,
  Sun, Moon, BatteryFull, CalendarDays, BriefcaseBusiness, Activity, AlarmClock
} from 'lucide-react';

const pickIcon=(kind:string)=>{
  const k=kind.toLowerCase();
  if(k.includes('circadian')||k.includes('nhịp sinh học')||k.includes('đồng hồ sinh học')) return AlarmClock;
  if(k.includes('sun')||k.includes('mặt trời')||k.includes('ban ngày')) return Sun;
  if(k.includes('moon')||k.includes('mặt trăng')||k.includes('ban đêm')) return Moon;
  if(k.includes('battery')||k.includes('năng lượng')||k.includes('energy')) return BatteryFull;
  if(k.includes('calendar')||k.includes('lịch')||k.includes('consistency')||k.includes('đều đặn')) return CalendarDays;
  if(k.includes('work')||k.includes('công việc')||k.includes('business')) return BriefcaseBusiness;
  if(k.includes('vitality')||k.includes('sinh lực')||k.includes('activity')) return Activity;
  if(k.includes('gym')||k.includes('dumbbell')||k.includes('tạ')||k.includes('weight')) return Dumbbell;
  if(k.includes('heart')||k.includes('tim')||k.includes('health')) return HeartPulse;
  if(k.includes('phone')||k.includes('điện thoại')||k.includes('call')) return Phone;
  if(k.includes('walk')||k.includes('chạy')||k.includes('đi bộ')||k.includes('foot')) return Footprints;
  if(k.includes('water')||k.includes('nước')||k.includes('drink')) return Droplets;
  if(k.includes('food')||k.includes('ăn')||k.includes('meal')) return Utensils;
  if(k.includes('sleep')||k.includes('ngủ')||k.includes('rest')||k.includes('bed')) return BedDouble;
  if(k.includes('brain')||k.includes('não')||k.includes('wave')) return Brain;
  if(k.includes('computer')||k.includes('laptop')||k.includes('tech')) return Laptop;
  if(k.includes('map')||k.includes('bản đồ')) return Map;
  if(k.includes('timeline')||k.includes('clock')||k.includes('thời')||k.includes('năm')) return Clock3;
  if(k.includes('timer')||k.includes('phút')||k.includes('giây')) return Timer;
  if(k.includes('document')||k.includes('tài liệu')||k.includes('hồ sơ')) return FileText;
  if(k.includes('military')||k.includes('quân')||k.includes('chiến')) return Shield;
  if(k.includes('factory')||k.includes('nhà máy')||k.includes('industrial')) return Factory;
  if(k.includes('car')||k.includes('xe')) return Car;
  if(k.includes('ship')||k.includes('tàu')) return Ship;
  if(k.includes('airplane')||k.includes('plane')||k.includes('máy bay')) return Plane;
  if(k.includes('book')||k.includes('sách')||k.includes('học')) return BookOpen;
  if(k.includes('chart')||k.includes('biểu đồ')||k.includes('số liệu')) return ChartNoAxesCombined;
  if(k.includes('building')||k.includes('tòa nhà')||k.includes('thành phố')) return Building2;
  if(k.includes('landmark')||k.includes('di tích')) return Landmark;
  if(k.includes('person')||k.includes('người')||k.includes('nhân vật')) return User;
  return CircleHelp;
};

export const SketchIcon:React.FC<{kind:string;index:number;style?:React.CSSProperties}>=({kind,index,style})=>{
  const f=useCurrentFrame();
  const reveal=interpolate(f,[8+index*3,24+index*3],[0,1],{extrapolateLeft:'clamp',extrapolateRight:'clamp'});
  const Icon=pickIcon(kind);
  return <div data-layer="semantic-lucide-icon" style={{position:'absolute',opacity:reveal,transformOrigin:'center',...style}}>
    <div style={{background:'#fffdf5',padding:18,border:'4px solid #171711',boxShadow:'8px 9px 0 #f4c900'}}>
      <Icon size={174} strokeWidth={2.5} color="#171711" />
    </div>
    <span style={{display:'block',font:'900 17px Arial',textAlign:'center',marginTop:8,textTransform:'uppercase',maxWidth:220,overflow:'hidden'}}>{kind}</span>
  </div>;
};
