#!/usr/bin/env python3
import argparse,asyncio,json
from pathlib import Path
import edge_tts

async def run(voice:str, rate:str):
 story=json.loads(Path('assets/story.json').read_text(encoding='utf-8'))
 text=' '.join(scene['narration'] for scene in story['scenes'])
 Path('assets').mkdir(exist_ok=True)
 communicate=edge_tts.Communicate(text=text,voice=voice,rate=rate)
 await communicate.save('assets/narration.mp3')
 print('Đã tạo assets/narration.mp3')

def main():
 p=argparse.ArgumentParser(); p.add_argument('--voice',default='vi-VN-NamMinhNeural'); p.add_argument('--rate',default='+4%'); a=p.parse_args()
 asyncio.run(run(a.voice,a.rate))
if __name__=='__main__': main()
