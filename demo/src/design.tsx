import React from 'react';
import {AbsoluteFill, Easing, interpolate, useCurrentFrame, useVideoConfig} from 'remotion';

export const color = {bg: '#111213', panel: '#111213', ink: '#ECEBE6', muted: '#90938E', blue: '#ECEBE6', green: '#AFCDA0', red: '#F27B50'};
export const mono = '"Consolas", "Liberation Mono", monospace';
export const ease = Easing.bezier(0.16, 1, 0.3, 1);
export const Frame: React.FC<{chapter: string; children: React.ReactNode}> = ({chapter, children}) => {
  return <AbsoluteFill style={{background:color.bg,color:color.ink,fontFamily:mono}}>
    <div style={{position:'absolute',left:76,right:76,top:46,display:'flex',justifyContent:'space-between',fontSize:23,color:color.muted}}>
      <span style={{color:color.ink}}>proofcli</span><span>{chapter}</span>
    </div>
    <div style={{position:'absolute',left:76,right:76,top:104,height:1,background:'#343633'}}/>
    {children}
    <div style={{position:'absolute',left:76,bottom:42,fontSize:21,color:color.muted}}>github.com/bk1202/proofcli</div>
    <div style={{position:'absolute',right:76,bottom:42,fontSize:21,color:color.muted}}>actual output / edited timing</div>
  </AbsoluteFill>;
};
export const Note: React.FC<{children: React.ReactNode}> = ({children}) => {
  const frame=useCurrentFrame();const {fps}=useVideoConfig();
  return <div style={{position:'absolute',left:112,bottom:140,fontSize:32,color:color.ink,overflow:'hidden'}}>
    <div style={{translate:`0 ${interpolate(frame,[.2*fps,.6*fps],[45,0],{easing:ease,extrapolateLeft:'clamp',extrapolateRight:'clamp'})}px`}}>{children}</div>
  </div>;
};
