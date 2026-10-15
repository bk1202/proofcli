import {interpolate,useCurrentFrame} from 'remotion';
import {Burst,C,clamp,display,ease,Label,Stage,Type,useLayout} from './style';
import evidence from '../evidence.json';

export const Hook = () => {
 const f=useCurrentFrame();const {wide,w,x,fps}=useLayout();
 const bad=f>=.85*fps;
 return <Stage bg={bad?C.ink:C.lime} dark={bad} chapter="EXIT-CODE-ONLY CI / BROKEN EXPORTER">
  <div style={{position:'absolute',width:wide?760:680,height:950,right:wide?20:-130,top:wide?95:830,perspective:1000,opacity:bad?.38:.2}}>
   <div style={{position:'absolute',inset:0,transformStyle:'preserve-3d',transform:`rotateX(10deg) rotateY(${interpolate(f,[0,3*fps],[-38,25],clamp)}deg) rotateZ(-12deg)`}}>
    {Array.from({length:8},(_,i)=><div key={i} style={{position:'absolute',inset:0,fontFamily:display,fontSize:wide?900:820,lineHeight:1,color:i===7?(bad?C.red:C.ink):'transparent',WebkitTextStroke:`2px ${bad?C.red:C.ink}`,transform:`translateZ(${i*18}px)`}}>0</div>)}
   </div>
  </div>
  <div style={{position:'absolute',left:x,top:wide?210:350,right:x}}>
   <div style={{overflow:'hidden'}}><Type size={wide?225:190} color={bad?C.paper:C.ink} style={{translate:`0 ${interpolate(f,[0,.35*fps],[30,0],{...clamp,easing:ease})}px`}}>GREEN CI.</Type></div>
   <div style={{overflow:'hidden',marginTop:wide?5:22}}><Type size={wide?225:190} color={C.red} style={{translate:`0 ${interpolate(f,[.85*fps,1.15*fps],[240,0],{...clamp,easing:ease})}px`,rotate:`${interpolate(f,[.85*fps,1.18*fps],[-7,0],clamp)}deg`}}>BAD DATA.</Type></div>
   <Label color={bad?C.paper:C.ink} style={{marginTop:wide?22:70,fontSize:wide?34:40}}>The command succeeded.<br/>The export didn’t.</Label>
  </div>
  <div style={{position:'absolute',left:x,top:wide?840:1190,display:'flex',alignItems:'center',gap:22,opacity:interpolate(f,[1.5*fps,1.8*fps],[0,1],clamp)}}>
   <div style={{background:C.lime,color:C.ink,padding:'12px 24px',fontSize:wide?38:40}}>exit {evidence.ordinary.exit_code}</div>
   <Label color={C.paper} style={{fontSize:wide?30:30}}>≠ correct output</Label>
  </div>
  {bad&&<Burst at={.85} size={w} color={C.red}/>}
 </Stage>;
};
