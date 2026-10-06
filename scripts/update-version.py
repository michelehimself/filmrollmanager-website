#!/usr/bin/env python3
"""Keep the version number and the DMG download link on the site in sync
with the latest GitHub release of the app.

Runs in GitHub Actions (see .github/workflows/update-version.yml), but also
works locally:  python3 scripts/update-version.py
Only the Python standard library is used. Exit code is 0 either way; the
workflow decides whether there is something to commit.
"""
import json
import os
import re
import sys
import urllib.request

REPO = "michelehimself/filmroll-manager"
PAGES = ["index.html", "impressum.html", "datenschutz.html"]
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def latest_release():
    req = urllib.request.Request(
        f"https://api.github.com/repos/{REPO}/releases/latest",
        headers={"Accept": "application/vnd.github+json", "User-Agent": "filmrollmanager-website"},
    )
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def pick_dmg(assets):
    dmgs = [a for a in assets if a["name"].lower().endswith(".dmg")]
    if not dmgs:
        return None
    for a in dmgs:  # prefer the Apple Silicon build
        if "aarch64" in a["name"].lower() or "arm64" in a["name"].lower():
            return a
    return dmgs[0]


def pick_exe(assets):
    """The 64-bit Windows installer (name ends with -setup.exe)."""
    exes = [a for a in assets if a["name"].lower().endswith("-setup.exe")]
    for a in exes:
        if "x64" in a["name"].lower():
            return a
    return exes[0] if exes else None


def main():
    release = latest_release()
    version = release["tag_name"].lstrip("v")
    dmg = pick_dmg(release.get("assets", []))
    if not re.fullmatch(r"\d+\.\d+\.\d+", version):
        sys.exit(f"Unexpected version tag: {release['tag_name']!r}")
    if dmg is None:
        sys.exit("Latest release has no .dmg asset yet, leaving the site unchanged.")
    url = dmg["browser_download_url"]
    exe = pick_exe(release.get("assets", []))
    exe_url = exe["browser_download_url"] if exe else None
    print(f"Latest release: v{version} -> {url}")
    print(f"Windows installer: {exe_url or 'none in this release, leaving the Windows link unchanged'}")

    link_re = re.compile(
        r"https://github\.com/" + re.escape(REPO) + r"/releases/download/[^\"'<>\s]+\.dmg"
    )
    exe_re = re.compile(
        r"https://github\.com/" + re.escape(REPO) + r"/releases/download/[^\"'<>\s]+-setup\.exe"
    )
    changed = []
    for page in PAGES:
        path = os.path.join(ROOT, page)
        with open(path, encoding="utf-8") as f:
            old = f.read()
        new = link_re.sub(url, old)
        if exe_url:
            new = exe_re.sub(exe_url, new)
        new = re.sub(r"(Version )\d+\.\d+\.\d+", r"\g<1>" + version, new)
        new = re.sub(r"(· v)\d+\.\d+\.\d+(</span>)", r"\g<1>" + version + r"\g<2>", new)
        if new != old:
            with open(path, "w", encoding="utf-8") as f:
                f.write(new)
            changed.append(page)
    print("Updated: " + (", ".join(changed) if changed else "nothing, already current"))


if __name__ == "__main__":
    main()
