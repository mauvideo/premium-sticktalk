import React from 'react';
import {Composition} from 'remotion';
import {StickTalkVideo, Story} from './StickTalkVideo';

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
    durationInFrames={45 * 30}
    fps={30}
    width={1080}
    height={1920}
    defaultProps={sample}
    calculateMetadata={({props}) => {
      const landscape = props.aspectRatio === '16:9';
      return {
        durationInFrames: Math.max(1, Math.round(props.duration * 30)),
        width: landscape ? 1920 : 1080,
        height: landscape ? 1080 : 1920,
      };
    }}
  />
);
