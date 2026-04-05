#!/usr/bin/env python3
"""
Locus Query Handler
Routes "what should I do today?" to scheduling endpoint
Usage: python3 query.py [user_id]
"""

import sys
import json
import os
import urllib.request
import urllib.error

LOCUS_API_URL = os.environ.get("LOCUS_API_URL", "http://locus-api:8000")


def main():
    user_id = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("TELEGRAM_OWNER_ID", "")

    url = f"{LOCUS_API_URL}/api/v1/schedule/recommend"
    payload = {"user_id": user_id}
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url, data=data, headers={"Content-Type": "application/json"}, method="POST"
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
