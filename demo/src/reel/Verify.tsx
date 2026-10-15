import {interpolate,useCurrentFrame} from 'remotion';
import evidence from '../evidence.json';
import {Burst,C,clamp,ease,Label,mono,Stage,Type,useLayout} from './style';

export const Verify = () => {
 const f=useCurrentFrame();const {wide,x,fps}=useLayout();const d=evidence.proofcli.difference;
 return <Stage chapter="DECLARED JSON + CSV ASSERTIONS / BOTH FAILED">
  <div style={{position:'absolute',left:x,top:wide?180:300}}><Label color={C.lime}>03 / PROOFCLI CHECKS THE FILES</Label><Type size={wide?145:148} color={C.paper} style={{marginTop:22}}>EXIT 0.<br/>PROOF FAILED.</Type></div>
  <div style={{position:'absolute',left:wide?1050:x,top:wide?220:750,width:wide?720:830,height:240,perspective:1200}}>
   <div style={{position:'absolute',left:0,top:60,display:'flex',gap:20,translate:`${interpolate(f,[0,1.4*fps],[-340,70],{...clamp,easing:ease})}px 0`,opacity:interpolate(f,[1.3*fps,1.7*fps],[1,0],clamp)}}>
    <div style={{padding:'24px 28px',border:`2px solid ${C.paper}`,fontSize:32,transform:'rotateY(25deg) rotateZ(-7deg)'}}>JSON<br/>{'{ rows }'}</div>
    <div style={{padding:'24px 28px',border:`2px solid ${C.paper}`,fontSize:32,transform:'rotateY(25deg) rotateZ(-7deg)'}}>CSV<br/>1,2,3</div>
   </div>
   <div style={{position:'absolute',right:0,top:0,height:230,width:230,border:`14px solid ${C.lime}`,rotate:`${interpolate(f,[0,1.4*fps],[45,0],{...clamp,easing:ease})}deg`,display:'flex',alignItems:'center',justifyContent:'center',fontFamily:mono,color:C.lime,fontSize:100,scale:interpolate(f,[1.5*fps,1.7*fps,2*fps],[1,1.15,1],clamp)}}>{'≠'}</div>
   <div style={{position:'absolute',left:10,top:50,padding:'12px 25px',border:`8px solid ${C.red}`,background:C.ink,color:C.red,fontFamily:'Anton',fontSize:wide?100:112,rotate:'-9deg',scale:interpolate(f,[1.5*fps,1.8*fps,2*fps],[2.5,.94,1],{...clamp,easing:ease}),opacity:interpolate(f,[1.5*fps,1.6*fps],[0,1],clamp)}}>FAILED</div>
  </div>
  <div style={{position:'absolute',left:wide?1050:x,top:wide?550:1080,width:wide?720:850,opacity:interpolate(f,[2*fps,2.4*fps],[0,1],clamp),translate:`0 ${interpolate(f,[2*fps,2.5*fps],[60,0],{...clamp,easing:ease})}px`}}>
   <Label color={C.muted} style={{fontSize:28}}>MISMATCH AT</Label>
   <Label color={C.paper} style={{fontSize:wide?36:42,marginTop:12}}>{d.path}</Label>
   <div style={{display:'flex',gap:32,marginTop:26,fontFamily:mono,fontSize:wide?42:45}}><span style={{color:C.lime}}>{d.expected}</span><span>≠</span><span style={{color:C.red}}>{d.actual}</span></div>
   <div style={{borderTop:'1px solid #585b50',marginTop:24,paddingTop:18,fontSize:26,color:C.muted}}>exporter exit {evidence.proofcli.child_exit_code} / ProofCLI exit {evidence.proofcli.exit_code}</div>
  </div>
  <div style={{position:'absolute',left:x,top:wide?780:1415,width:wide?820:860,borderLeft:`5px solid ${C.lime}`,paddingLeft:22,fontFamily:mono,fontSize:wide?27:28,color:C.paper}}>$ proofcli run<br/>  examples/export/wrong-value.json</div>
  <Burst at={1.5} color={C.red}/>
  <div style={{position:'absolute',left:wide?x:610,top:wide?650:935,fontSize:wide?30:24,color:C.red,opacity:interpolate(f,[4*fps,4.4*fps],[0,1],clamp),translate:`${interpolate(f,[4*fps,4.4*fps],[100,0],{...clamp,easing:ease})}px 0`}}>× JSON<br/>× CSV</div>
  <div style={{position:'absolute',left:0,right:0,top:interpolate(f,[0,1.5*fps],[180,1600],clamp),height:3,background:C.lime,boxShadow:`0 0 28px ${C.lime}`,opacity:interpolate(f,[0,1.3*fps,1.6*fps],[.5,.5,0],clamp)}}/>
 </Stage>;
};
