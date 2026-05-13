---
title: PBAP Demo
emoji: 🧬
colorFrom: indigo
colorTo: blue
sdk: gradio
sdk_version: 4.40.0
app_file: app.py
pinned: false
license: polyform-noncommercial-1.0.0
---

# PBAP demo — Hugging Face Space

This folder is the **public-facing frontend** for the PBAP demo,
designed to be deployed as a free Hugging Face Space. The Space does
no compute; it forwards user input to the operator's Linux backend
(see `../api/`) and renders the result.

The YAML block at the top of this file is the Space's metadata. When
you create a new Space and tell it to look at this folder, Hugging
Face reads those keys to configure the runtime.

---

## Quick deploy

### 1. Create the Space

1. On Hugging Face, click **New Space**.
2. Owner: your account.
3. Space name: `pbap-demo` (or whatever you like; the URL becomes
   `https://huggingface.co/spaces/<your-user>/pbap-demo`).
4. License: **Other** (the SDK presets list does not include
   PolyForm; you'll declare it in the README YAML above and in
   the footer of the app).
5. SDK: **Gradio**.
6. Hardware: **CPU basic** (free tier). The frontend is essentially
   an HTTP proxy + UI; it never runs the pipeline itself.
7. Visibility: **Public**.

Create the Space; you get an empty repo with a `README.md` and a
default `app.py`.

### 2. Upload the frontend

```bash
git clone https://huggingface.co/spaces/<your-user>/pbap-demo
cd pbap-demo

# Replace defaults with the demo files
cp /path/to/pbap/demo/frontend/app.py .
cp /path/to/pbap/demo/frontend/requirements.txt .
cp /path/to/pbap/demo/frontend/README.md .

git add . && git commit -m "deploy PBAP demo frontend" && git push
```

The Space rebuilds automatically. First boot takes 1–3 minutes.

### 3. Set secrets

In **Settings → Variables and secrets**, add:

| Name | Value | Visible to users? |
|---|---|---|
| `PBAP_API_BASE` | `https://pbap-demo.<your-domain>.com` (the Cloudflare Tunnel URL — see `../api/README.md` step 6) | No (Secret) |
| `CONTACT_EMAIL` | `noeparedesalf@gmail.com` | Yes (Variable) — surfaces in the footer |
| `DEMO_VERSION` | `0.1.0` (optional) | Yes |

The Space will pick these up on next reload (Settings → Restart Space
or push a trivial commit).

### 4. Smoke test

Open `https://huggingface.co/spaces/<your-user>/pbap-demo`. The
"Backend status" panel should show queue + rate counters. If it says
"Backend unreachable", the Tunnel is down or `PBAP_API_BASE` is wrong.

Load the 4-peptide example, click **Run audit**, wait 30–120 seconds.
You should see the inline REPORT.html plus four download links.

---

## What the user sees

- A textarea for FASTA or plain peptides (one per line).
- A checkbox group of 10 tools (all on by default).
- A "Backend status" panel updating on demand.
- After submitting: a progress bar, then the inline `REPORT.html`
  plus links to download `consolidated.csv`, `consolidated.json`,
  `tool_health_report.json`, and the full HTML.
- Two collapsible accordions:
  1. **Tools and attribution** — table of the 10 tools with links
     to upstream repos and a request to cite the original papers.
  2. **About this demo / license / takedown** — explicit
     non-commercial framing, no-tracking statement, takedown email.

These are the operator-side commitments documented in the
"Mitigation shield" section of `../api/README.md`. **Do not strip
them**; they are what makes the demo defensible.

---

## Local development

You can run the frontend locally pointed at a local backend:

```bash
# In one terminal: backend (see ../api/README.md)
cd ../api
set -a; source .env; set +a
uvicorn server:app --host 127.0.0.1 --port 8000

# In another terminal: frontend
cd ../frontend
pip install -r requirements.txt
PBAP_API_BASE=http://127.0.0.1:8000 python app.py
```

Open `http://127.0.0.1:7860`.

---

## Limits the user sees

Pulled live from `/health` on each refresh. Defaults:

- 50 peptides per submission.
- 3 jobs per IP per hour.
- 200 jobs per day, total.
- Sequences must be 5–100 residues of standard amino acids
  (ACDEFGHIKLMNPQRSTVWY).
- Per-job timeout: 600 s.

These are operator-tunable on the backend (`demo/api/.env`).

---

## Disabling a tool

Two ways, both backend-side:

1. **Soft**: set `ALLOWED_TOOLS` in `demo/api/.env` to the subset you
   want enabled. The frontend will reflect this on next `/health`
   refresh, and submissions referencing other tools get rejected
   with HTTP 400.
2. **Hard**: edit `config/pipeline_config.yaml` in the repo on the
   backend host and mark the tool as inactive. This affects the
   pipeline globally (not just the demo) so prefer (1) for
   demo-only ablations.
