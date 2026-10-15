import React from 'react';
import {interpolate,useCurrentFrame} from 'remotion';
import {color,Frame,Title,mono} from './design';
import evidence from './evidence.json';

export const Opening: React.FC = () => {
  const frame=useCurrentFrame();
  return <Frame chapter="01 / THE BUG"><Title>Green CI.<br/><span style={{color:color.red}}>Wrong data.</span></Title>
    <div style={{fontSize:42,color:color.muted,marginBottom:52}}>An exporter silently changes one customer's amount.</div>
    <div style={{display:'flex',gap:34,opacity:interpolate(frame,[25,45],[0,1],{extrapolateLeft:'clamp',extrapolateRight:'clamp'})}}>
      <div style={{background:color.panel,border:'1px solid #2E425F',padding:38,borderRadius:20,flex:1}}>
        <div style={{color:color.muted,fontSize:28,marginBottom:20}}>EXPECTED · GRACE</div><div style={{fontFamily:mono,fontSize:76,color:color.green}}>{evidence.proofcli.difference.expected}</div>
      </div>
      <div style={{background:color.panel,border:'1px solid #74404D',padding:38,borderRadius:20,flex:1}}>
        <div style={{color:color.muted,fontSize:28,marginBottom:20}}>EXPORTED · {evidence.record.customer.toUpperCase()}</div><div style={{fontFamily:mono,fontSize:76,color:color.red}}>{evidence.record.amount}</div>
      </div>
    </div>
  </Frame>;
};
