# Profile cards

Brand source: https://eshan.fyi/ (read 2026-11-10). Cards retain the site's
olive accent and typography, with GitHub-compatible foregrounds and borders.
Backgrounds are transparent so they inherit the exact surrounding GitHub theme.
Light: ink #1f2328, muted #59636e, border #d1d9e0, accent #59684d.
Dark: ink #f0f6fc, muted #9198a1, border #3d444d, accent #a9bf8e.
Cormorant Garamond display and Manrope body fonts are bundled with OFL licenses.
The original README's six featured repos are preserved.

```sh
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
python scripts/render_cards.py
STATIC=1 python scripts/render_cards.py
```

Open `preview-static/preview.html` to screenshot all final frames. Static mode
writes no animations to the images and leaves the production cards untouched.
Open `cards/preview.html` for the animated version. Each image starts its own
clock on load; staggered delays approximate top-to-bottom playback, without
scroll detection. All animation finishes once. Reduced motion disables CSS
animation and hides the SMIL layer in favour of its final-state twin.

The hero is text-only, with no portrait.
Fonts are subset using pyftsubset into base64 WOFF data URIs on every render.

The daily Action runs at 02:17 UTC and can be dispatched manually. It refreshes
`data/contributions.json` from GitHub's GraphQL API, renders, and commits changed
JSON, README and cards. It uses the built-in GITHUB_TOKEN with contents:write;
repository rules must permit the bot to push. The token sees public activity;
private activity visibility depends on GitHub permissions and profile settings.
A failed fetch fails the job and keeps the prior snapshot. No fabricated data.

Current streak counts consecutive active UTC days ending today, or yesterday
if today has no contributions. Active days and busiest day cover the displayed
calendar; ties choose the earliest date. Months at the edges may be partial.
The initial snapshot came from GitHub's public contribution calendar and REST
repository API. Subsequent refreshes use GraphQL.

The renderer is intentionally one Python script. Edit the hero copy and links
in `render()`, and the featured repository list in `FEATURED`. Refresh metadata
with `GITHUB_TOKEN=... python scripts/render_cards.py --refresh` (use an env
secret; never commit credentials). README is generated with outer anchor tags,
because links inside an SVG do not work when it is embedded as an img.

README picture/source markup selects the dark SVGs using prefers-color-scheme.
The daily renderer updates both sets. Preview HTML follows the browser colour
preference; static previews also include both sets. Repositories are laid out
in pairs using 49%-width img elements and 470px-wide SVGs with wrapped descriptions.

GitHub strips target attributes from README links (verified against its Markdown
API). New-tab clicks cannot be forced on the profile; use Cmd/Ctrl-click or
middle-click. The standalone preview uses target="_blank" and rel="noopener
noreferrer", where browsers support the requested behaviour.
