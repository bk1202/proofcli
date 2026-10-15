import React from 'react';
import {interpolate,useCurrentFrame,useVideoConfig} from 'remotion';
import {color,Frame,Note,ease} from './design';
import evidence from './evidence.json';

export const Verification: React.FC = () => {
  const frame=useCurrentFrame(); const {fps}=useVideoConfig();
  return <Frame chapter="03 / verify the contract">
    <div style={{position:'absolute',left:112,top:169,fontSize:31,color:color.ink}}><span style={{color:color.muted}}>&gt; </span>{evidence.commands.proofcli}</div>
    <div style={{position:'absolute',left:112,top:276,fontSize:35,lineHeight:1.7,scale:interpolate(frame,[2.2*fps,3*fps],[1,1.065],{easing:ease,extrapolateLeft:'clamp',extrapolateRight:'clamp'}),transformOrigin:'left center',opacity:interpolate(frame,[.35*fps,.5*fps],[0,1],{extrapolateLeft:'clamp',extrapolateRight:'clamp'})}}>
      <div style={{color:color.muted,fontSize:22,marginBottom:18}}>report excerpt</div>
      <div><span style={{color:color.muted}}>"status": </span><span style={{color:color.red}}>"{evidence.proofcli.status}"</span>,</div>
      <div><span style={{color:color.muted}}>"exit_code": </span>{evidence.proofcli.child_exit_code},</div>
      <div style={{marginTop:29,color:color.muted}}>"difference": {'{'}</div>
      <div style={{paddingLeft:42}}>"path": "{evidence.proofcli.difference.path}",</div>
      <div style={{paddingLeft:42}}>"expected": "{evidence.proofcli.difference.expected}",</div>
      <div style={{paddingLeft:42,color:color.red}}><span style={{position:'relative'}}>"actual": "{evidence.proofcli.difference.actual}"<span style={{position:'absolute',left:0,right:0,bottom:-12,height:3,background:color.red,transformOrigin:'left',scale:`${interpolate(frame,[1.4*fps,2*fps],[0,1],{easing:ease,extrapolateLeft:'clamp',extrapolateRight:'clamp'})} 1`}}/></span></div>
      <div style={{color:color.muted}}>{'}'}</div>
    </div>
    <div style={{position:'absolute',right:150,top:527,textAlign:'right',opacity:interpolate(frame,[3.3*fps,3.5*fps],[0,1],{extrapolateLeft:'clamp',extrapolateRight:'clamp'})}}>
      <div style={{fontSize:25,color:color.muted}}>ProofCLI exit</div><div style={{fontSize:176,lineHeight:1.25,color:color.red,translate:`0 ${interpolate(frame,[3.3*fps,3.9*fps],[180,0],{easing:ease,extrapolateLeft:'clamp',extrapolateRight:'clamp'})}px`}}>{evidence.proofcli.exit_code}</div>
    </div>
    <div style={{position:'absolute',left:112,top:827,fontSize:23,color:color.muted,opacity:interpolate(frame,[5*fps,5.5*fps],[0,1],{extrapolateLeft:'clamp',extrapolateRight:'clamp'})}}>JSON record check: failed   /   CSV record check: failed</div>
    <Note>The command exited 0. The records don't match.</Note>
  </Frame>;
};
