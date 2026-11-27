#!/usr/bin/env python3
"""
Regenerate the COSMIC TELEMETRY galaxy map (galaxy.svg) from the live repo list.

- Center hub stays the flagship repo (Axiom-self-evident-truth).
- The 8 orbiting nodes become the 8 most recently updated public repos
  (excluding the center and the profile repo itself), in orbit order.
- The HUD "REPOSITORIES: NN" count becomes the live public-repo total.
- Node label pills are re-sized to fit the new text.

Only the label text, pill width/x and the repo count change -- the orbit
paths, animations, nebula and HUD wording are untouched, so the map keeps
its hand-drawn look.

Data source: api.github.com/users/<user>/repos (public, no auth needed).
If GITHUB_TOKEN is set (the daily workflow passes secrets.GITHUB_TOKEN),
it is sent as a Bearer token for the higher rate limit. If the fetch fails
or is rate-limited, the script exits 0 WITHOUT touching galaxy.svg, so the
old map stays live and the next daily run retries.

Run daily by .github/workflows/update-profile-art.yml.
"""
import json
import os
import re
import sys
import urllib.request

USERNAME = os.environ.get("GH_PROFILE_USER", "ProNoob-Dev")
CENTER_REPO = "Axiom-self-evident-truth"
CENTER_LABEL = "ProNoob-Dev"
MAX_LABEL = 15
API_URL = f"https://api.github.com/users/{USERNAME}/repos?per_page=100&sort=updated"

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GALAXY_PATH = os.path.join(ROOT, "galaxy.svg")

# Short display names for the long repo slugs. Anything not listed here
# falls back to short_name() below.
SHORT = {
    "Axiom-self-evident-truth": "Axiom",
    "ai-investment-intelligence-platform": "Invest-Intel",
    "Employee-Onboarding-Hr-Policy-Copilot": "HR-Copilot",
    "ai-multi-agent-workflow-engine": "Multi-Agent",
    "ai-insurance-claims-triage-agent": "Claims-Triage",
    "ai-kyc-client-onboarding-agent": "KYC-Agent",
    "MoviesDriveAPi": "MoviesDrive",
    "Pro-MovieAPiDrive": "Pro-Movie",
    "Telegram-Expense-Tracker-Bot": "Telegram-Bot",
    "Free-udemy-courses-bot": "Free-Udemy",
    "Personal-Agent-Free": "Personal-Agent",
    "udemy-enroller-site": "Udemy-Site",
    "Paper-Trader": "Paper-Trader",
    "SaveReel": "SaveReel",
    "WA-BOT": "WA-BOT",
    "nosleep": "NoSleep",
    "Pinger": "Pinger",
}


def short_name(repo):
    if repo in SHORT:
        return SHORT[repo]
    name = repo
    if name.lower().startswith("ai-"):
        name = name[3:]
    parts = [p[:1].upper() + p[1:] for p in re.split(r"[-_]", name) if p]
    out = ""
    for p in parts:
        cand = p if not out else out + "-" + p
        if len(cand) <= MAX_LABEL:
            out = cand
        else:
            break
    return out or parts[0][:MAX_LABEL]


def fetch_repos():
    req = urllib.request.Request(API_URL, headers={"User-Agent": "profile-readme-bot/1.0"})
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.load(resp)
    except Exception as exc:  # noqa: BLE001 - offline/rate-limit: keep old map
        print(f"galaxy: repo fetch failed ({exc}) -- leaving galaxy.svg unchanged")
        return None


def pill_width(label):
    # 11px monospace bold: ~6.6px per char + 14px padding, rounded to even
    w = int(round(len(label) * 6.6)) + 14
    return w + (w % 2)


def main():
    repos = fetch_repos()
    if repos is None:
        return 0
    if isinstance(repos, dict) and repos.get("message"):
        print(f"galaxy: GitHub API error: {repos['message']} -- leaving galaxy.svg unchanged")
        return 0

    live = [r for r in repos if not r.get("fork") and not r.get("archived")]
    total = len(live)
    pool = [r for r in live if r["name"] != USERNAME and r["name"] != CENTER_REPO]
    pool.sort(key=lambda r: r.get("updated_at") or "", reverse=True)
    orbiters = [short_name(r["name"]) for r in pool[:8]]
    labels = [CENTER_LABEL] + orbiters
    if len(orbiters) < 8:
        print(f"galaxy: only {len(orbiters)} orbiters found, expected 8 -- leaving galaxy.svg unchanged")
        return 0

    with open(GALAXY_PATH, encoding="utf-8") as fh:
        svg = fh.read()

    # One label pill per node, in document order: center, inner 1-2, mid 3-4, outer 5-8.
    pair_re = re.compile(
        r'(<rect x=")-?\d+(" y="-\d+" width=")\d+(" height="\d+" rx="\d+" fill="#090d16" '
        r'fill-opacity="0\.8\d+"[^/]*/>\s*<text x="0" y="-\d+" text-anchor="middle" '
        r'fill="#[0-9a-f]{6}">)[^<]*(</text>)'
    )
    pairs = pair_re.findall(svg)
    if len(pairs) != 9:
        print(f"galaxy: expected 9 label pills, found {len(pairs)} -- template changed, aborting", file=sys.stderr)
        return 1

    def swap(match):
        idx = swap.i
        swap.i += 1
        label = labels[idx]
        w = pill_width(label)
        return f'{match.group(1)}-{w // 2}{match.group(2)}{w}{match.group(3)}{label}{match.group(4)}'

    swap.i = 0
    new_svg, n = pair_re.subn(swap, svg)
    assert n == 9

    new_svg, n = re.subn(r"REPOSITORIES: \d+ • ORBIT: LIVE",
                         f"REPOSITORIES: {total:02d} • ORBIT: LIVE", new_svg)
    assert n == 1, "HUD repo-count string not found"

    if new_svg == svg:
        print(f"galaxy: no change (orbiters {', '.join(orbiters)}, total {total})")
        return 0
    with open(GALAXY_PATH, "w", encoding="utf-8") as fh:
        fh.write(new_svg)
    print(f"galaxy: updated -- center {CENTER_LABEL}, orbiters {', '.join(orbiters)}, total {total}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
