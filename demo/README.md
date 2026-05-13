# PBAP — Public demo

> **Live demo** → coming soon at `https://pbap-demo.<your-domain>`
> **Maintainer** → noeparedesalf@gmail.com
> **License** → see top-level `LICENSE` (PolyForm Noncommercial 1.0.0)
> **Status** → reference scaffold; deployment is operator-driven.

This folder contains the **operator-side scaffold** for hosting a free,
non-commercial public demo of the PBAP pipeline. The demo lets anyone
paste up to 50 peptides into a web form and receive the same
consolidated multi-tool report that `scripts/run_audit.py` produces
locally — without installing anything.

It is intentionally split in two halves so the heavy compute stays on
the operator's machine and the public-facing surface is cheap to host:

```
┌─────────────────────────────────────────────────────────────────────┐
│  User                                                               │
│   ↓ HTTPS                                                           │
│  Frontend (Hugging Face Space — Gradio)        ← demo/frontend/     │
│   ↓ HTTPS (Cloudflare Tunnel)                                       │
│  Backend  (FastAPI, on operator's Linux PC)    ← demo/api/          │
│   ↓ subprocess                                                      │
│  scripts/run_audit.py  (the same orchestrator as the CLI)           │
│   ↓                                                                 │
│  10 prediction tools (each in its own micromamba env)               │
└─────────────────────────────────────────────────────────────────────┘
```

The frontend is stateless and cheap; the backend bears all the GPU
load and enforces the rate / concurrency / daily-cap controls.

---

## Why this exists separately from the main pipeline

- **Licensing posture.** The repo itself contains no third-party code
  or weights (see `THIRD_PARTY_LICENSES.md`). The demo runs the same
  tools the user would clone locally; running them on the operator's
  hardware as a free, attribution-preserving, non-commercial service
  stays within each upstream license's terms. The mitigation shield
  (clear attribution, takedown contact, no weight downloads) is
  documented in `demo/api/README.md` §"Mitigation shield".
- **Operational separation.** The demo's compute envelope, queue,
  rate limits and disclaimer surface are demo concerns, not pipeline
  concerns. Keeping them under `demo/` means the main pipeline is
  unaffected by demo changes and vice-versa.

---

## Folder layout

```
demo/
├── README.md                  ← this file
├── api/                       ← backend (runs on operator's Linux)
│   ├── server.py              ← FastAPI app: /submit, /status, /result, /health
│   ├── jobs.py                ← in-memory FIFO queue + single-worker thread
│   ├── limits.py              ← per-IP rate limit, daily cap, input validation
│   ├── runner.py              ← subprocess wrapper around scripts/run_audit.py
│   ├── requirements.txt       ← FastAPI + uvicorn + python-multipart
│   ├── .env.example           ← config: cap, rate, tools allow-list, etc.
│   ├── cloudflared.example.yml← Cloudflare Tunnel config template
│   ├── pbap-api.service.example ← systemd unit template
│   └── README.md              ← step-by-step deployment on Linux
└── frontend/                  ← Hugging Face Space (Gradio)
    ├── app.py                 ← Gradio UI + backend client
    ├── requirements.txt       ← gradio + httpx
    └── README.md              ← step-by-step Space deployment
```

---

## Operating principles

1. **No login, no tracking, no cookies.** Minimizes GDPR surface and
   the perception that the operator is collecting anything about
   users' peptide sequences.
2. **Attribution surfaces in every result.** Each tool's output is
   labeled with the tool name, the citation of its paper, and a link
   to its upstream repo. The frontend renders a "Tools used in this
   run" section at the top of every result.
3. **Takedown contact is visible.** The footer of every page shows the
   maintainer email. Any upstream author can request removal of their
   tool and the operator commits to acting within 24h.
4. **Weights are never served.** The demo executes the tools but does
   not expose model files for download. Users get predictions, not
   redistributable artifacts.
5. **Conservative compute envelope.** N=1 worker, 50 peptides per
   submission, 3 jobs per IP per hour, daily global cap. The operator
   can dial all of these without code changes (`.env`).

---

## Quick start (operator)

1. Read [`api/README.md`](api/README.md) and deploy the backend on the
   Linux host that already has the 10 tool environments installed.
2. Read [`frontend/README.md`](frontend/README.md) and create a free
   Hugging Face Space pointing at the backend's public URL.
3. Add a "Try online" badge to the top-level `README.md` once the
   Space is up.

Both halves can be developed and tested independently — the frontend
talks to the backend over plain HTTPS with a JSON contract, no shared
state.

---

## Quick start (user)

Open the live demo URL (once published), paste up to 50 peptide
sequences (one per line, or paste/upload a FASTA), pick which tools to
run, and submit. The result page shows a summary table and offers the
full `REPORT.html` and `consolidated.csv` as downloads — identical to
what `scripts/run_audit.py --input <file>` produces locally.
