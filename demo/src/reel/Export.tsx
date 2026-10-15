import {interpolate,useCurrentFrame} from 'remotion';
import evidence from '../evidence.json';
import {C,clamp,ease,Label,mono,Stage,Type,useLayout} from './style';

export const Export = () => {
 const f=useCurrentFrame();const {wide,x,fps}=useLayout();
 const rows=evidence.output_csv.trim().split('\n').map(r=>r.split(','));
 return <Stage bg={C.paper} dark={false} chapter="ACTUAL EXPORT / report.csv">
  <div style={{position:'absolute',left:x,top:wide?260:315,width:wide?690:900}}><Label>01 / THE FALSE SUCCESS</Label><Type size={wide?120:130} style={{marginTop:24}}>“EXPORT<br/>COMPLETE.”</Type><Label style={{fontSize:wide?34:36,marginTop:30}}>Three rows. Exit 0.<br/>One wrong amount.</Label></div>
  <div style={{position:'absolute',left:wide?920:112,top:wide?250:950,width:wide?850:840,height:wide?530:460,perspective:1600,transformOrigin:'70% 66%',scale:interpolate(f,[3.45*fps,4*fps],[1,3.5],{...clamp,easing:ease}),translate:`${interpolate(f,[0,.8*fps],[wide?600:0,0],{...clamp,easing:ease})}px ${interpolate(f,[0,.8*fps],[wide?0:450,0],{...clamp,easing:ease})}px`}}>
   <div style={{position:'absolute',inset:0,background:C.lime,transform:'translate(30px,32px) rotate(6deg)',border:`2px solid ${C.ink}`}}/>
   <div style={{position:'absolute',inset:0,background:C.paper,border:`3px solid ${C.ink}`,padding:'28px 30px',boxShadow:'15px 24px 0 #161714',transform:`rotateY(${interpolate(f,[0,4*fps],[-24,3],{...clamp,easing:ease})}deg) rotateZ(${interpolate(f,[0,4*fps],[-9,-2],clamp)}deg)`}}>
    <div style={{display:'flex',justifyContent:'space-between',borderBottom:`2px solid ${C.ink}`,paddingBottom:20,marginBottom:22,fontFamily:mono,fontSize:28}}><span>report.csv</span><span>3 RECORDS ↗</span></div>
    {rows.map((row,i)=><div key={i} style={{display:'grid',gridTemplateColumns:'1fr 2.3fr 2.3fr',padding:'14px 12px',fontFamily:mono,fontSize:wide?39:38,background:i===2?C.red:undefined,borderBottom:i<3?'1px solid #b4b5aa':undefined,clipPath:`inset(0 ${interpolate(f,[i*.12*fps,(i*.12+.5)*fps],[100,0],{...clamp,easing:ease})}% 0 0)`}}>{row.map((cell,j)=><span key={j}>{cell}</span>)}</div>)}
    <div style={{position:'absolute',right:-30,top:wide?298:295,background:C.ink,color:C.lime,padding:'8px 18px',fontSize:24,rotate:'-5deg',opacity:interpolate(f,[2*fps,2.2*fps],[0,1],clamp)}}>THERE IT IS.</div>
   </div>
  </div>
 </Stage>;
};
