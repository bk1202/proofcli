import { MyComposition } from "./Composition";
import {ReelCompositions} from './reel/Reel';

export const RemotionRoot: React.FC = () => {
  return (
    <>
      <MyComposition />
      <ReelCompositions />
    </>
  );
};
