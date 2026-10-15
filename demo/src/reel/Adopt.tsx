import {interpolate,useCurrentFrame} from 'remotion';
import {C,clamp,ease,Label,mono,Stage,Type,useLayout} from './style';

export const Adopt = () => {
 const f=useCurrentFrame();const {wide,x,fps}=useLayout();
 return <Stage bg={C.paper} dark={false} chapter="VERIFY YOUR CONTRACT / ASSERTIONS DEFINE THE COVERAGE">
  <div style={{position:'absolute',left:x,top:wide?220:310}}><Label>04 / PUT IT IN YOUR WORKFLOW</Label><Type size={wide?150:150} style={{marginTop:30}}>CHECK<br/>THE OUTPUT.</Type><Label style={{fontSize:wide?34:38,marginTop:40}}>Expected records.<br/>Expected columns.<br/>Expected values.</Label></div>
  <div style={{position:'absolute',left:wide?1000:x,top:wide?240:1000,width:wide?800:850,translate:`0 ${interpolate(f,[0,.7*fps],[220,0],{...clamp,easing:ease})}px`}}>
   <div style={{background:C.ink,color:C.paper,padding:'35px 30px',boxShadow:`16px 16px 0 ${C.lime}`}}><Label color={C.lime} style={{fontSize:27,marginBottom:20}}>INSTALL FROM PYPI</Label><div style={{fontFamily:mono,fontSize:wide?32:33,lineHeight:1.5,whiteSpace:'nowrap'}}>$ python -m pip install proofcli</div></div>
   <div style={{marginTop:60,borderTop:`3px solid ${C.ink}`,paddingTop:30,opacity:interpolate(f,[1.6*fps,2*fps],[0,1],clamp)}}><Label style={{fontSize:27,marginBottom:15}}>OR ADD THE GITHUB ACTION</Label><div style={{fontFamily:mono,fontSize:wide?32:33,lineHeight:1.6}}>uses:<br/><span style={{background:C.lime}}>bk1202/proofcli@v0.4.1</span></div></div>
  </div>
 </Stage>;
};
