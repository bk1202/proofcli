import React from 'react';
import {interpolate,useCurrentFrame,useVideoConfig} from 'remotion';
import {color,Frame,Title,Terminal} from './design';
import evidence from './evidence.json';

export const Ordinary: React.FC = () => {
  const frame=useCurrentFrame(); const {fps}=useVideoConfig();
  return <Frame chapter="02 / EXIT CODE ONLY"><Title>The export step passes.</Title>
    <div style={{fontSize:42,color:color.muted,marginBottom:48}}>A CI step that checks only the exit code misses the bug.</div>
    <Terminal title="Exit-code-only CI · command shortened for readability">
      <div style={{color:color.blue}}>$ python export.py input.csv report.json<br/>  --fault wrong-value</div>
      <div style={{marginTop:28,opacity:interpolate(frame,[fps,1.5*fps],[0,1],{extrapolateLeft:'clamp',extrapolateRight:'clamp'})}}>{evidence.ordinary.stdout}</div>
      <div style={{color:color.green,marginTop:28,fontWeight:700,opacity:interpolate(frame,[2*fps,2.3*fps],[0,1],{extrapolateLeft:'clamp',extrapolateRight:'clamp'})}}>EXIT {evidence.ordinary.exit_code} · STEP PASSED</div>
    </Terminal>
    <div style={{marginTop:38,fontSize:36,color:color.muted}}>Valid JSON. Nonempty CSV. Still the wrong amount.</div>
  </Frame>;
};
