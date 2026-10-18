#!/usr/bin/env python3
"""
Turn CBL Walks YouTube video metadata into Hugo blog post drafts.

Input:  a JSON file (default: videos.json) that is a list of objects like
    {
      "videoId": "abc123XYZ",
      "title": "Tokyo Night Walk 4K | 도쿄 밤 산책 #koreatravelvlog",
      "description": "... bilingual description, Korean + English lines ...",
      "publishedAt": "2026-03-01T10:00:00Z",
      "thumbnails": {"maxres": {"url": "https://i.ytimg.com/vi/abc123XYZ/maxresdefault.jpg"}}
    }

This is the exact shape returned by YouTube Data API v3's
videos.list(part=snippet) combined with playlistItems. Fetch that JSON
separately (see fetch_videos.md) and point this script at it.

Output: content/posts/<slug>.md draft files, one per video, plus a
downloaded cover image under static/images/covers/<videoId>.jpg.

This script produces DRAFTS (draft: true in front matter). Nothing is
meant to go live without the user editing the English body text by hand,
per the standing rule: automation supplies raw material, a person
polishes it.

Idempotent: a video whose post file already exists is skipped unless
--force is passed, so re-running after new uploads only creates posts
for the new videos.
"""
import argparse
import json
import pathlib
import re
import sys
import urllib.request

sys.path.insert(0, str(pathlib.Path(__file__).parent))
from koreanlib import korean_ratio, is_english_line, is_credit_line

ROOT = pathlib.Path(__file__).parent.parent
POSTS_DIR = ROOT / "content" / "posts"
COVERS_DIR = ROOT / "static" / "images" / "covers"

# Known place names to auto-tag as "destinations" -- extend freely.
PLACE_KEYWORDS = {
    "tokyo": "Tokyo", "osaka": "Osaka", "kyoto": "Kyoto", "seoul": "Seoul",
    "busan": "Busan", "incheon": "Incheon", "jeju": "Jeju",
    "amsterdam": "Amsterdam", "ghent": "Ghent", "brussels": "Brussels",
    "stockholm": "Stockholm", "lisbon": "Lisbon", "porto": "Porto",
    "helsinki": "Helsinki", "tallinn": "Tallinn", "luxembourg": "Luxembourg",
    "hong kong": "Hong Kong", "auckland": "Auckland", "wellington": "Wellington",
    "queenstown": "Queenstown",
}


def slugify(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r"[^a-z0-9\s-]", "", text)
    text = re.sub(r"\s+", "-", text).strip("-")
    return text[:70].strip("-") or "walk"


def pick_english_hook(title: str) -> tuple[str, list[str]]:
    """Split a '{hook} | {korean} #tags' title. Returns (hook, hashtags)."""
    hashtags = re.findall(r"#(\w+)", title)
    title_no_tags = re.sub(r"#\w+", "", title).strip()
    parts = [p.strip() for p in title_no_tags.split("|") if p.strip()]
    if not parts:
        return title_no_tags.strip(), hashtags
    # English hook = the segment with the LOWEST Korean-character ratio
    hook = min(parts, key=korean_ratio)
    return hook, hashtags


def extract_english_body(description: str) -> list[str]:
    lines = description.splitlines()
    kept = []
    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
        if is_credit_line(stripped):
            continue
        if re.fullmatch(r"(#\w+\s*)+", stripped):
            continue  # pure hashtag footer line, handled separately
        if is_english_line(stripped):
            kept.append(stripped)
    return kept


def extract_hashtags(description: str) -> list[str]:
    return re.findall(r"#(\w+)", description)


def guess_destinations(title: str, body_lines: list[str]) -> list[str]:
    haystack = (title + " " + " ".join(body_lines)).lower()
    found = []
    for key, label in PLACE_KEYWORDS.items():
        if key in haystack and label not in found:
            found.append(label)
    return found


def download_cover(video_id: str, thumbnails: dict) -> str:
    """Try to pull the thumbnail down locally (needed for pin-image
    generation). If the network here can't reach i.ytimg.com (e.g. a
    sandboxed environment with a restricted egress allowlist), fall back
    to the thumbnail's own CDN URL -- still works fine for the site's
    <img> tags and OG/meta tags, just isn't self-hosted. Re-run this
    script with --force on a machine with normal internet access (e.g.
    your own Mac) to replace these with locally-downloaded copies, which
    make_pins.py needs.
    """
    COVERS_DIR.mkdir(parents=True, exist_ok=True)
    dest = COVERS_DIR / f"{video_id}.jpg"
    url = (
        thumbnails.get("maxres", {}).get("url")
        or thumbnails.get("high", {}).get("url")
        or thumbnails.get("default", {}).get("url")
    )
    if dest.exists():
        return f"/images/covers/{video_id}.jpg"
    if not url:
        return ""
    try:
        urllib.request.urlretrieve(url, dest)
        return f"/images/covers/{video_id}.jpg"
    except Exception as e:
        print(f"  ! cover download failed for {video_id}, using hotlinked URL instead: {e}", file=sys.stderr)
        return url


def build_post(video: dict, force: bool) -> str | None:
    video_id = video["videoId"]
    title_raw = video["title"]
    hook, title_tags = pick_english_hook(title_raw)
    body_lines = extract_english_body(video.get("description", ""))
    desc_tags = extract_hashtags(video.get("description", ""))
    tags = sorted(set(t.lower() for t in title_tags + desc_tags))
    destinations = guess_destinations(title_raw, body_lines)

    slug = f"{slugify(hook)}-{video_id[:6].lower()}"
    post_path = POSTS_DIR / f"{slug}.md"
    if post_path.exists() and not force:
        return None

    cover_path = download_cover(video_id, video.get("thumbnails", {}))
    meta_desc = " ".join(body_lines)[:155].strip()
    if not meta_desc:
        meta_desc = hook

    date = video.get("publishedAt", "")[:10] or "2026-01-01"

    fm_tags = json.dumps(tags, ensure_ascii=False)
    fm_dest = json.dumps(destinations, ensure_ascii=False)
    hook_escaped = hook.replace('"', '\\"')
    meta_desc_escaped = meta_desc.replace('"', '\\"')

    body_md = "\n\n".join(body_lines) if body_lines else (
        "<!-- TODO: no English lines were auto-detected in the original "
        "description -- write the walk-through yourself here. -->"
    )

    front_matter = f"""---
title: "{hook_escaped}"
date: {date}
draft: true
description: "{meta_desc_escaped}"
tags: {fm_tags}
destinations: {fm_dest}
cover:
  image: "{cover_path}"
  alt: "{hook_escaped}"
  relative: false
videoID: "{video_id}"
---
"""

    content = f"""{front_matter}
{{{{< youtube {video_id} >}}}}

{body_md}

<!-- TODO (edit before publishing):
  1. Rewrite/polish the lines above in your own voice -- this is a raw
     auto-extracted draft, not finished copy.
  2. Add 1-2 practical notes (best time to walk this route, nearest
     station, anything you'd tell a first-time visitor).
  3. Double-check `tags` / `destinations` in the front matter above.
  4. Remove `draft: true` once it's ready to publish.
-->
"""
    post_path.parent.mkdir(parents=True, exist_ok=True)
    post_path.write_text(content, encoding="utf-8")
    return str(post_path.relative_to(ROOT))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", default="videos.json")
    ap.add_argument("--force", action="store_true", help="overwrite existing drafts")
    args = ap.parse_args()

    data_path = ROOT / args.input
    if not data_path.exists():
        print(f"Input file not found: {data_path}", file=sys.stderr)
        sys.exit(1)

    videos = json.loads(data_path.read_text(encoding="utf-8"))
    created, skipped = 0, 0
    for video in videos:
        result = build_post(video, args.force)
        if result:
            created += 1
            print(f"  + {result}")
        else:
            skipped += 1
    print(f"\nDone. Created {created} draft(s), skipped {skipped} existing.")


if __name__ == "__main__":
    main()
