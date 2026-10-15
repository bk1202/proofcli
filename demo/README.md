# ProofCLI motion demos

Two separately composed 30-second layouts: `InstagramReel` (1080 × 1920) and
`LandscapeMotion` (1920 × 1080), at 30 fps. The older terminal walkthrough remains
available as `ProofCLI`. The new cuts use kinetic type, a moving CSV sheet,
dimensional graphics, and a sound bed generated from scratch.

## Rebuild

From the repository root, with Python and Node.js installed:

```sh
python tools/capture_demo.py
python tools/make_reel_audio.py
cd demo
npm ci
npm run dev
```

Open `InstagramReel` or `LandscapeMotion` in Studio. Each scene also has a standalone
timeline in `Reel-scenes`. The landscape cut repositions and resizes the scene
elements; it does not crop a vertical video.

```sh
npm run lint
npm run reel
npm run landscape
npm run reel-cover
npm run landscape-cover
cd ..
python tools/verify_demo_media.py
```

The verification step needs `ffmpeg` and `ffprobe` on PATH, or explicit paths via
`--ffmpeg` and `--ffprobe`. It decodes both videos, checks their streams and frame
counts, checks cover dimensions, and writes a dedicated SHA-256 manifest.
AAC framing can add a few milliseconds to the container duration; video duration
is exactly 900 frames / 30 fps.

## Evidence and presentation

`capture_demo.py` runs the actual broken exporter and ProofCLI in a fresh temporary
directory. It checks exit codes, captures the CSV, and checks the reported mismatch.
CI reruns it and rejects any difference from `src/evidence.json`.

The motion graphics are an edited explanation of that captured run, rather than a
screen recording. The large values, CSV rows, mismatch path, and exit codes come
from the capture. Installation and Action snippets are instructions, not fabricated
execution logs. The Action snippet shows a reference, not a complete workflow;
the root README has the full example. The CI comparison is specifically with an
exit-code-only check. pytest and shell scripts can also assert file contents.

The text is readable without sound. The vertical layout leaves generous margins
for social-app controls; placement varies by app and device. No social posting is
part of the build or release workflow.

## Assets and rights

- Anton and IBM Plex Mono are bundled under their respective OFL licenses in
  `public/fonts/`; no font network requests are needed during rendering.
- `tools/make_reel_audio.py` generates the original deterministic synth/percussion
  soundtrack using Python's standard library. No stock recording or music is used.
- The generated WAV and rendered media are ignored by Git. Release files have
  distinct names; the workflow does not overwrite package assets or older demos.

Changes to a published cut should use new versioned filenames in the scripts,
verifier and workflow. Publication deliberately fails if a filename already exists.
