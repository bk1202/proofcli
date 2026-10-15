import {Audio} from '@remotion/media';
import {Composition,Folder,Series,Still,staticFile,useVideoConfig} from 'remotion';
import {Hook} from './Hook';
import {Export} from './Export';
import {Mismatch} from './Mismatch';
import {Verify} from './Verify';
import {Adopt} from './Adopt';
import {End} from './End';
import {C,Label,Stage,Type,useLayout} from './style';

export const Reel = () => {
 const {fps}=useVideoConfig();
 return <>
  <Series>
   <Series.Sequence name="Green CI. Bad data." durationInFrames={3*fps} premountFor={fps}><Hook/></Series.Sequence>
   <Series.Sequence name="The real broken export" durationInFrames={4*fps} premountFor={fps}><Export/></Series.Sequence>
   <Series.Sequence name="Isolate the wrong value" durationInFrames={5*fps} premountFor={fps}><Mismatch/></Series.Sequence>
   <Series.Sequence name="Verify the actual files" durationInFrames={7*fps} premountFor={fps}><Verify/></Series.Sequence>
   <Series.Sequence name="Install and add to CI" durationInFrames={6*fps} premountFor={fps}><Adopt/></Series.Sequence>
   <Series.Sequence name="Get bk1202/proofcli" durationInFrames={5*fps} premountFor={fps}><End/></Series.Sequence>
  </Series>
  <Audio src={staticFile('reel-soundtrack.wav')} premountFor={fps}/>
 </>;
};

const Cover = () => {const {wide,x}=useLayout();return <Stage chapter="A REAL BROKEN EXPORT / CAUGHT BY PROOFCLI">
 <div style={{position:'absolute',left:x,top:wide?220:500}}><Type size={wide?210:188} color={C.paper}>GREEN CI.</Type><Type size={wide?210:188} color={C.red}>BAD DATA.</Type><Label color={C.lime} style={{fontSize:wide?50:58,marginTop:70}}>8.25 → 999.00</Label><Label color={C.paper} style={{fontSize:36,marginTop:45}}>Exit 0 didn’t catch it.<br/>ProofCLI did.</Label></div>
 </Stage>;};

export const ReelCompositions = () => <>
 <Composition id="InstagramReel" component={Reel} width={1080} height={1920} fps={30} durationInFrames={900}/>
 <Composition id="LandscapeMotion" component={Reel} width={1920} height={1080} fps={30} durationInFrames={900}/>
 <Still id="ReelCover" component={Cover} width={1080} height={1920}/>
 <Still id="LandscapeCover" component={Cover} width={1920} height={1080}/>
 <Folder name="Reel-scenes">
  <Composition id="ReelHook" component={Hook} width={1080} height={1920} fps={30} durationInFrames={90}/>
  <Composition id="ReelExport" component={Export} width={1080} height={1920} fps={30} durationInFrames={120}/>
  <Composition id="ReelMismatch" component={Mismatch} width={1080} height={1920} fps={30} durationInFrames={150}/>
  <Composition id="ReelVerify" component={Verify} width={1080} height={1920} fps={30} durationInFrames={210}/>
  <Composition id="ReelAdopt" component={Adopt} width={1080} height={1920} fps={30} durationInFrames={180}/>
  <Composition id="ReelEnd" component={End} width={1080} height={1920} fps={30} durationInFrames={150}/>
 </Folder>
</>;
