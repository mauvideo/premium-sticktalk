"""Hậu kỳ FFmpeg tách biệt giữa Google và Edge."""

import subprocess
from pathlib import Path

GOOGLE_FILTERS = {
    "tu_nhien": "highpass=f=70,loudnorm=I=-16:TP=-1.5:LRA=8,alimiter=limit=.95",
    "phat_thanh": "highpass=f=70,acompressor=threshold=-20dB:ratio=2.2:attack=15:release=180,loudnorm=I=-15:TP=-1.3:LRA=7,alimiter=limit=.93",
    "noi_luc": "highpass=f=70,equalizer=f=125:t=q:w=1:g=1.5,acompressor=threshold=-21dB:ratio=2:attack=18:release=200,loudnorm=I=-15:TP=-1.2:LRA=7,alimiter=limit=.92",
}
EDGE_FILTERS = {
    "power_plus": "highpass=f=55,equalizer=f=90:t=q:w=1.0:g=5,equalizer=f=180:t=q:w=1.1:g=3,acompressor=threshold=-20dB:ratio=4:attack=8:release=160:makeup=4,alimiter=limit=.89,loudnorm=I=-14:TP=-1:LRA=5",
    "power": "highpass=f=65,equalizer=f=110:t=q:w=1:g=3,acompressor=threshold=-19dB:ratio=3,loudnorm=I=-15:TP=-1.2:LRA=6",
    "mc": "highpass=f=75,acompressor=threshold=-18dB:ratio=2.8,loudnorm=I=-16:TP=-1.5:LRA=7",
    "podcast": "highpass=f=65,acompressor=threshold=-21dB:ratio=2.5,loudnorm=I=-17:TP=-1.5:LRA=7",
    "emotional": "highpass=f=65,acompressor=threshold=-20dB:ratio=2.2,loudnorm=I=-16:TP=-1.5:LRA=8",
    "business": "highpass=f=70,acompressor=threshold=-18dB:ratio=3,loudnorm=I=-15:TP=-1.3:LRA=6",
    "gentle": "highpass=f=85,acompressor=threshold=-20dB:ratio=2,loudnorm=I=-17:TP=-1.5:LRA=8",
}


def postprocess(source: Path, destination: Path, preset) -> None:
    filters = GOOGLE_FILTERS if preset.provider == "google" else EDGE_FILTERS
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(source), "-af",
                    filters[preset.mastering], "-c:a", "libmp3lame", "-b:a", "192k", str(destination)], check=True)
