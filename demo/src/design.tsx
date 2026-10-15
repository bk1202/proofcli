import React from 'react';
import {AbsoluteFill, interpolate, useCurrentFrame} from 'remotion';

export const color = {bg: '#0A101C', panel: '#121E30', ink: '#F4F7FC', muted: '#A1B2CB', blue: '#68ACFF', green: '#61E9AF', red: '#FF8C9A'};
export const mono = 'Consolas, "DejaVu Sans Mono", monospace';
export const Frame: React.FC<{chapter: string; children: React.ReactNode}> = ({chapter, children}) => {
  const frame = useCurrentFrame();
  return <AbsoluteFill style={{background: color.bg, color: color.ink, fontFamily: '"Segoe UI", Arial, sans-serif', padding: '72px 112px',
    opacity: interpolate(frame,[0,10],[0,1],{extrapolateLeft:'clamp',extrapolateRight:'clamp'})}}>
    <div style={{position:'absolute',width:780,height:780,borderRadius:'50%',background:'#153654',filter:'blur(220px)',right:-300,top:-500,opacity:.5}}/>
    <div style={{display:'flex',justifyContent:'space-between',fontSize:28,letterSpacing:3,color:color.muted,marginBottom:60}}>
      <span style={{color:color.blue,fontWeight:700}}>PROOFCLI</span><span>{chapter}</span>
    </div>
    <div style={{position:'relative'}}>{children}</div>
    <div style={{position:'absolute',bottom:54,left:112,right:112,display:'flex',justifyContent:'space-between',fontSize:24,color:color.muted}}>
      <span>Actual command results · edited for a 30-second walkthrough</span><span>github.com/bk1202/proofcli</span>
    </div>
  </AbsoluteFill>;
};
export const Title: React.FC<{children: React.ReactNode}> = ({children}) => <div style={{fontSize:96,fontWeight:700,lineHeight:1.08,letterSpacing:-3,marginBottom:30}}>{children}</div>;
export const Terminal: React.FC<{title: string; children: React.ReactNode}> = ({title, children}) => <div style={{background:color.panel,border:'1px solid #2E425F',borderRadius:24,overflow:'hidden',boxShadow:'0 24px 64px #0005'}}>
  <div style={{padding:'22px 36px',borderBottom:'1px solid #2E425F',fontSize:26,color:color.muted,display:'flex',gap:12,alignItems:'center'}}>
    <span style={{width:12,height:12,borderRadius:10,background:color.red}}/><span style={{width:12,height:12,borderRadius:10,background:'#FFD08C'}}/><span style={{width:12,height:12,borderRadius:10,background:color.green}}/><span style={{marginLeft:16}}>{title}</span>
  </div>
  <div style={{padding:'34px 40px',fontFamily:mono,fontSize:32,lineHeight:1.65,whiteSpace:'pre-wrap'}}>{children}</div>
</div>;
