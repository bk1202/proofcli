import React from 'react';
import {interpolate,useCurrentFrame,useVideoConfig} from 'remotion';
import {color,Frame,Title,Terminal,mono} from './design';
import evidence from './evidence.json';

export const Verification: React.FC = () => {
  const frame=useCurrentFrame(); const {fps}=useVideoConfig();
  return <Frame chapter="03 / CHECK THE RECORDS"><Title>ProofCLI catches it.</Title>
    <div style={{fontSize:42,color:color.muted,marginBottom:42}}>The contract checks the exported records, not the success message.</div>
    <Terminal title="ProofCLI · selected fields from the actual JSON report">
      <div style={{color:color.blue}}>$ proofcli run examples/export/wrong-value.json</div>
      <div style={{marginTop:22,color:color.red,fontWeight:700}}>FAILED · child exit {evidence.proofcli.child_exit_code} · ProofCLI exit {evidence.proofcli.exit_code}</div>
      <div style={{marginTop:18}}>path:     {evidence.proofcli.difference.path}</div>
      <div style={{color:color.green}}>expected: "{evidence.proofcli.difference.expected}"</div>
      <div style={{color:color.red}}>actual:   "{evidence.proofcli.difference.actual}"</div>
    </Terminal>
    <div style={{marginTop:36,fontFamily:mono,fontSize:34,color:color.muted,opacity:interpolate(frame,[3*fps,3.4*fps],[0,1],{extrapolateLeft:'clamp',extrapolateRight:'clamp'})}}>JSON and CSV both fail at the same field.</div>
  </Frame>;
};
