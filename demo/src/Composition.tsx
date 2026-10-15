import {Composition,Series,useVideoConfig} from 'remotion';
import {Opening} from './Opening';
import {Ordinary} from './Ordinary';
import {Verification} from './Verification';
import {Closing} from './Closing';

const Video = () => {
  const {fps}=useVideoConfig();
  return <Series>
    <Series.Sequence name="Run the broken exporter" durationInFrames={7*fps} premountFor={fps}><Opening/></Series.Sequence>
    <Series.Sequence name="Inspect the actual CSV" durationInFrames={6*fps} premountFor={fps}><Ordinary/></Series.Sequence>
    <Series.Sequence name="ProofCLI detects the mismatch" durationInFrames={11*fps} premountFor={fps}><Verification/></Series.Sequence>
    <Series.Sequence name="Add the action" durationInFrames={6*fps} premountFor={fps}><Closing/></Series.Sequence>
  </Series>;
};
export const MyComposition = () => <>
  <Composition id="ProofCLI" component={Video} durationInFrames={900} fps={30} width={1920} height={1080}/>
  <Composition id="Opening" component={Opening} durationInFrames={210} fps={30} width={1920} height={1080}/>
  <Composition id="ExitCodeOnly" component={Ordinary} durationInFrames={180} fps={30} width={1920} height={1080}/>
  <Composition id="Verification" component={Verification} durationInFrames={330} fps={30} width={1920} height={1080}/>
  <Composition id="AddTheAction" component={Closing} durationInFrames={180} fps={30} width={1920} height={1080}/>
</>;
