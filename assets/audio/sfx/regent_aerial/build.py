"""Rebuild the cinematic's recorded bird effects offline (requires ffmpeg).

The unmodified CC0 source WAVs and their attribution are shipped alongside
this script. Neither a network connection nor additional Python packages
are required.
"""

from pathlib import Path
import subprocess


ROOT = Path(__file__).resolve().parent
EFFECTS = (
    (
        "548118__basedmedia__hawk-2.wav",
        "hawk_call.ogg",
        "atrim=start=0:end=1.9,asetpts=PTS-STARTPTS,"
        "highpass=f=250,lowpass=f=11000,volume=1.5,"
        "afade=t=in:st=0:d=0.008,afade=t=out:st=1.81:d=0.09",
    ),
    (
        "389634__stubb__wing-flap-1.wav",
        "wing_flap.ogg",
        "atrim=start=0.13:end=0.43,asetpts=PTS-STARTPTS,"
        "highpass=f=160,lowpass=f=8000,volume=2,"
        "afade=t=in:st=0:d=0.01,afade=t=out:st=0.27:d=0.03",
    ),
)


def main():
    for original, output, filters in EFFECTS:
        subprocess.run(
            [
                "ffmpeg", "-y", "-v", "error",
                "-i", str(ROOT / "source" / original),
                "-map", "0:a:0", "-map_metadata", "-1",
                "-ac", "1", "-ar", "48000", "-af", filters,
                "-c:a", "libvorbis", "-q:a", "6",
                "-metadata", "license=CC0-1.0",
                str(ROOT / output),
            ],
            check=True,
        )


if __name__ == "__main__":
    main()
