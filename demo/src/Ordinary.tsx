import React from 'react';
import {interpolate,useCurrentFrame,useVideoConfig} from 'remotion';
import {color,Frame,Note,ease} from './design';
import evidence from './evidence.json';

export const Ordinary: React.FC = () => {
  const frame=useCurrentFrame(); const {fps}=useVideoConfig();
  return <Frame chapter="02 / inspect files">
    <div style={{position:'absolute',left:112,top:218,width:1696,display:'flex',gap:100,scale:interpolate(frame,[1.4*fps,2.2*fps],[1,1.08],{easing:ease,extrapolateLeft:'clamp',extrapolateRight:'clamp'}),transformOrigin:'left 220px'}}>
      <div style={{width:760}}><div style={{fontSize:26,color:color.muted,marginBottom:48}}>fixtures/input.csv</div>
        {evidence.source_csv.trimEnd().split('\n').map((line,i)=><div key={i} style={{fontSize:39,lineHeight:1.8,whiteSpace:'pre',color:i===2?color.ink:color.muted}}>{line}</div>)}
      </div>
      <div style={{width:760}}><div style={{fontSize:26,color:color.muted,marginBottom:48}}>report.csv</div>
        {evidence.output_csv.trimEnd().split('\n').map((line,i)=><div key={i} style={{fontSize:39,lineHeight:1.8,whiteSpace:'pre',color:i===2?color.ink:color.muted}}>{i===2?<>{line.slice(0,line.lastIndexOf(',')+1)}<span style={{position:'relative',color:color.red}}>{line.slice(line.lastIndexOf(',')+1)}<span style={{position:'absolute',left:0,right:0,bottom:-12,height:2,background:color.red,transformOrigin:'left',scale:`${interpolate(frame,[.8*fps,1.4*fps],[0,1],{easing:ease,extrapolateLeft:'clamp',extrapolateRight:'clamp'})} 1`}}/></span></>:line}</div>)}
      </div>
    </div>
    <div style={{position:'absolute',left:112,top:700,fontSize:25,color:color.muted,opacity:interpolate(frame,[2.1*fps,2.4*fps],[0,1],{extrapolateLeft:'clamp',extrapolateRight:'clamp'})}}>same record / different amount</div>
    <Note>Grace: {evidence.proofcli.difference.expected} → {evidence.proofcli.difference.actual}</Note>
  </Frame>;
};
