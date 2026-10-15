import {interpolate,useCurrentFrame} from 'remotion';
import {C,clamp,display,ease,Label,Stage,Type,useLayout} from './style';

export const End = () => {
 const f=useCurrentFrame();const {wide,x,w,h,fps}=useLayout();
 return <Stage bg={C.lime} dark={false} chapter="OPEN SOURCE / PYTHON / MIT LICENSE">
  <div style={{position:'absolute',width:wide?1200:1600,height:wide?1200:1600,border:`2px solid ${C.ink}`,borderRadius:'50%',left:wide?1000:200,top:wide?-500:740,opacity:.25,scale:interpolate(f,[0,5*fps],[.6,1.3],clamp)}}/>
  <div style={{position:'absolute',left:wide?1320:620,top:wide?330:1070,width:320,height:320,perspective:1400,opacity:wide?1:.16,translate:`0 ${interpolate(f,[0,5*fps],[60,-30],clamp)}px`}}>
   <div style={{width:320,height:320,transformStyle:'preserve-3d',transform:`rotateX(-18deg) rotateY(${interpolate(f,[0,5*fps],[-34,-18],clamp)}deg) rotateZ(12deg)`}}>
    <div style={{position:'absolute',inset:0,background:C.ink,transform:'translateZ(160px)',color:C.lime,fontFamily:display,fontSize:240,lineHeight:'320px',textAlign:'center'}}>P</div>
    <div style={{position:'absolute',inset:0,border:`3px solid ${C.ink}`,background:C.lime,transform:'rotateY(90deg) translateZ(160px)'}}/>
    <div style={{position:'absolute',inset:0,border:`3px solid ${C.ink}`,background:C.lime,transform:'rotateY(-90deg) translateZ(160px)'}}/>
    <div style={{position:'absolute',inset:0,border:`3px solid ${C.ink}`,background:C.lime,transform:'rotateX(90deg) translateZ(160px)'}}/>
    <div style={{position:'absolute',inset:0,border:`3px solid ${C.ink}`,background:C.lime,transform:'rotateX(-90deg) translateZ(160px)'}}/>
   </div>
  </div>
  <div style={{position:'absolute',left:x,top:wide?200:400,right:x}}>
   <Label style={{fontSize:wide?42:44}}>GET IT ON GITHUB ↗</Label>
   <Type size={wide?100:140} style={{marginTop:wide?30:65,translate:`${interpolate(f,[0,.6*fps],[-w,0],{...clamp,easing:ease})}px 0`}}>bk1202/</Type>
   <div style={{overflow:'hidden'}}><Type size={wide?260:232} style={{translate:`0 ${interpolate(f,[.2*fps,.9*fps],[350,0],{...clamp,easing:ease})}px`}}>proofcli</Type></div>
   <Label style={{marginTop:wide?50:100,fontSize:wide?36:32,borderTop:`3px solid ${C.ink}`,paddingTop:30}}>github.com/bk1202/proofcli</Label>
  </div>
  <div style={{position:'absolute',left:x,top:wide?h-190:1380,fontSize:wide?32:36}}>Exit 0 is only the beginning.</div>
 </Stage>;
};
