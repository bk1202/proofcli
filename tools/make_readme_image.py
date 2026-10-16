"""Render the README and social preview graphic from captured demo evidence.

Development-only dependency: Pillow. No network requests or stock assets.
"""
import json
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
evidence = json.loads((ROOT / 'demo/src/evidence.json').read_text())
assert evidence['ordinary']['exit_code'] == 0
assert evidence['proofcli']['exit_code'] == 1
diff = evidence['proofcli']['difference']
assert diff == {'path':'$/rows/1/amount','reason':'value or type differs','expected':'8.25','actual':'999.00'}

S = 2
im = Image.new('RGB', (1280*S, 640*S), '#161714')
d = ImageDraw.Draw(im)
fonts = ROOT/'demo/public/fonts'

def text(x,y,value,size=22,color='#ECEBE3',display=False):
    path=fonts/('Anton-Regular.ttf' if display else 'IBMPlexMono-Medium.ttf')
    font=ImageFont.truetype(str(path),size*S)
    d.text((x*S,y*S),value,font=font,fill=color)

def rect(box,fill,outline=None,width=1):
    d.rectangle(tuple(v*S for v in box),fill=fill,outline=outline,width=width*S)

rect((0,0,1280,7),'#D5FF3F')
text(56,31,'ProofCLI',28,'#D5FF3F',True)
text(865,40,'bk1202/proofcli',21,'#96998D')
text(56,85,'EXIT 0. WRONG EXPORT.',66,display=True)
text(57,180,'Check the files your command actually writes.',25)

rect((56,242,628,460),'#20211D','#41443A')
rect((652,242,1224,460),'#20211D','#D5FF3F',2)
text(80,261,'EXIT-CODE-ONLY CI',21,'#96998D')
text(676,261,'PROOFCLI + A CONTRACT',21,'#D5FF3F')
text(80,308,'Export complete',30,display=True)
text(80,357,'Valid JSON + CSV. Three rows.',19)
text(80,405,'PASS  /  exporter exit 0',22,'#D5FF3F')
text(676,307,diff['path'],24)
text(676,353,'EXPECTED',16,'#96998D')
text(942,353,'ACTUAL',16,'#96998D')
text(676,377,diff['expected'],36,'#D5FF3F',True)
text(942,377,diff['actual'],36,'#FF5B3B',True)
text(676,431,'FAIL  /  ProofCLI exit 1',20,'#FF5B3B')

text(56,494,'REPRODUCE THE FAILURE',16,'#96998D')
text(56,527,'proofcli run examples/export/wrong-value.json',24,'#D5FF3F')
text(56,595,'Actual example results. Declared assertions define what is verified.',16,'#96998D')
out=ROOT/'docs/assets/output-contract.png'
im.save(out,optimize=True)
print(out)
