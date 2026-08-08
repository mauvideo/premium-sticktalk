import React from 'react';
import {Composition} from 'remotion';
import {StickTalkVideo, Story} from './StickTalkVideo';

const FPS=30;
const sample: Story & {aspectRatio?: '9:16'|'16:9'} = {
  title: 'Premium StickTalk',
  duration: 45,
  style: 'vox_giay_cat',
  audio: 'assets/narration.mp3',
  aspectRatio: '9:16',
  scenes: []
};

export const Root: React.FC = () => (
  <Composition<any, Story & {aspectRatio?: '9:16'|'16:9'}>
    id="StickTalk"
    component={StickTalkVideo}
    durationInFrames={45 * FPS}
    fps={FPS}
    width={1080}
    height={1920}
    defaultProps={sample}
    calculateMetadata={({props}) => {
      const landscape = props.aspectRatio === '16:9';
      // Dùng đúng tổng số khung hình mà StickTalkVideo tạo cho từng phân cảnh.
      // Trước đây composition lấy props.duration*30 còn Sequence lại làm tròn từng scene,
      // có thể lệch đúng 1 frame (ví dụ 991 tổng nhưng scene chỉ phủ 990) và kẹt ở frame cuối.
      const sceneFrames=(props.scenes||[]).reduce((sum,scene)=>sum+Math.max(1,Math.round(Number(scene.duration||0)*FPS)),0);
      const fallbackFrames=Math.max(1,Math.round(Number(props.duration||45)*FPS));
      return {
        durationInFrames: sceneFrames>0?sceneFrames:fallbackFrames,
        width: landscape ? 1920 : 1080,
        height: landscape ? 1080 : 1920,
      };
    }}
  />
);
