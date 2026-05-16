#!/usr/bin/env python3
"""
One-time authentication setup for Locus Chat Vault.

Usage:
    python setup_auth.py <platform> <account_slug>

Example:
    python setup_auth.py claude soni82003

A headed browser opens so you can log in manually (2FA, SSO, CAPTCHA, etc.).
The session is saved to /vault/.browser_profiles/<platform>_<account>/.
"""

import argparse
import os
import sys
import time

from playwright.sync_api import sync_playwright

# ---------------------------------------------------------------------------
# Platform definitions
# ---------------------------------------------------------------------------
PLATFORMS = {
    "claude": {
        "login_url": "https://claude.ai",
        "success_pattern": "**/new**",
    },
    "chatgpt": {
        "login_url": "https://chatgpt.com",
        "success_pattern": "chatgpt.com/**",
    },
    "gemini": {
        "login_url": "https://gemini.google.com",
        "success_pattern": "gemini.google.com/app**",
    },
    "aistudio": {
        "login_url": "https://aistudio.google.com",
        "success_pattern": "aistudio.google.com/prompts**",
    },
    "perplexity": {
        "login_url": "https://perplexity.ai",
        "success_pattern": "perplexity.ai/**",
    },
    "flow": {
        "login_url": "https://flow.microsoft.com",
        "success_pattern": "flow.microsoft.com/**",
    },
}

TIMEOUT_MS = 300_000  # 5 minutes


def main():
    parser = argparse.ArgumentParser(description="Authenticate a platform/account combo")
    parser.add_argument("platform", choices=list(PLATFORMS.keys()), help="Platform name")
    parser.add_argument("account", help="Account slug (e.g. soni82003)")
    args = parser.parse_args()

    platform = args.platform
    account = args.account
    cfg = PLATFORMS[platform]

    profiles_dir = os.environ.get("PROFILES_DIR", "/vault/.browser_profiles")
    profile_path = os.path.join(profiles_dir, f"{platform}_{account}")
    os.makedirs(profile_path, exist_ok=True)

    print(f"\n[setup_auth] Platform: {platform} | Account: {account}")
    print(f"[setup_auth] Profile dir: {profile_path}")
    print(f"[setup_auth] Login URL:  {cfg['login_url']}")
    print("[setup_auth] Please complete login in the browser window (5-minute timeout).\n")

    with sync_playwright() as p:
        context = p.chromium.launch_persistent_context(
            profile_path,
            headless=False,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-first-run",
                "--no-default-browser-check",
            ],
        )
        page = context.new_page()

        try:
            page.goto(cfg["login_url"], wait_until="domcontentloaded")
            page.wait_for_url(cfg["success_pattern"], timeout=TIMEOUT_MS)
        except Exception:
            print(
                "\nLogin did not complete within the 5-minute timeout. Possible causes: "
                "2FA still pending, wrong account, CAPTCHA unsolved, or this account may "
                "not exist on this platform. Check the browser window. Re-run this script "
                "if you need to try again."
            )
            context.close()
            sys.exit(1)

        # Extra settling time so session cookies/localStorage are fully written.
        time.sleep(3)

        print(f"\n[setup_auth] Login detected for {platform}/{account}.")
        print("[setup_auth] Saving browser profile…")
        context.close()
        print("[setup_auth] Done.\n")


if __name__ == "__main__":
    main()
