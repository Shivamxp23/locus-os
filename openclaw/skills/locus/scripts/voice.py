#!/usr/bin/env python3
"""
Locus Voice Handler
Receives audio file, calls POST /api/v1/log/voice
Usage: python3 voice.py <audio_file_path>
"""

import sys
import json
import os
import urllib.request
import urllib.error
import mimetypes

LOCUS_API_URL = os.environ.get("LOCUS_API_URL", "http://locus-api:8000")


def main():
    if len(sys.argv) < 2:
        print("Usage: voice.py <audio_file_path>")
        sys.exit(1)

    audio_path = sys.argv[1]
    if not os.path.exists(audio_path):
        print(f"Error: File not found: {audio_path}")
        sys.exit(1)

    boundary = "----WebKitFormBoundary7MA4YWxkTrZu0gW"
    content_type = f"multipart/form-data; boundary={boundary}"

    filename = os.path.basename(audio_path)
    mime_type, _ = mimetypes.guess_type(audio_path)
    if not mime_type:
        mime_type = "audio/ogg"

    with open(audio_path, "rb") as f:
        audio_data = f.read()

    body = (
        (
            f"--{boundary}\r\n"
            f'Content-Disposition: form-data; name="file"; filename="{filename}"\r\n'
            f"Content-Type: {mime_type}\r\n\r\n"
        ).encode("utf-8")
        + audio_data
        + f"\r\n--{boundary}--\r\n".encode("utf-8")
    )

    url = f"{LOCUS_API_URL}/api/v1/log/voice"
    req = urllib.request.Request(
        url, data=body, headers={"Content-Type": content_type}, method="POST"
    )

    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            result = json.loads(resp.read().decode("utf-8"))
            print(json.dumps(result, indent=2))
    except urllib.error.HTTPError as e:
        print(f"Error {e.code}: {e.read().decode('utf-8', errors='replace')}")
        sys.exit(1)
    except urllib.error.URLError as e:
        print(f"Connection error: {e.reason}")
        sys.exit(1)


if __name__ == "__main__":
    main()
