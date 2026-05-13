# Deploying the PBAP design page

This folder hosts a self-contained, static HTML page that illustrates how
PBAP works. It is intended to be served at the project URL
**https://paredes0.github.io/pbap/** via GitHub Pages.

The page is rendered entirely client-side — React via UMD + Babel — and
has **no build step**. You can open `site/index.html` directly in a
browser to preview it locally.

---

## File layout

```
.
├── .github/workflows/pages.yml      ← GitHub Actions workflow (auto-deploys)
└── site/
    ├── .nojekyll                    ← tells Pages NOT to run Jekyll preprocessing
    ├── index.html                   ← the page
    └── components/
        ├── flow.jsx                 ← Phase 1 interactive flow diagram
        ├── tools.jsx                ← 10 tools grouped by 7 categories
        ├── agreement.jsx            ← intra-category agreement table
        ├── ranking.jsx              ← structural + holistic ranking visual
        ├── apex.jsx                 ← APEX 34-strain deep dive
        └── mount.jsx                ← ReactDOM.createRoot mounts
```

---

## One-time setup on GitHub

1. **Add these files to your repository** at the same paths shown above —
   keep `site/` as a top-level folder alongside `bin/`, `scripts/`, etc.
   The existing pipeline code is untouched.

2. **Enable Pages in repo settings.**
   `Settings → Pages → Build and deployment → Source: GitHub Actions`.

3. **Push to `main`.** The workflow runs and publishes to
   `https://paredes0.github.io/pbap/`. The Action's run summary prints
   the live URL once deployment finishes (≈30–60s).

After that, every push that touches `site/**` or the workflow file
re-deploys automatically. Manual re-deploys via the Actions tab also
work (`Run workflow` button).

---

## Local preview

Open `site/index.html` in any modern browser. Everything works offline
except the Google Fonts stylesheet (`IBM Plex Sans/Serif/Mono`) and the
React + Babel CDN scripts, which are loaded from unpkg.

To avoid the CDN dependency entirely, you can pre-download those scripts
and inline them — see the comment block at the bottom of `index.html`.
Not necessary for the GitHub Pages deployment, since users always have
network connectivity to reach the page in the first place.

---

## Theme

The page supports a **dark/light toggle** in the top bar.

- The initial theme follows the user's OS preference
  (`prefers-color-scheme: dark`).
- Manual selection is stored in `localStorage` under the key
  `pbap-theme` and persists across reloads.
- The theme attribute (`<html data-theme="dark|light">`) is applied
  **before first paint** to avoid the flash-of-wrong-theme.

To change the palette, edit the two CSS variable blocks at the top of
`site/index.html`:

```css
:root, [data-theme="light"] { /* light tokens */ }
[data-theme="dark"]          { /* dark tokens */ }
```

---

## Modularity / extending the diagram

Each visualisation is a small React component under
`site/components/`. To add a new section, write a new
`<name>.jsx` file that calls `window.YourComponent = YourComponent;`
at the bottom, register it in `mount.jsx`, and drop a
`<div id="your-mount" />` into the HTML.

The page has **no bundler** — files are loaded as plain `<script type="text/babel">`
in order, and Babel transpiles them in-browser. This is acceptable for
a static showcase; for a heavier site you'd add a bundler.
