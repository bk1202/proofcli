import React from 'react';
import {interpolate,useCurrentFrame,useVideoConfig} from 'remotion';
import {color,Frame,Note,ease} from './design';

export const Closing: React.FC = () => {
  const frame=useCurrentFrame();const {fps}=useVideoConfig();
  return <Frame chapter="04 / add to CI">
    <div style={{position:'absolute',left:112,top:222,fontSize:26,color:color.muted}}>.github/workflows/export.yml</div>
    <div style={{position:'absolute',left:112,top:330,fontSize:41,lineHeight:1.9,whiteSpace:'pre',translate:`${interpolate(frame,[0,.6*fps],[55,0],{easing:ease,extrapolateLeft:'clamp',extrapolateRight:'clamp'})}px 0`}}>
      <div><span style={{color:color.muted}}>- uses: </span>bk1202/proofcli@v0.4.0</div><div style={{color:color.muted}}>  with:</div><div>    spec: tests/export-contract.json</div>
    </div>
    <div style={{position:'absolute',left:112,top:650,width:interpolate(frame,[.5*fps,1.2*fps],[0,1650],{easing:ease,extrapolateLeft:'clamp',extrapolateRight:'clamp'}),height:1,background:'#454841'}}/>
    <div style={{position:'absolute',left:112,top:720,fontSize:28,color:color.muted}}>Python setup included. Your assertions define the check.</div>
    <Note>Check the exported records in CI.</Note>
  </Frame>;
};
