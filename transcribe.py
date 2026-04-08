#!/usr/bin/env python3
"""Transcribe an audio file using OpenAI Whisper API."""

import sys
import os
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv(Path(__file__).parent / ".env")


def transcribe(audio_path: str) -> str:
    client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
    with open(audio_path, "rb") as f:
        result = client.audio.transcriptions.create(model="whisper-1", file=f)
    return result.text


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: transcribe.py <audio_file>", file=sys.stderr)
        sys.exit(1)
    print(transcribe(sys.argv[1]))
