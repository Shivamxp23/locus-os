#!/usr/bin/env python3
"""
Locus Morning Log Handler
Parses "log E M S ST T" and calls POST /api/v1/log/morning
Usage: python3 morning_log.py <energy> <mood> <sleep> <stress> [time_available]
"""

import sys
import json
import os
import urllib.request
import urllib.error

LOCUS_API_URL = os.environ.get("LOCUS_API_URL", "http://locus-api:8000")


def main():
    if len(sys.argv) < 5:
        print("Usage: morning_log.py <energy> <mood> <sleep> <stress> [time_available]")
        print("Example: morning_log.py 7 6 8 3 5")
        sys.exit(1)

    try:
        energy = int(sys.argv[1])
        mood = int(sys.argv[2])
        sleep = int(sys.argv[3])
        stress = int(sys.argv[4])
        time_available = float(sys.argv[5]) if len(sys.argv) > 5 else None
    except ValueError as e:
        print(f"Error: All metrics must be numbers. {e}")
        sys.exit(1)

    payload = {
        "energy": energy,
        "mood": mood,
        "sleep": sleep,
        "stress": stress,
    }
    if time_available is not None:
        payload["time_available"] = time_available

    url = f"{LOCUS_API_URL}/api/v1/log/morning"
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
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
