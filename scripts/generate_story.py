#!/usr/bin/env python3
import argparse,hashlib,json,random
from pathlib import Path

TEMPLATES=[
("Bạn có từng cố thắng một cuộc tranh luận, rồi nhận ra mình đã mất nhiều hơn được?",["tranh","luận"],"zoom_in",[{"name":"A","position":"left","action":"walk","emotion":"serious"}]),
("Người trưởng thành hiểu rằng không phải lời nào cũng cần đáp lại.",["trưởng","thành"],"pan_right",[{"name":"A","position":"center","action":"think","emotion":"serious"}]),
("Có người chỉ muốn được nghe mình nói, chứ không muốn tìm sự thật.",["sự","thật"],"punch_in",[{"name":"A","position":"left","action":"point","emotion":"angry"},{"name":"B","position":"right","action":"shake","emotion":"angry"}]),
("Nếu bạn tiếp tục đôi co, cả hai chỉ càng xa nhau hơn.",["đôi","co"],"pan_left",[{"name":"A","position":"left","action":"shake","emotion":"sad"},{"name":"B","position":"right","action":"point","emotion":"angry"}]),
("Im lặng không phải yếu đuối. Đó là khả năng chọn điều xứng đáng với năng lượng của mình.",["im","lặng"],"zoom_out",[{"name":"A","position":"center","action":"stand","emotion":"serious"}]),
("Bạn vẫn có thể nói rõ quan điểm, nhưng không cần biến mọi khác biệt thành một trận chiến.",["khác","biệt"],"zoom_in",[{"name":"A","position":"left","action":"point","emotion":"happy"},{"name":"B","position":"right","action":"nod","emotion":"happy"}]),
("Đôi khi chiến thắng lớn nhất là giữ được sự bình tĩnh và lòng tự trọng.",["chiến","thắng"],"punch_in",[{"name":"A","position":"center","action":"nod","emotion":"happy"}]),
("Lần tới, hãy tự hỏi: chuyện này có thật sự đáng để mình đánh đổi bình yên không?",["bình","yên"],"zoom_out",[{"name":"A","position":"center","action":"think","emotion":"serious"}])]

def main():
 p=argparse.ArgumentParser(); p.add_argument('--idea',required=True); p.add_argument('--duration',type=int,default=45); p.add_argument('--tone',default='sâu sắc'); p.add_argument('--format',default='hybrid'); p.add_argument('--style',default='dark_neon'); p.add_argument('--voice',default='nam_bac_news'); p.add_argument('--motion-level',default='medium'); a=p.parse_args()
 a.motion_level={'nhẹ':'light','trung_bình':'medium','nhiều':'high','viral_tiktok':'viral'}.get(a.motion_level,a.motion_level)
 if a.motion_level not in {'light','medium','high','viral'}: p.error('--motion-level không hợp lệ')
 rng=random.Random(int(hashlib.sha256(f'{a.idea}|{a.style}|{a.motion_level}'.encode()).hexdigest()[:12],16))
 styles={'người_que_triết_lý':'philosophy','người_que_tiktok':'tiktok','người_que_doanh_nhân':'entrepreneur','người_que_kể_chuyện':'storytelling','tin_tức_ai':'news'}
 style=styles.get(a.style,a.style); strength={'light':.45,'medium':.75,'high':1.05,'viral':1.35}[a.motion_level]
 cameras=['zoom-in','zoom-out','dolly','push','pull','pan-left','pan-right','tilt-up','tilt-down','orbit','handheld','parallax']
 transitions=['fade','flash','blur','whip','slide','mask','morph','glitch','scale','camera-cut']; easings=['linear','ease-in','ease-out','ease-in-out']
 weights=[4,5,6,6,6,6,6,6]; factor=a.duration/sum(weights)
 scenes=[]
 for i,(text,keys,_camera,chars) in enumerate(TEMPLATES,1):
  # A seeded shuffle provides reproducible exports while preventing adjacent scenes from repeating motion or timing.
  camera=cameras.pop(rng.randrange(len(cameras))); transition=transitions.pop(rng.randrange(len(transitions)))
  duration=round(weights[i-1]*factor*rng.uniform(.94,1.06),2)
  gesture={'think':'think','point':'point-right','shake':'angry','nod':'idle','stand':'stand','walk':'walk'}
  characters=[{**c,'gesture':gesture.get(c['action'],'idle')} for c in chars]
  scenes.append({'id':i,'type':'intro' if i==1 else 'outro' if i==len(TEMPLATES) else 'dialogue','duration':duration,'narration':text,'dialogue':[],'background':'dark','camera':{'type':camera,'speed':round(rng.uniform(.85,1.15),2),'easing':rng.choice(easings),'strength':strength,'duration':duration},'transition':{'type':transition,'strength':strength,'duration':round(rng.uniform(.3,.75),2)},'emotion':characters[0]['emotion'],'gesture':characters[0]['gesture'],'zoom':round(rng.uniform(.06,.15),2),'subtitleAnimation':rng.choice(['pop','fade','slide','word','karaoke']),'keywords':keys,'characters':characters,'seed':rng.randrange(1,1000000)})
 total=sum(s['duration'] for s in scenes); scenes[-1]['duration']=round(scenes[-1]['duration']+(a.duration-total),2)
 story={'version':3,'title':a.idea,'hook':TEMPLATES[0][0],'message':'Chọn bình yên thay vì hơn thua.','cta':'Bạn nghĩ sao?','duration':a.duration,'style':style,'motionLevel':a.motion_level,'voice':a.voice,'audio':'assets/narration.mp3','scenes':scenes}
 Path('assets').mkdir(exist_ok=True); Path('output').mkdir(exist_ok=True)
 Path('assets/story.json').write_text(json.dumps(story,ensure_ascii=False,indent=2),encoding='utf-8')
 script='\n'.join(s['narration'] for s in scenes)
 Path('output/script.txt').write_text(script,encoding='utf-8')
 print(f'Đã tạo {len(scenes)} cảnh, tổng thời lượng {sum(s["duration"] for s in scenes):.1f}s')
if __name__=='__main__': main()
