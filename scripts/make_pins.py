#!/usr/bin/env python3
"""
Generate Pinterest-ready vertical pin images (1000x1500, 2:3) from each
blog post's cover photo + title. Reads every content/posts/*.md front
matter, pulls `cover.image` and `title` (+ first `destinations` entry
as a small subtitle), and writes static/images/pins/<slug>.jpg.

Run this AFTER generate_posts.py has produced posts and downloaded
cover images (it needs the real JPG file on disk under static/, not
just the front-matter path).

Usage:
    python3 scripts/make_pins.py              # all posts missing a pin
    python3 scripts/make_pins.py --force      # regenerate every pin
    python3 scripts/make_pins.py --slug SLUG  # just one post
"""
import argparse
import pathlib
import re
import sys

from PIL import Image, ImageDraw, ImageFont, ImageFilter
import yaml

ROOT = pathlib.Path(__file__).parent.parent
POSTS_DIR = ROOT / "content" / "posts"
STATIC_DIR = ROOT / "static"
PINS_DIR = STATIC_DIR / "images" / "pins"
FONT_BOLD = ROOT / "assets" / "fonts" / "Poppins-Bold.ttf"
FONT_REG = ROOT / "assets" / "fonts" / "Poppins-Regular.ttf"

CANVAS_W, CANVAS_H = 1000, 1500
BRAND = "CBL WALKS"
HANDLE = "youtube.com/@CBL-walk"


def read_front_matter(md_path: pathlib.Path) -> dict:
    text = md_path.read_text(encoding="utf-8")
    m = re.match(r"^---\n(.*?)\n---\n", text, re.DOTALL)
    if not m:
        return {}
    return yaml.safe_load(m.group(1)) or {}


def wrap_text(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.FreeTypeFont, max_width: int) -> list[str]:
    words = text.split()
    lines, current = [], ""
    for word in words:
        trial = f"{current} {word}".strip()
        if draw.textlength(trial, font=font) <= max_width:
            current = trial
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines


def make_pin(cover_path: pathlib.Path, title: str, subtitle: str, out_path: pathlib.Path):
    if cover_path.exists():
        img = Image.open(cover_path).convert("RGB")
        # cover-fit crop to 2:3
        target_ratio = CANVAS_W / CANVAS_H
        w, h = img.size
        cur_ratio = w / h
        if cur_ratio > target_ratio:
            new_w = int(h * target_ratio)
            x0 = (w - new_w) // 2
            img = img.crop((x0, 0, x0 + new_w, h))
        else:
            new_h = int(w / target_ratio)
            y0 = (h - new_h) // 2
            img = img.crop((0, y0, w, y0 + new_h))
        img = img.resize((CANVAS_W, CANVAS_H), Image.LANCZOS)
    else:
        img = Image.new("RGB", (CANVAS_W, CANVAS_H), (30, 30, 35))

    # Dark gradient at the bottom third for text legibility
    gradient = Image.new("L", (1, CANVAS_H), color=0)
    for y in range(CANVAS_H):
        t = max(0.0, (y - CANVAS_H * 0.45) / (CANVAS_H * 0.55))
        gradient.putpixel((0, y), int(255 * min(1.0, t) * 0.85))
    gradient = gradient.resize((CANVAS_W, CANVAS_H))
    black = Image.new("RGB", (CANVAS_W, CANVAS_H), (0, 0, 0))
    img = Image.composite(black, img, gradient)

    draw = ImageDraw.Draw(img)
    title_font = ImageFont.truetype(str(FONT_BOLD), 58)
    sub_font = ImageFont.truetype(str(FONT_REG), 34)
    brand_font = ImageFont.truetype(str(FONT_BOLD), 30)

    margin = 60
    max_text_w = CANVAS_W - margin * 2

    lines = wrap_text(draw, title.upper(), title_font, max_text_w)
    line_h = title_font.getbbox("A")[3] + 14
    block_h = line_h * len(lines)

    y = CANVAS_H - margin - 70 - block_h
    if subtitle:
        draw.text((margin, y - 50), subtitle.upper(), font=sub_font, fill=(255, 210, 120))

    for line in lines:
        draw.text((margin, y), line, font=title_font, fill=(255, 255, 255))
        y += line_h

    draw.text((margin, CANVAS_H - 50), f"{BRAND}  ·  {HANDLE}", font=brand_font, fill=(230, 230, 230))

    out_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(out_path, "JPEG", quality=90)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--slug", default=None)
    args = ap.parse_args()

    md_files = sorted(POSTS_DIR.glob("*.md"))
    if args.slug:
        md_files = [p for p in md_files if p.stem == args.slug]

    made, skipped = 0, 0
    for md_path in md_files:
        fm = read_front_matter(md_path)
        title = fm.get("title", md_path.stem)
        destinations = fm.get("destinations") or []
        subtitle = destinations[0] if destinations else ""
        cover_rel = (fm.get("cover") or {}).get("image", "")
        cover_path = STATIC_DIR / cover_rel.lstrip("/") if cover_rel else None

        out_path = PINS_DIR / f"{md_path.stem}.jpg"
        if out_path.exists() and not args.force:
            skipped += 1
            continue

        make_pin(cover_path or pathlib.Path("/nonexistent"), title, subtitle, out_path)
        made += 1
        print(f"  + {out_path.relative_to(ROOT)}")

    print(f"\nDone. Created {made} pin(s), skipped {skipped} existing.")


if __name__ == "__main__":
    main()
