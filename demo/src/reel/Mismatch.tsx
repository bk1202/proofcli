import {interpolate,useCurrentFrame} from 'remotion';
import evidence from '../evidence.json';
import {Burst,C,clamp,ease,Label,Stage,Type,useLayout} from './style';

export const Mismatch = () => {
 const f=useCurrentFrame();const {wide,x,w,fps}=useLayout();const d=evidence.proofcli.difference;
 return <Stage bg={C.lime} dark={false} chapter="SAME ROW / WRONG AMOUNT">
  <div style={{position:'absolute',left:x,top:wide?185:305}}><Label>02 / ZOOM IN</Label><Type size={wide?90:104} style={{marginTop:18}}>GRACE’S AMOUNT.</Type></div>
  <div style={{position:'absolute',left:x,top:wide?410:570,width:wide?750:900}}>
   <Label style={{fontSize:wide?34:36}}>EXPECTED / FIXTURE</Label>
   <Type size={wide?280:230} style={{marginTop:15,translate:`${interpolate(f,[0,.5*fps],[-500,0],{...clamp,easing:ease})}px 0`}}>{d.expected}</Type>
  </div>
  <div style={{position:'absolute',left:wide?1035:x,top:wide?410:1030,width:wide?800:900}}>
   <Label style={{fontSize:wide?34:36}}>ACTUAL / EXPORTED FILE</Label>
   <Type size={wide?270:225} color={C.paper} style={{position:'relative',marginTop:15,zIndex:1,background:C.ink,padding:'12px 18px 20px',width:'fit-content',translate:`${interpolate(f,[.65*fps,1.15*fps],[600,0],{...clamp,easing:ease})}px 0`}}>{d.actual}</Type>
  </div>
  <div style={{position:'absolute',left:wide?885:470,top:wide?540:902,fontSize:wide?100:90,rotate:wide?'0deg':'90deg',scale:interpolate(f,[.4*fps,.65*fps],[0,1],{...clamp,easing:ease})}}>→</div>
  <div style={{position:'absolute',left:x,top:wide?920:1490,fontSize:wide?32:28,borderLeft:`6px solid ${C.ink}`,paddingLeft:22}}>id: {evidence.record.id} / customer: {evidence.record.customer}</div>
  <Burst at={.8} color={C.ink} size={w}/>
  <div style={{position:'absolute',left:0,top:wide?790:1360,width:w*1.2,background:C.red,color:C.ink,fontSize:wide?48:34,padding:'15px 0',textAlign:'center',rotate:'-3deg',translate:`${interpolate(f,[2.8*fps,3.2*fps],[-w*1.5,-70],{...clamp,easing:ease})}px 0`}}>VALUE MISMATCH / VALUE MISMATCH / VALUE MISMATCH</div>
 </Stage>;
};
