import React from 'react';
import {color,Frame,Title,Terminal} from './design';

export const Closing: React.FC = () => <Frame chapter="04 / ADD THE CHECK"><Title>Make the output<br/>part of the contract.</Title>
  <div style={{fontSize:42,color:color.muted,marginBottom:38}}>One workflow step. Python setup included.</div>
  <Terminal title="Your GitHub Actions workflow">
    <div><span style={{color:color.blue}}>- uses:</span> bk1202/proofcli@v0.4.0<br/><span style={{color:color.blue}}>  with:</span><br/>    spec: tests/export-contract.json</div>
  </Terminal>
  <div style={{marginTop:36,fontSize:32,color:color.muted}}>A pass covers the assertions you declare. Write them carefully.</div>
</Frame>;
