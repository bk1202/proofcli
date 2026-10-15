import React from 'react';
import {interpolate,useCurrentFrame,useVideoConfig} from 'remotion';
import {color,Frame,Note,ease} from './design';
import evidence from './evidence.json';

export const Opening: React.FC = () => {
  const frame=useCurrentFrame();const {fps}=useVideoConfig();
  return <Frame chapter="01 / export">
    <div style={{position:'absolute',left:112,top:196,width:1570,fontSize:35,lineHeight:1.7,scale:interpolate(frame,[3*fps,4*fps],[1,1.045],{easing:ease,extrapolateLeft:'clamp',extrapolateRight:'clamp'}),transformOrigin:'left top'}}>
      <div style={{color:color.muted,marginBottom:26}}>export-demo &gt;</div>
      <div style={{whiteSpace:'pre-wrap'}}>{evidence.commands.export}</div>
      <div style={{marginTop:48,opacity:interpolate(frame,[fps,1.15*fps],[0,1],{extrapolateLeft:'clamp',extrapolateRight:'clamp'})}}>{evidence.ordinary.stdout}</div>
    </div>
    <div style={{position:'absolute',right:150,top:527,overflow:'hidden',textAlign:'right',opacity:interpolate(frame,[1.8*fps,2*fps],[0,1],{extrapolateLeft:'clamp',extrapolateRight:'clamp'})}}>
      <div style={{fontSize:25,color:color.muted}}>process exit</div>
      <div style={{fontSize:176,lineHeight:1.25,color:color.green,translate:`0 ${interpolate(frame,[1.8*fps,2.4*fps],[190,0],{easing:ease,extrapolateLeft:'clamp',extrapolateRight:'clamp'})}px`}}>{evidence.ordinary.exit_code}</div>
    </div>
    <div style={{position:'absolute',left:112,top:598,width:interpolate(frame,[2.3*fps,3*fps],[0,1130],{easing:ease,extrapolateLeft:'clamp',extrapolateRight:'clamp'}),height:1,background:'#4C5048'}}/>
    <Note>The export step passes.</Note>
  </Frame>;
};
