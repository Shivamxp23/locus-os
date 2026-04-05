#!/usr/bin/env python3
"""
Locus Vault Handler
RAG search, calls POST /api/v1/vault/search
Usage: python3 vault.py "search query" [top_k]
"""

import sys
import json
import os
import urllib.request
import urllib.error

LOCUS_API_URL = os.environ.get("LOCUS_API_URL", "http://locus-api:8000")


def main():
    if len(sys.argv) < 2:
        print('Usage: vault.py "search query" [top_k]')
        sys.exit(1)

    query = sys.argv[1]
    top_k = int(sys.argv[2]) if len(sys.argv) > 2 else 5

    url = f"{LOCUS_API_URL}/api/v1/vault/search"
    payload = {"query": query, "top_k": top_k}
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
