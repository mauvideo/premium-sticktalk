#!/usr/bin/env python3
"""Topic-driven visual planner for Vox paper-collage scenes."""
from __future__ import annotations
import re
PAPER=["newspaper","torn paper","marker","highlight","tape","stamp"]
CAMERAS=["push","pan left","pan right","parallax","soft rotate","slide"]
TRANSITIONS=["paper slide","paper reveal","card stack","mask reveal","wipe","cut"]
COMPOSITIONS=["subject-left with evidence-right","subject-right with map-left","center cutout with document stack","diagonal archival collage","timeline foreground with portrait background","map route with cutout subject"]
ICON_RULES=[
 ({"nhịp sinh học","đồng hồ sinh học","circadian rhythm"},"circadian clock"),
 ({"chu kỳ ngày đêm","mặt trời và mặt trăng","sun moon cycle"},"sun"),
 ({"ngủ đủ giấc","ngủ sâu","giấc ngủ sâu","deep sleep"},"sleep"),
 ({"năng lượng","hồi phục năng lượng","energy level"},"battery"),
 ({"đều đặn","nhất quán","thói quen hằng ngày","consistency"},"calendar"),
 ({"tập gym","phòng gym","tập tạ","nâng tạ","dumbbell","weight training"},"dumbbell"),
 ({"nhịp tim","tim mạch","heart rate"},"heart"),
 ({"điện thoại","phone","smartphone"},"phone"),
 ({"đi bộ","chạy bộ","khởi động","walking","running","warm up"},"walk"),
 ({"uống nước","nước uống","hydration"},"water"),
 ({"dinh dưỡng","bữa ăn","ăn uống","nutrition"},"food"),
 ({"giấc ngủ","nghỉ ngơi","sleep","rest"},"sleep"),
 ({"não bộ","sóng não","brain wave","brain"},"brain"),
 ({"công việc","làm việc","năng suất","productivity","work"},"work"),
 ({"bản đồ","địa điểm","vị trí địa lý","map"},"map"),
 ({"dòng thời gian","mốc thời gian","timeline"},"timeline"),
 ({"tài liệu","hồ sơ","văn kiện","document"},"document"),
 ({"quân đội","đại tướng","chiến dịch","trận đánh","binh sĩ","military"},"military"),
 ({"nhà máy","sản xuất công nghiệp","factory","industrial"},"factory"),
 ({"ô tô","xe hơi","car"},"car"),
 ({"tàu biển","con tàu","đại dương","ship"},"ship"),
 ({"máy bay","hàng không","airplane"},"airplane"),
 ({"sách giáo khoa","giáo dục","book"},"book"),
 ({"biểu đồ","số liệu thống kê","chart"},"chart"),
 ({"thành phố","đô thị","tòa nhà","building"},"building"),
]
ALLOWED_ICON_HINTS={"dumbbell","gym","heart","phone","walk","water","food","sleep","brain","computer","laptop","map","timeline","clock","timer","document","military","factory","car","ship","airplane","plane","book","chart","building","landmark","person","sun","moon","battery","calendar","work","circadian","activity"}
def _norm(text:str)->str:return " ".join(re.findall(r"[\wÀ-ỹ]+",str(text).casefold()))
def _pick(options:list[str],seed:int)->str:return options[seed%len(options)]
def _semantic_icons(text:str,evidence:list[str])->list[str]:
 hay=_norm(text+" "+" ".join(evidence));icons=[]
 for required,icon in ICON_RULES:
  if any(_norm(term) in hay for term in required) and icon not in icons:icons.append(icon)
 return icons[:2]
def _scene_icons(scene:dict,text:str,evidence:list[str])->list[str]:
 semantic=_semantic_icons(text,evidence);ai=[]
 for raw in scene.get("icons") or []:
  v=str(raw).strip().casefold()
  if not v:continue
  mapped=next((hint for hint in ALLOWED_ICON_HINTS if hint in v),None)
  if mapped and mapped in semantic and mapped not in ai:ai.append(mapped)
 return (ai or semantic)[:2]
def create_visual_plan(scene:dict,story:dict,scene_index:int)->dict:
 narration=str(scene.get("narration") or scene.get("loi_dan") or "")
 text=" ".join(str(scene.get(k,"")) for k in ("narration","loi_dan","sceneRole","storyProgress","imageFocus","headline","event"))
 seed=int(scene.get("seed") or (scene_index+1)*97);entity=scene.get("entityVisualPlan") or {};global_entities=story.get("entityVisualPlan") or {};evidence=[str(x) for x in (entity.get("visualEvidence") or []) if x];maps=list(global_entities.get("mapsNeeded") or []);charts=list(global_entities.get("chartsNeeded") or []);time_period=str(entity.get("timePeriod") or "");event=str(entity.get("event") or "");location=str(entity.get("location") or "")
 narration_norm=narration.casefold();tokens=set(re.findall(r"[\wÀ-ỹ]+",text.casefold()));data_layers=[]
 if maps and location and location.casefold() in narration_norm:data_layers.append({"type":"map","label":maps[0]})
 if charts and ({"số","liệu","tăng","giảm","%","phần","trăm"}&tokens):data_layers.append({"type":"chart","label":charts[scene_index%len(charts)]})
 if time_period and time_period in narration:data_layers.append({"type":"timeline","label":time_period})
 if not data_layers and event:data_layers.append({"type":"evidence","label":event})
 secondary=[x for x in [event,location,*evidence] if x]
 return {"background":"archival paper collage","mainCharacter":entity.get("mainSubject") or story.get("title") or "documentary subject","secondaryObjects":secondary[:3],"icons":_scene_icons(scene,text,secondary),"paperElements":[_pick(PAPER,seed+scene_index),_pick(PAPER,seed+scene_index+2)],"camera":_pick(CAMERAS,seed+scene_index),"transition":_pick(TRANSITIONS,seed+scene_index),"highlight":event or scene.get("imageFocus") or scene.get("sceneRole") or "Dữ kiện chính","mood":"documentary","colorPalette":"cream black yellow red","composition":_pick(COMPOSITIONS,seed+scene_index),"dataLayers":data_layers[:3],"location":location,"timePeriod":time_period,"layerContract":entity.get("assetRoles") or ["paper-background","print-texture","main-subject","context-photo","semantic-icon","map-chart-timeline","annotation","typography"]}
def apply_visual_plans(story:dict)->dict:
 used=set()
 for index,scene in enumerate(story.get("scenes",[])):
  plan=create_visual_plan(scene,story,index);base=plan["composition"]
  if base in used:plan["composition"]=f"{base} variant {index+1}"
  used.add(plan["composition"]);scene["visualPlan"]=plan
 return story
