#!/usr/bin/env python3
"""Tạo giọng đọc VieNeu theo từng scene và đồng bộ phụ đề chính xác."""
from __future__ import annotations
import argparse,json,os,re,subprocess,unicodedata
from pathlib import Path
from typing import Any
from mutagen.mp3 import MP3
from vieneu import Vieneu

def clean_text(text:str)->str:
 text=re.sub(r"\s+"," ",str(text or "")).strip();text=re.sub(r"(?<=\d)\s*%"," phần trăm",text);return re.sub(r"\s+([.!?,:;])",r"\1",text)
def normalize_requested_voice(selected:str,custom_voice_id:str)->str:
 value=selected.strip();aliases={"":"Trúc Ly","default":"Trúc Ly","Mặc định — Trúc Ly":"Trúc Ly","Bác sĩ Tuyên":"Phạm Tuyền","bac_si_tuyen":"Phạm Tuyền"}
 if value in aliases:return aliases[value]
 if value=="Nhập mã giọng khác":
  custom=custom_voice_id.strip()
  if not custom:raise ValueError("Bạn đã chọn nhập mã giọng khác nhưng chưa điền tên hoặc mã giọng VieNeu.")
  return custom
 return value
def _key(value:object)->str:
 text=unicodedata.normalize("NFKD",str(value));text="".join(ch for ch in text if unicodedata.category(ch) not in {"Mn","Cf"});text=text.replace("đ","d").replace("Đ","D");return re.sub(r"[^0-9a-zA-Z]+","",text).casefold()
def resolve_preset_voice(available:list[tuple[Any,Any]],requested:str)->tuple[Any,str,str]:
 wanted=_key(requested)
 for label,voice_id in available:
  if wanted and wanted in {_key(label),_key(voice_id)}:return voice_id,str(voice_id).strip(),str(label).strip()
 raise ValueError(f"Không tìm thấy giọng VieNeu '{requested}'.")
def _wav_to_mp3(wav:Path,mp3:Path):
 subprocess.run(["ffmpeg","-y","-loglevel","error","-i",str(wav),"-codec:a","libmp3lame","-b:a","192k",str(mp3)],check=True)

def synthesize(voice_selection:str,custom_voice_id:str,emotion:str)->None:
 story_path=Path("assets/story.json")
 if not story_path.is_file():raise RuntimeError("Không tìm thấy assets/story.json.")
 story=json.loads(story_path.read_text(encoding="utf-8"));scenes=story.get("scenes") or []
 if not scenes:raise RuntimeError("Kịch bản không có scene để tạo giọng đọc.")
 style_code={"Tự nhiên":"tu_nhien","Kể chuyện":"ke_chuyen","Tin tức":"tin_tuc","tu_nhien":"tu_nhien","ke_chuyen":"ke_chuyen","tin_tuc":"tin_tuc"}.get(emotion)
 if style_code is None:raise ValueError(f"Phong cách đọc không hợp lệ: {emotion}")
 requested=normalize_requested_voice(voice_selection,custom_voice_id);tts=Vieneu(backend="onnx");voice_value,voice_name,description=resolve_preset_voice(list(tts.list_preset_voices()),requested)
 out_dir=Path("assets/tts-scenes");out_dir.mkdir(parents=True,exist_ok=True);Path("output").mkdir(parents=True,exist_ok=True)
 concat=[];total=0.0
 for i,scene in enumerate(scenes,1):
  text=clean_text(scene.get("narration") or scene.get("loi_dan") or "")
  if not text:raise RuntimeError(f"Scene {i} không có lời dẫn.")
  scene["narration"]=text;scene["subtitleText"]=text;scene["ttsText"]=text
  wav=out_dir/f"scene-{i:02d}.wav";mp3=out_dir/f"scene-{i:02d}.mp3"
  audio=tts.infer(text,voice=voice_value,style=style_code);tts.save(audio,str(wav));_wav_to_mp3(wav,mp3)
  duration=float(MP3(mp3).info.length);display=round(duration+0.08,3)
  scene["audioDuration"]=round(duration,3);scene["duration"]=display;scene["subtitleStart"]=round(total,3);scene["subtitleEnd"]=round(total+duration,3);total+=display
  concat.append(f"file '{mp3.resolve().as_posix()}'")
 concat_file=out_dir/"concat.txt";concat_file.write_text("\n".join(concat)+"\n",encoding="utf-8")
 narration=Path("assets/narration.mp3");subprocess.run(["ffmpeg","-y","-loglevel","error","-f","concat","-safe","0","-i",str(concat_file),"-c:a","libmp3lame","-b:a","192k",str(narration)],check=True)
 actual=float(MP3(narration).info.length);story["duration"]=round(total,3);story["subtitleTimingMode"]="scene-tts-exact";story_path.write_text(json.dumps(story,ensure_ascii=False,indent=2),encoding="utf-8")
 Path("output/tts-info.json").write_text(json.dumps({"nha_cung_cap":"vieneu","engine":"v3_turbo","ten_giong":voice_name,"mo_ta_giong":description,"phong_cach_doc":style_code,"thoi_luong_giay":round(actual,3),"scene_count":len(scenes),"subtitle_sync":"exact-per-scene-tts"},ensure_ascii=False,indent=2),encoding="utf-8")
 print(f"Đã tạo {len(scenes)} đoạn TTS; phụ đề và thoại dùng cùng văn bản, cùng timing từng scene.")
def main():
 p=argparse.ArgumentParser();p.add_argument("--voice",default=os.getenv("VIENEU_VOICE","Mặc định — Trúc Ly"));p.add_argument("--custom-voice-id",default=os.getenv("VIENEU_CUSTOM_VOICE_ID",""));p.add_argument("--emotion",default=os.getenv("VIENEU_EMOTION","Tự nhiên"));a=p.parse_args();synthesize(a.voice,a.custom_voice_id,a.emotion)
if __name__=="__main__":main()
