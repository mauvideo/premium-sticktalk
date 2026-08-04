#!/usr/bin/env python3
import argparse,json,re
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
 p=argparse.ArgumentParser(); p.add_argument('--idea',required=True); p.add_argument('--duration',type=int,default=45); p.add_argument('--tone',default='sâu sắc'); p.add_argument('--format',default='hybrid'); p.add_argument('--style',default='dark_neon'); p.add_argument('--voice',default='nam_bac_news'); a=p.parse_args()
 weights=[4,5,6,6,6,6,6,6]; factor=a.duration/sum(weights)
 scenes=[]
 for i,(text,keys,camera,chars) in enumerate(TEMPLATES,1):
  scenes.append({'id':i,'type':'intro' if i==1 else 'outro' if i==len(TEMPLATES) else 'dialogue','duration':round(weights[i-1]*factor,2),'narration':text,'dialogue':[],'background':'dark','camera':camera,'transition':['slide','blur','whip','zoom'][i%4],'keywords':keys,'characters':chars})
 story={'title':a.idea,'hook':TEMPLATES[0][0],'message':'Chọn bình yên thay vì hơn thua.','cta':'Bạn nghĩ sao?','duration':a.duration,'style':a.style,'voice':a.voice,'audio':'assets/narration.mp3','scenes':scenes}
 Path('assets').mkdir(exist_ok=True); Path('output').mkdir(exist_ok=True)
 Path('assets/story.json').write_text(json.dumps(story,ensure_ascii=False,indent=2),encoding='utf-8')
 script='\n'.join(s['narration'] for s in scenes)
 Path('output/script.txt').write_text(script,encoding='utf-8')
 print(f'Đã tạo {len(scenes)} cảnh, tổng thời lượng {sum(s["duration"] for s in scenes):.1f}s')
if __name__=='__main__': main()
