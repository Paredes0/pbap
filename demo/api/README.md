# PBAP demo backend — operator guide

This is the **server side** of the public PBAP demo. It runs on the
operator's Linux host (the same one that already has the 10 prediction
tool environments installed) and exposes a small FastAPI surface that
the frontend (a Hugging Face Space, see `../frontend/`) calls over
HTTPS.

The frontend never touches the tools directly. It POSTs sequences to
this backend, polls a job ID, and downloads artifacts when ready.

---

## At a glance

```
HuggingFace Space  ──HTTPS──▶  Cloudflare Tunnel  ──HTTP──▶  uvicorn:8000
                                                                  │
                                                                  ▼
                                                      JobManager (queue, N=1)
                                                                  │
                                                                  ▼
                                           micromamba run -n ml python scripts/run_audit.py
                                                                  │
                                                                  ▼
                                                      Outputs/<job>/REPORT.html + .csv
```

Files in this folder:

| File | Role |
|---|---|
| `server.py` | FastAPI app — endpoints, validation, CORS, IP extraction |
| `jobs.py` | In-memory FIFO queue + worker thread + janitor |
| `runner.py` | Subprocess wrapper around `scripts/run_audit.py` |
| `limits.py` | Input validation + per-IP / global rate limiting |
| `requirements.txt` | `fastapi`, `uvicorn`, `pydantic`, `python-multipart` |
| `.env.example` | All operator-tunable knobs |
| `cloudflared.example.yml` | Cloudflare Tunnel config template |
| `pbap-api.service.example` | systemd unit template |

---

## Endpoints

| Verb | Path | Purpose |
|---|---|---|
| `GET`  | `/`                  | Plain-text landing |
| `GET`  | `/health`            | Limits, queue stats, daily-cap usage |
| `POST` | `/submit`            | Submit `{text, tools}` → `{job_id, status, queue_position}` |
| `GET`  | `/status/{job_id}`   | Poll a job |
| `GET`  | `/result/{job_id}/{kind}` | `kind` ∈ `report`, `csv`, `json`, `health` |
| `POST` | `/cancel/{job_id}`   | Cancel a job that is still `PENDING` |
| `GET`  | `/docs`              | Auto-generated OpenAPI UI |

The contract is documented in `server.py`. Pydantic models double as the
public schema.

---

## Deployment (one-time)

These steps assume:
- Linux host with the 10 PBAP tool environments already installed.
- An env called `ml` (or whichever you set in `PBAP_RUN_ENV`) that has
  the orchestrator's 5 deps (`pandas`, `numpy`, `pyyaml`, `openpyxl`,
  `requests`).
- A Cloudflare account and a domain you control (free tier is fine).

### 1. Clone the repo

If you haven't already:

```bash
git clone https://github.com/Paredes0/pbap.git
cd pbap
```

### 2. Create the backend's own env

The backend runs in its own micromamba env, **separate** from any
per-tool env and from `pbap_orchestrator`:

```bash
micromamba create -n pbap_demo_api python=3.11 pip
micromamba activate pbap_demo_api
pip install -r demo/api/requirements.txt
```

### 3. Configure

```bash
cp demo/api/.env.example demo/api/.env
$EDITOR demo/api/.env
```

Required edits: `PBAP_REPO_ROOT`, `PBAP_RUN_ENV`, `PBAP_JOBS_DIR`. The
rest are sensible defaults.

### 4. Run in the foreground (smoke test)

```bash
cd demo/api
set -a; source .env; set +a
uvicorn server:app --host 127.0.0.1 --port 8000
```

From another shell:

```bash
curl http://127.0.0.1:8000/health
curl -s -X POST http://127.0.0.1:8000/submit \
     -H 'Content-Type: application/json' \
     -d '{"text": "GIGKFLHSAKKFGKAFVGEIMNS\nGIGAVLKVLTTGLPALISWIKRKRQQ", "tools": []}'
```

You should get back a `job_id`. Poll `/status/{job_id}` until it says
`DONE` (usually 30–120 s for 2 peptides), then GET
`/result/{job_id}/report`.

### 5. Install as a systemd service

```bash
sudo cp demo/api/pbap-api.service.example /etc/systemd/system/pbap-api.service
$EDITOR /etc/systemd/system/pbap-api.service   # fix paths if needed
sudo systemctl daemon-reload
sudo systemctl enable --now pbap-api
sudo journalctl -u pbap-api -f
```

### 6. Expose via Cloudflare Tunnel

```bash
# Install cloudflared (skip if already installed)
sudo curl -L -o /usr/local/bin/cloudflared \
    https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64
sudo chmod +x /usr/local/bin/cloudflared

cloudflared tunnel login
cloudflared tunnel create pbap-demo
cloudflared tunnel route dns pbap-demo pbap-demo.<your-domain>.com

cp demo/api/cloudflared.example.yml ~/.cloudflared/config.yml
$EDITOR ~/.cloudflared/config.yml   # fill in TUNNEL_ID and credentials path

sudo cloudflared service install
sudo systemctl enable --now cloudflared
```

Now the API is reachable at `https://pbap-demo.<your-domain>.com`.

### 7. Point the frontend at it

Set the `PBAP_API_BASE` secret on your Hugging Face Space to the
public URL above. See `../frontend/README.md`.

---

## Mitigation shield (operator commitments)

The demo is hosted under a free non-commercial posture. To minimize
legal exposure to upstream tool authors who have not been formally
asked for permission, the deployment **must** preserve these
behaviors out of the box:

1. **Attribution surfaces in every result.** The frontend renders a
   "Tools used in this run" block. Do not strip it.
2. **Takedown contact is visible.** The footer of every frontend
   page shows `noeparedesalf@gmail.com`. The operator commits to
   acting on any takedown request within **24 hours**.
3. **No weights served.** This backend only serves CSV / JSON / HTML
   reports. Do not add endpoints that expose model files.
4. **No login, no tracking, no cookies, no per-user storage.** The
   backend pseudonymizes nothing because it stores nothing. The
   janitor wipes finished jobs after `JANITOR_JOB_TTL_SECONDS`
   (default 24 h).
5. **Rate / cap / queue protect the host.** Defaults: 50 peptides
   per job, 3 jobs / IP / hour, 200 jobs / day, N=1 worker. These
   are tunable but should never be relaxed without re-evaluating
   the load on the host.
6. **Tool allow-list.** `ALLOWED_TOOLS` in `.env` is the single
   place to disable a specific upstream tool (e.g. on a takedown
   request) without redeploying anything else.

See the top-level `THIRD_PARTY_LICENSES.md` and `docs/licenses_audit.md`
for the per-tool legal context this scaffold is built on.

---

## Operational notes

### Capacity

A single PBAP run touches up to 10 tools, several of which load PLM
weights (ESM-2, ProtT5) of 2–4 GB each. On a single GPU with ≤ 12 GB
VRAM, **N=1 worker is the safe default**. With more VRAM, you can
raise `WORKER_COUNT`, but verify with `nvidia-smi` while two heavy
tools run in parallel.

For a typical 10–50 peptide submission, end-to-end wall time on a
mid-range GPU (e.g. RTX 3060 12 GB) lands around 60–180 s. The
`PBAP_RUN_TIMEOUT=600` default leaves a comfortable margin.

### Logs

The backend writes a per-job `run.log` (stdout + stderr of the
orchestrator) into the job's working directory. These are wiped by
the janitor along with everything else. If you need to debug a
failure post-hoc, raise `JANITOR_JOB_TTL_SECONDS` or `tail -f`
`journalctl -u pbap-api`.

### Restart behavior

Jobs in memory are lost on restart. Users polling a `job_id` after a
restart get `404 Unknown job_id`. The frontend handles this by
re-submitting. For a single-host demo, this is fine; if it ever
matters, swap the dict in `jobs.py` for a Redis-backed store with
the same interface.

### Updating the pipeline

`git pull` in `PBAP_REPO_ROOT` is enough — `runner.py` invokes
`scripts/run_audit.py` afresh per job, so the new code takes effect
on the next submission with no service restart needed. Restart only
if `audit_lib/` changed in a way that affects the orchestrator's own
imports (rare).

---

## Troubleshooting

| Symptom | First thing to check |
|---|---|
| `/submit` returns `429` | You hit a rate limit. Check `/health.rate.jobs_last_24h`. |
| `/submit` returns `400` | Validation. Common: too many peptides, non-standard residues, length out of range. |
| Job sits in `PENDING` forever | Worker thread dead — check `journalctl -u pbap-api` for tracebacks. |
| Job ends in `FAILED` with `Launcher missing: 'micromamba'` | The uvicorn process can't find micromamba on PATH. systemd and SSH non-interactive shells do NOT load `~/.bashrc`. Two fixes (do both for robustness): (1) set `PBAP_MICROMAMBA_BIN=/absolute/path/to/micromamba` in `.env`; (2) add `PATH=${HOME}/bin:${PATH}` (or wherever micromamba lives) to `.env` so the subprocess chain inherits it — `audit_lib/tool_runner.py` also spawns `micromamba run` internally and depends on PATH. |
| `tool_health` shows `error_batch_failed` with `numpy.AxisError: axis 1 is out of bounds` | Several upstream tools assume ≥2 peptides per batch (their feature-concatenation step uses `np.concatenate(..., axis=1)` which is invalid on 1-D arrays). Workaround: submit at least 2 sequences. This is a tool-side bug, not a demo bug. |
| Job ends in `TIMEOUT` | Bump `PBAP_RUN_TIMEOUT` or reduce the tool list / peptide count. |
| `404` from public URL but works on `127.0.0.1` | Cloudflare Tunnel not running. `systemctl status cloudflared`. |
