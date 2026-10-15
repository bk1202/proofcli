"""Check encoded demo deliverables, decode every frame, and write their manifest."""

import argparse
from array import array
import hashlib
import io
import json
import math
from pathlib import Path
import shutil
import struct
import subprocess
import sys
import wave


ROOT = Path(__file__).resolve().parents[1]
MEDIA = {
    "proofcli-instagram-reel-v1.mp4": (1080, 1920),
    "proofcli-landscape-motion-v1.mp4": (1920, 1080),
    "proofcli-instagram-cover-v1.png": (1080, 1920),
    "proofcli-landscape-cover-v1.png": (1920, 1080),
}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--directory", type=Path, default=ROOT / "demo/out")
    parser.add_argument("--ffprobe", default="ffprobe")
    parser.add_argument("--ffmpeg", default="ffmpeg")
    args = parser.parse_args()
    ffprobe = shutil.which(args.ffprobe)
    ffmpeg = shutil.which(args.ffmpeg)
    if not ffprobe or not ffmpeg:
        parser.error("ffprobe and ffmpeg are required to verify the rendered media")
    ffprobe, ffmpeg = str(Path(ffprobe).resolve()), str(Path(ffmpeg).resolve())
    results = {}
    checksums = []
    for name, dimensions in MEDIA.items():
        path = (args.directory / name).resolve(strict=True)
        data = path.read_bytes()
        if path.suffix == ".mp4":
            report = json.loads(subprocess.check_output([
                ffprobe, "-v", "error", "-show_streams", "-show_format", "-of", "json", str(path),
            ], cwd=Path(ffprobe).parent, timeout=30))
            video = [s for s in report["streams"] if s["codec_type"] == "video"]
            audio = [s for s in report["streams"] if s["codec_type"] == "audio"]
            if len(video) != 1 or len(audio) != 1:
                raise ValueError(f"{name}: expected one video and one audio stream")
            v, a = video[0], audio[0]
            if (v["width"], v["height"]) != dimensions or v["codec_name"] != "h264":
                raise ValueError(f"{name}: incorrect resolution or codec")
            if v.get("pix_fmt") != "yuv420p" or v.get("color_space") != "bt709":
                raise ValueError(f"{name}: expected YUV 4:2:0 with explicit BT.709 color metadata")
            if v["nb_frames"] != "900" or v["r_frame_rate"] != "30/1":
                raise ValueError(f"{name}: expected 900 frames at 30 fps")
            if abs(float(report["format"]["duration"]) - 30) > .05:
                raise ValueError(f"{name}: incorrect duration (AAC padding allowed up to 50 ms)")
            if a["codec_name"] != "aac" or a["sample_rate"] != "48000" or a["channels"] != 2:
                raise ValueError(f"{name}: expected 48 kHz stereo AAC")
            subprocess.run([
                ffmpeg, "-v", "error", "-xerror", "-i", str(path),
                "-c:v", "rawvideo", "-c:a", "pcm_s16le", "-f", "null", "-",
            ], cwd=Path(ffmpeg).parent, check=True, timeout=120, capture_output=True)
            decoded = subprocess.check_output([
                ffmpeg, "-v", "error", "-xerror", "-i", str(path), "-vn",
                "-c:a", "pcm_s16le", "-f", "wav", "-",
            ], cwd=Path(ffmpeg).parent, timeout=60)
            with wave.open(io.BytesIO(decoded), "rb") as wav:
                if wav.getsampwidth() != 2 or wav.getnchannels() != 2 or wav.getframerate() != 48000:
                    raise ValueError(f"{name}: unexpected decoded PCM format")
                pcm = wav.readframes(wav.getnframes())
            samples = array("h")
            samples.frombytes(pcm)
            if sys.byteorder != "little":
                samples.byteswap()
            peak = max(abs(value) for value in samples) / 32768
            rms = math.sqrt(sum(value*value for value in samples) / len(samples)) / 32768
            if not .01 < peak < .99 or rms < .005:
                raise ValueError(f"{name}: decoded audio is silent or clips ({peak=}, {rms=})")
            result = {"dimensions": dimensions, "video_frames": 900, "video_seconds": 30,
                      "container_seconds": float(report["format"]["duration"]),
                      "audio": "AAC / 48000 Hz / stereo", "audio_sample_peak_dbfs": round(20*math.log10(peak),2),
                      "audio_rms_dbfs": round(20*math.log10(rms),2), "full_decode": "passed"}
        else:
            if data[:8] != b"\x89PNG\r\n\x1a\n" or data[12:16] != b"IHDR":
                raise ValueError(f"{name}: not a PNG")
            if struct.unpack(">II", data[16:24]) != dimensions:
                raise ValueError(f"{name}: incorrect cover dimensions")
            result = {"dimensions": dimensions}
        digest = hashlib.sha256(data).hexdigest()
        results[name] = {**result, "bytes": len(data), "sha256": digest}
        checksums.append(f"{digest}  {name}\n")
    (args.directory / "proofcli-motion-v1.SHA256SUMS").write_text("".join(checksums), encoding="utf-8")
    (args.directory / "proofcli-motion-v1-verification.json").write_text(
        json.dumps(results, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()
