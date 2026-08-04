import React from 'react';
import {Composition} from 'remotion';
import {StickTalkVideo, Story} from './StickTalkVideo';

const sample: Story = {
  title: 'Người trưởng thành không cần thắng mọi cuộc tranh luận',
  duration: 45,
  style: 'dark_neon',
  audio: 'assets/narration.mp3',
  scenes: []
};

export const Root: React.FC = () => (
  <Composition<any, Story>
    id="StickTalk"
    component={StickTalkVideo}
    durationInFrames={45 * 30}
    fps={30}
    width={1080}
    height={1920}
    defaultProps={sample}
    calculateMetadata={({props}) => ({durationInFrames: Math.max(1, Math.round(props.duration * 30))})}
  />
);
