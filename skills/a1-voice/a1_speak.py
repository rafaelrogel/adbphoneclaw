#!/usr/bin/env python3
"""A1 Voice: edge-tts (Antonio PT-BR) + heavy robotic ffmpeg filter.
Usage: a1_speak.py "text to speak" [output.ogg]
Generates a robotic Antonio voice note ready for WhatsApp.
"""
import asyncio
import os
import subprocess
import sys
import tempfile

VOICE = "pt-BR-AntonioNeural"
# Robotic filter: tremolo (AM), bandpass, slight ring-mod feel via chorus+vibrato
ROBOT_FILTER = (
    "highpass=f=200,"
    "lowpass=f=4800,"
    "tremolo=f=32:d=0.6,"
    "vibrato=f=8:d=0.4,"
    "aecho=0.6:0.6:15|23:0.35|0.25"
)


async def generate(text: str, out_path: str):
    import edge_tts
    with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tmp:
        tmp_path = tmp.name
    try:
        comm = edge_tts.Communicate(text, VOICE)
        await comm.save(tmp_path)
        subprocess.run(
            ["ffmpeg", "-y", "-i", tmp_path, "-af", ROBOT_FILTER, out_path],
            check=True,
            capture_output=True,
        )
    finally:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)


def main():
    if len(sys.argv) < 2:
        print("Usage: a1_speak.py 'text' [output.ogg]", file=sys.stderr)
        sys.exit(1)
    text = sys.argv[1]
    out = sys.argv[2] if len(sys.argv) > 2 else "/home/rafael/.openclaw/workspace/skills/a1-voice/a1_robot.ogg"
    asyncio.run(generate(text, out))
    print(out)


if __name__ == "__main__":
    main()
