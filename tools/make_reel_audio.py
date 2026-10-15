"""Generate the demo's original, deterministic sound bed using the standard library.

No samples, external services, or downloaded music. Times match the authored cuts.
The WAV is a build artifact, not a Python package dependency.
"""

from array import array
import math
from pathlib import Path
import random
import sys
import wave


RATE = 48000
DURATION = 30
ROOT = Path(__file__).resolve().parents[1]


def main():
    rng = random.Random(1202)
    mix = array("d", [0.0]) * (RATE * DURATION * 2)

    def add(start, duration, sample, gain=1.0, pan=0.0):
        offset = round(start * RATE)
        for i in range(round(duration * RATE)):
            index = offset + i
            if 0 <= index < RATE * DURATION:
                value = sample(i / RATE) * gain
                mix[index * 2] += value * math.sqrt((1 - pan) / 2)
                mix[index * 2 + 1] += value * math.sqrt((1 + pan) / 2)

    def kick(t):
        return math.sin(2 * math.pi * (47*t + 76*.026*(1-math.exp(-t/.026)))) * math.exp(-t*13)

    def hat(t):
        return rng.uniform(-1, 1) * math.exp(-t*180)

    def snare(t):
        return (rng.uniform(-1, 1)*.7 + math.sin(2*math.pi*180*t)*.3)*math.exp(-t*30)

    def impact(t):
        return (math.sin(2*math.pi*(35*t+80*.03*(1-math.exp(-t/.03))))*.8 + rng.uniform(-1,1)*math.exp(-t*35)*.2)*math.exp(-t*6)

    def whoosh(t):
        envelope = math.sin(math.pi*t/.4)**2
        return (rng.uniform(-1,1)*.6 + math.sin(2*math.pi*(400*t+2400*t*t))*.4)*envelope

    # Half-second pulse; silence before each impact makes the scene changes land.
    for beat in range(59):
        time = beat * .5
        if any(cut-.35 < time < cut for cut in (3,7,12,19,25)):
            continue
        add(time, .36, kick, .42)
        if beat % 2:
            add(time, .2, snare, .17)
        add(time+.25, .065, hat, .09, -.35 if beat%2 else .35)
        note = [55,55,65.406,49][(beat//4)%4]
        add(time, .34, lambda t,n=note: (math.sin(2*math.pi*n*t)+.18*math.sin(4*math.pi*n*t))*math.exp(-t*10)*min(1,t/.008), .19)

    for time in (.85,3,7,7.8,12,13.5,19,25):
        add(time, .8, impact, .68)
        if time >= 3:
            add(time-.4, .4, whoosh, .16, -.15)
    # A two-note resolved tag, rather than a stock notification sound.
    for time,note in ((26.0,440),(26.18,659.255)):
        add(time,1.5,lambda t,n=note: math.sin(2*math.pi*n*t)*math.exp(-t*4)*min(1,t/.006),.15,.2)

    peak = max(abs(v) for v in mix)
    pcm = array("h")
    for i,value in enumerate(mix):
        time = i/(RATE*2)
        fade = min(1,time/.012,(DURATION-time)/.6)
        pcm.append(round(value / peak * .79 * max(0,fade) * 32767))
    if sys.byteorder != "little":
        pcm.byteswap()
    target = ROOT / "demo/public/reel-soundtrack.wav"
    target.parent.mkdir(parents=True,exist_ok=True)
    with wave.open(str(target),"wb") as out:
        out.setnchannels(2)
        out.setsampwidth(2)
        out.setframerate(RATE)
        out.writeframes(pcm.tobytes())
    print(f"Generated {target.name}: {DURATION}s / {RATE} Hz / stereo PCM16")


if __name__ == "__main__":
    main()
