#!/usr/bin/env python3
"""
Locus Task Handler
Operations: create, complete, defer tasks
Usage:
  python3 task.py create "Task title" [faction] [difficulty]
  python3 task.py complete <task_id>
  python3 task.py defer <task_id> [reason]
"""

import sys
import json
import os
import urllib.request
import urllib.error

LOCUS_API_URL = os.environ.get("LOCUS_API_URL", "http://locus-api:8000")


def create_task(title, faction=None, difficulty=None):
    payload = {"title": title}
    if faction:
        payload["faction"] = faction
    if difficulty:
        payload["difficulty"] = int(difficulty)

    url = f"{LOCUS_API_URL}/api/v1/tasks"
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url, data=data, headers={"Content-Type": "application/json"}, method="POST"
    )
    with urllib.request.urlopen(req, timeout=15) as resp:
        return json.loads(resp.read().decode("utf-8"))


def complete_task(task_id):
    url = f"{LOCUS_API_URL}/api/v1/tasks/{task_id}/complete"
    req = urllib.request.Request(
        url, data=b"", headers={"Content-Type": "application/json"}, method="POST"
    )
    with urllib.request.urlopen(req, timeout=15) as resp:
        return json.loads(resp.read().decode("utf-8"))


def defer_task(task_id, reason=None):
    url = f"{LOCUS_API_URL}/api/v1/tasks/{task_id}/defer"
    payload = {}
    if reason:
        payload["reason"] = reason
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url, data=data, headers={"Content-Type": "application/json"}, method="POST"
    )
    with urllib.request.urlopen(req, timeout=15) as resp:
        return json.loads(resp.read().decode("utf-8"))


def main():
    if len(sys.argv) < 3:
        print("Usage:")
        print('  task.py create "Task title" [faction] [difficulty]')
        print("  task.py complete <task_id>")
        print("  task.py defer <task_id> [reason]")
        sys.exit(1)

    action = sys.argv[1].lower()

    try:
        if action == "create":
            title = sys.argv[2]
            faction = sys.argv[3] if len(sys.argv) > 3 else None
            difficulty = sys.argv[4] if len(sys.argv) > 4 else None
            result = create_task(title, faction, difficulty)
        elif action == "complete":
            task_id = sys.argv[2]
            result = complete_task(task_id)
        elif action == "defer":
            task_id = sys.argv[2]
            reason = sys.argv[3] if len(sys.argv) > 3 else None
            result = defer_task(task_id, reason)
        else:
            print(f"Unknown action: {action}")
            sys.exit(1)

        print(json.dumps(result, indent=2))
    except urllib.error.HTTPError as e:
        print(f"Error {e.code}: {e.read().decode('utf-8', errors='replace')}")
        sys.exit(1)
    except urllib.error.URLError as e:
        print(f"Connection error: {e.reason}")
        sys.exit(1)


if __name__ == "__main__":
    main()
