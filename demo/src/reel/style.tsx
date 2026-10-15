import React, {useEffect, useState} from 'react';
import {AbsoluteFill, cancelRender, continueRender, delayRender, Easing, interpolate, staticFile, useCurrentFrame, useVideoConfig} from 'remotion';

export const C = {ink:'#161714', paper:'#ECEBE3', lime:'#D5FF3F', red:'#FF5B3B', muted:'#96998D'};
export const display = 'Anton';
export const mono = 'Plex';
export const ease = Easing.bezier(.16,1,.3,1);
export const clamp = {extrapolateLeft:'clamp' as const, extrapolateRight:'clamp' as const};
export const useLayout = () => {const {width:w,height:h,fps}=useVideoConfig(); return {w,h,fps,wide:w>h,x:w>h?110:84,top:w>h?76:166};};

export const Fonts: React.FC = () => {
  const [handle] = useState(()=>delayRender('Load bundled OFL fonts'));
  useEffect(()=>{Promise.all([
    document.fonts.load('100px Anton'), document.fonts.load('40px Plex'),
  ]).then(()=>continueRender(handle)).catch(cancelRender);},[handle]);
  return <style>{`@font-face{font-family:Anton;src:url('${staticFile('fonts/Anton-Regular.ttf')}')}@font-face{font-family:Plex;src:url('${staticFile('fonts/IBMPlexMono-Medium.ttf')}')}*{box-sizing:border-box}`}</style>;
};

export const Type: React.FC<React.PropsWithChildren<{size:number;color?:string;style?:React.CSSProperties}>> = ({children,size,color=C.ink,style}) => <div style={{fontFamily:display,fontSize:size,lineHeight:1.03,letterSpacing:'-.025em',color,...style}}>{children}</div>;
export const Label: React.FC<React.PropsWithChildren<{color?:string;style?:React.CSSProperties}>> = ({children,color=C.ink,style}) => <div style={{fontFamily:mono,fontSize:30,lineHeight:1.45,color,...style}}>{children}</div>;

export const Check: React.FC<{size:number;color?:string}> = ({size,color=C.ink}) => <svg width={size} height={size} viewBox="0 0 100 100" fill="none"><path d="M18 52L40 74L83 26" stroke={color} strokeWidth="12" strokeLinecap="square"/></svg>;

export const Burst: React.FC<{at:number;color?:string;size?:number}> = ({at,color=C.red,size=780}) => {
 const f=useCurrentFrame(); const {fps}=useVideoConfig(); const p=interpolate(f,[at*fps,(at+.6)*fps],[0,1],clamp);
 return <svg width={size} height={size} viewBox="0 0 600 600" style={{position:'absolute',left:'50%',top:'50%',translate:'-50% -50%',opacity:1-p,pointerEvents:'none'}}>{Array.from({length:16},(_,i)=>{const a=i*Math.PI/8;return <line key={i} x1={300+Math.cos(a)*(80+p*200)} y1={300+Math.sin(a)*(80+p*200)} x2={300+Math.cos(a)*(140+p*210)} y2={300+Math.sin(a)*(140+p*210)} stroke={color} strokeWidth={6*(1-p)}/>;})}</svg>;
};

export const Stage: React.FC<React.PropsWithChildren<{bg?:string;dark?:boolean;chapter?:string}>> = ({children,bg=C.ink,dark=true,chapter='REAL COMMANDS / ACTUAL RESULTS'}) => {
 const {x,top,w,h,wide}=useLayout(); const f=useCurrentFrame();
 return <AbsoluteFill style={{background:bg,overflow:'hidden',color:dark?C.paper:C.ink,fontFamily:mono}}>
  <Fonts/>
  <div style={{position:'absolute',inset:0,opacity:.075,backgroundImage:`linear-gradient(${dark?C.paper:C.ink} 1px,transparent 1px),linear-gradient(90deg,${dark?C.paper:C.ink} 1px,transparent 1px)`,backgroundSize:'90px 90px',backgroundPosition:`${f*.3}px 0`}}/>
  {children}
  <div style={{position:'absolute',left:x,top,right:x,display:'flex',justifyContent:'space-between',alignItems:'center',color:dark?C.paper:C.ink}}>
   <div style={{display:'flex',alignItems:'center',gap:18,fontSize:wide?32:31}}><span style={{background:dark?C.lime:C.ink,color:dark?C.ink:bg,width:44,height:44,display:'inline-flex',justifyContent:'center',alignItems:'center',fontFamily:display,fontSize:32}}>P</span>bk1202/proofcli</div>
   <span style={{fontSize:22,opacity:.65}}>{wide?'OUTPUT > EXIT CODE':'// 01'}</span>
  </div>
  <div style={{position:'absolute',left:x,top:wide?h-64:1564,right:x,fontSize:wide?22:23,letterSpacing:1,color:dark?C.paper:C.ink,opacity:.6,borderTop:`1px solid ${dark?C.paper:C.ink}`,paddingTop:18}}>{chapter}</div>
  <div style={{position:'absolute',left:0,bottom:0,height:8,width:w,background:dark?C.lime:C.ink}}/>
 </AbsoluteFill>;
};
