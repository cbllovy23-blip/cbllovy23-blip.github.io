# CBL Walks blog

A static (Hugo) blog that turns [CBL Walks](https://www.youtube.com/@CBL-walk) YouTube videos
into English blog posts, for overseas (Google/Pinterest) discovery. Content is
auto-drafted from each video's existing English description, then hand-edited
before publishing — nothing goes live un-reviewed (`draft: true` by default).

## 0. One-time setup (do this yourself — account creation isn't something
   Claude can do on your behalf)

1. Create a GitHub account: https://github.com/signup
2. Create a new **public** repository. Two naming options:
   - `cblwalks-blog` → site will live at `https://<your-username>.github.io/cblwalks-blog/`
   - `<your-username>.github.io` → site will live at the root, `https://<your-username>.github.io/`
     (simpler URL, but only one such repo is allowed per account)
3. Push this folder to that repository:
   ```bash
   cd cblwalks-blog
   git remote add origin https://github.com/<your-username>/<repo-name>.git
   git add .
   git commit -m "Initial site scaffold"
   git branch -M main
   git push -u origin main
   ```
4. In the repo on GitHub: **Settings → Pages → Source → "GitHub Actions"**.
   The workflow in `.github/workflows/hugo.yml` will build and deploy
   automatically on every push to `main`.
5. If you used the `cblwalks-blog` name (not `<username>.github.io`), edit
   `hugo.yaml`'s `baseURL` to `https://<your-username>.github.io/cblwalks-blog/`
   before your first push.

## 1. Content pipeline (repeat this whenever you want new posts)

```bash
# 1. Get video metadata from YouTube Data API into videos.json
#    (title, description, publishedAt, thumbnails) -- see NOTES.md for how
#    this was fetched during the earlier playlist/title-rewrite project.

# 2. Auto-generate draft posts from videos.json
python3 scripts/generate_posts.py --input videos.json

# 3. Open each new file under content/posts/*.md and edit the body text
#    by hand -- the script only extracts the English lines that were
#    already in the video description as a starting point.

# 4. Generate Pinterest pin images once cover photos exist
python3 scripts/make_pins.py

# 5. Preview locally
hugo server --buildDrafts
# open http://localhost:1313

# 6. When a post is ready, remove `draft: true` from its front matter.

# 7. Publish
git add .
git commit -m "Add N new walks"
git push
```

## 2. Repo layout

```
content/posts/        one .md file per video (generated + hand-edited)
static/images/covers/ downloaded YouTube thumbnails
static/images/pins/   generated Pinterest-ready vertical images (1000x1500)
scripts/
  generate_posts.py   videos.json -> draft posts
  make_pins.py         posts -> Pinterest pin images
  koreanlib.py          Korean/English line classifier shared by both scripts
assets/fonts/           Poppins (SIL Open Font License) used for pin text
.github/workflows/hugo.yml   builds + deploys to GitHub Pages on every push
```

## 3. SEO notes

- Each post's `description` front matter becomes the meta description / OG
  description — keep it under ~155 characters and specific (city + what
  the walk covers), since that's what shows up in Google search results.
- `tags` and `destinations` build `/tags/<x>/` and `/destinations/<x>/`
  archive pages automatically — these are useful internal-link hubs for SEO,
  so it's worth keeping them consistent across posts for the same city.
- `sitemap.xml` and `robots.txt` are generated automatically; once the
  site is live, submit the sitemap URL in Google Search Console.
