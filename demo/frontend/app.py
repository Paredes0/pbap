"""
demo/frontend/app.py — Gradio app for the public PBAP demo.

Designed to run on a free Hugging Face Space (CPU tier is enough; this
process does no compute beyond HTTP). The heavy lifting lives on the
operator's Linux backend reached via `PBAP_API_BASE`.

Set as Space secrets (Settings → Variables and secrets):
    PBAP_API_BASE     e.g. https://pbap-demo.<your-domain>.com
    CONTACT_EMAIL     e.g. noeparedesalf@gmail.com   (visible in footer)
    DEMO_VERSION      optional; surfaces under "About"

This file is intentionally a single module so it can be dropped into
a Space's repo root unchanged.
"""
from __future__ import annotations

import os
import time
from typing import Any

import gradio as gr
import httpx


PBAP_API_BASE = os.environ.get("PBAP_API_BASE", "http://127.0.0.1:8000").rstrip("/")
CONTACT_EMAIL = os.environ.get("CONTACT_EMAIL", "noeparedesalf@gmail.com")
DEMO_VERSION = os.environ.get("DEMO_VERSION", "0.1.0")
POLL_INTERVAL_SECONDS = float(os.environ.get("POLL_INTERVAL_SECONDS", "3"))
POLL_TIMEOUT_SECONDS = int(os.environ.get("POLL_TIMEOUT_SECONDS", "900"))

ALL_TOOLS = [
    ("ToxinPred3 — toxicity",         "toxinpred3"),
    ("AntiBP3 — antibacterial",       "antibp3"),
    ("HemoPI2 — hemolysis",           "hemopi2"),
    ("HemoDL — hemolysis",            "hemodl"),
    ("DeepB3P — blood-brain barrier", "deepb3p"),
    ("DeepBP — anticancer",           "deepbp"),
    ("APEX — MIC across 34 strains",  "apex"),
    ("PerseuCPP — cell-penetrating",  "perseucpp"),
    ("ACP-DPE — anticancer",          "acp_dpe"),
    ("BertAIP — anti-inflammatory",   "bertaip"),
]

EXAMPLE_INPUT = """\
>magainin_2
GIGKFLHSAKKFGKAFVGEIMNS
>melittin
GIGAVLKVLTTGLPALISWIKRKRQQ
>buforin_2
TRSSRAGLQFPVGRVHRLLRK
>LL37
LLGDFFRKSKEKIGKEFKRIVQRIKDFLRNLVPRTES
"""


def _http() -> httpx.Client:
    return httpx.Client(base_url=PBAP_API_BASE, timeout=30.0)


def fetch_health() -> dict[str, Any]:
    try:
        with _http() as c:
            r = c.get("/health")
            r.raise_for_status()
            return r.json()
    except Exception as exc:
        return {"_error": str(exc)}


def health_panel() -> str:
    h = fetch_health()
    if "_error" in h:
        return (
            "**Backend unreachable.** The demo's compute backend is currently "
            f"offline or unreachable from this Space.\n\n`{h['_error']}`"
        )
    lim = h.get("limits", {})
    q = h.get("queue", {})
    r = h.get("rate", {})
    return (
        f"**Limits** · {lim.get('max_peptides_per_job')} peptides/submission · "
        f"{lim.get('jobs_per_ip_per_hour')} jobs/hour/IP · "
        f"{lim.get('daily_global_cap')} jobs/day global\n\n"
        f"**Queue** · {q.get('pending', 0)} pending · "
        f"{q.get('running', 0)} running · "
        f"{q.get('done', 0)} done · "
        f"{q.get('failed_or_timeout', 0)} failed/timeout\n\n"
        f"**Today** · {r.get('jobs_last_24h', 0)} / "
        f"{r.get('daily_cap', '?')} jobs used in the last 24h\n\n"
        f"**Tools enabled** · {', '.join(lim.get('allowed_tools', []))}"
    )


def submit_and_wait(text: str, tools: list[str], progress=gr.Progress(track_tqdm=False)):
    if not text or not text.strip():
        raise gr.Error("Please paste at least one peptide (or a FASTA).")

    payload = {"text": text, "tools": tools}
    try:
        with _http() as c:
            r = c.post("/submit", json=payload)
            if r.status_code == 400:
                raise gr.Error(_extract_detail(r))
            if r.status_code == 429:
                raise gr.Error(_extract_detail(r))
            r.raise_for_status()
            submit_data = r.json()
    except gr.Error:
        raise
    except httpx.HTTPError as exc:
        raise gr.Error(f"Backend error during submit: {exc}") from exc

    job_id = submit_data["job_id"]
    progress(0, desc=_status_line(submit_data))

    deadline = time.time() + POLL_TIMEOUT_SECONDS
    last_status = None
    while time.time() < deadline:
        try:
            with _http() as c:
                r = c.get(f"/status/{job_id}")
                r.raise_for_status()
                st = r.json()
        except httpx.HTTPError as exc:
            raise gr.Error(f"Backend error while polling: {exc}") from exc

        if st["status"] != last_status:
            progress(_progress_value(st), desc=_status_line(st))
            last_status = st["status"]

        if st["status"] == "DONE":
            return _render_done(job_id, st, submit_data)
        if st["status"] in ("FAILED", "TIMEOUT"):
            raise gr.Error(
                f"Job ended with status {st['status']}: "
                f"{st.get('error') or 'no error message'}"
            )
        if st["status"] == "CANCELLED":
            raise gr.Error("Job was cancelled.")

        time.sleep(POLL_INTERVAL_SECONDS)

    raise gr.Error(
        "Timed out waiting for the job to finish. The backend may be busy; "
        "please try again later."
    )


def _extract_detail(r: httpx.Response) -> str:
    try:
        return r.json().get("detail") or r.text
    except Exception:
        return r.text or f"HTTP {r.status_code}"


def _status_line(payload: dict) -> str:
    s = payload.get("status", "?")
    if s == "PENDING":
        qp = payload.get("queue_position")
        if qp is None:
            return "Queued…"
        return f"Queued (position {qp})"
    if s == "RUNNING":
        return "Running the pipeline…"
    return f"Status: {s}"


def _progress_value(payload: dict) -> float:
    s = payload.get("status")
    if s == "PENDING":
        return 0.1
    if s == "RUNNING":
        return 0.5
    if s == "DONE":
        return 1.0
    return 0.0


def _render_done(job_id: str, status: dict, submit_data: dict) -> tuple:
    runtime = status.get("runtime_seconds") or 0.0
    report_url = f"{PBAP_API_BASE}/result/{job_id}/report"
    csv_url = f"{PBAP_API_BASE}/result/{job_id}/csv"
    json_url = f"{PBAP_API_BASE}/result/{job_id}/json"
    health_url = f"{PBAP_API_BASE}/result/{job_id}/health"

    summary = (
        f"### Job `{job_id}` — done in {runtime:.1f} s\n\n"
        f"**{submit_data['n_peptides']} peptides** scored across "
        f"**{len(submit_data['tools'])} tools**: "
        f"{', '.join(submit_data['tools'])}\n\n"
        f"---\n\n"
        f"**Download artifacts:**\n"
        f"- [Full interactive REPORT.html]({report_url})\n"
        f"- [consolidated.csv]({csv_url}) — wide-format predictions table\n"
        f"- [consolidated.json]({json_url}) — nested predictions + extras\n"
        f"- [tool_health_report.json]({health_url}) — per-tool status\n\n"
        "Artifacts are kept on the backend for 24 hours, then deleted."
    )
    # Sandbox the embedded REPORT.html so its scripts cannot reach back
    # into the parent Space's origin. The REPORT.html is generated by the
    # PBAP orchestrator (not user input), so we still allow scripts inside
    # the frame (interactive tables/filters need them) and same-origin so
    # the relative asset paths work, but we deny top-navigation, popups
    # and form submission to keep blast radius minimal.
    iframe = (
        f'<iframe src="{report_url}" '
        'sandbox="allow-scripts allow-same-origin" '
        'referrerpolicy="no-referrer" '
        'style="width:100%;height:780px;border:1px solid #ddd;border-radius:8px;"></iframe>'
    )
    return summary, iframe


# ----------------------------------------------------------------------------
# UI
# ----------------------------------------------------------------------------

ATTRIBUTION_MD = """\
### Tools used in this demo

The pipeline orchestrates 10 published prediction tools. **All credit
for the underlying models goes to their authors.** This demo executes
the tools without modification and links every result to the upstream
source. If you use these results in research, **please cite the
original papers**, not this demo.

| Tool | What it predicts | Upstream |
|---|---|---|
| ToxinPred3 | Toxicity | [raghavagps/toxinpred3](https://github.com/raghavagps/toxinpred3) |
| AntiBP3 | Antibacterial | [raghavagps/AntiBP3](https://github.com/raghavagps/AntiBP3) |
| HemoPI2 | Hemolysis | [raghavagps/hemopi2](https://github.com/raghavagps/hemopi2) |
| HemoDL | Hemolysis | [abcair/HemoDL](https://github.com/abcair/HemoDL) |
| DeepB3P | Blood-brain barrier | [GreatChenLab/deepB3P](https://github.com/GreatChenLab/deepB3P) |
| DeepBP | Anticancer | [Zhou-Jianren/bioactive-peptides](https://github.com/Zhou-Jianren/bioactive-peptides) |
| APEX | MIC across 34 strains | [machine-biology-group-public/apex](https://gitlab.com/machine-biology-group-public/apex) |
| PerseuCPP | Cell-penetrating | [goalmeida05/PERSEU](https://github.com/goalmeida05/PERSEU) |
| ACP-DPE | Anticancer | [CYJ-sudo/ACP-DPE](https://github.com/CYJ-sudo/ACP-DPE) |
| BertAIP | Anti-inflammatory | [ying-jc/BertAIP](https://github.com/ying-jc/BertAIP) |

Source code for this orchestration layer:
**[github.com/Paredes0/pbap](https://github.com/Paredes0/pbap)**
(PolyForm Noncommercial 1.0.0)
"""


DISCLAIMER_MD = f"""\
### About this demo

This is a **free, non-commercial academic demo**. Each integrated tool
retains its own license and copyright; see
[THIRD_PARTY_LICENSES.md](https://github.com/Paredes0/pbap/blob/main/THIRD_PARTY_LICENSES.md)
in the source repo for the per-tool breakdown.

**No login, no cookies, no tracking, no per-user storage.** The
backend wipes job artifacts 24 hours after completion. Peptide
sequences submitted here never leave the operator's host beyond
serving them back to you.

If you are an author of an integrated tool and want it removed from
the demo, write to **{CONTACT_EMAIL}** and it will be disabled within
24 hours.

Predictions are **not medical or clinical advice**. They reflect each
upstream model's training distribution, which may not match yours —
read the *Applicability Domain* discussion in the
[project page](https://paredes0.github.io/pbap/) before trusting any
individual call.

_Demo version: {DEMO_VERSION}_
"""


def build_ui() -> gr.Blocks:
    with gr.Blocks(title="PBAP — Peptide Bioactivity Audit Pipeline (demo)",
                   theme=gr.themes.Soft()) as ui:
        gr.Markdown(
            "# PBAP — Peptide Bioactivity Audit Pipeline\n"
            "*Free, non-commercial demo. Paste up to 50 peptides and get a "
            "consolidated multi-tool report.*\n\n"
            f"📦 Source: [github.com/Paredes0/pbap](https://github.com/Paredes0/pbap) · "
            f"📖 Design: [paredes0.github.io/pbap](https://paredes0.github.io/pbap/) · "
            f"✉️ Contact: {CONTACT_EMAIL}"
        )

        with gr.Row():
            with gr.Column(scale=2):
                input_box = gr.Textbox(
                    label="Input — paste FASTA or one peptide per line",
                    lines=10,
                    placeholder=EXAMPLE_INPUT,
                    value="",
                )
                example_btn = gr.Button("📋 Load 4-peptide example", size="sm")
                tool_check = gr.CheckboxGroup(
                    label="Tools to run (leave all checked for the full audit)",
                    choices=[(lbl, val) for lbl, val in ALL_TOOLS],
                    value=[v for _, v in ALL_TOOLS],
                )
                submit_btn = gr.Button("Run audit", variant="primary")

            with gr.Column(scale=1):
                gr.Markdown("### Backend status")
                health_md = gr.Markdown(health_panel())
                refresh_btn = gr.Button("Refresh status", size="sm")

        gr.Markdown("---")
        gr.Markdown("### Result")
        summary_md = gr.Markdown("*Submit a job to see results here.*")
        report_html = gr.HTML()

        gr.Markdown("---")
        with gr.Accordion("Tools and attribution", open=False):
            gr.Markdown(ATTRIBUTION_MD)
        with gr.Accordion("About this demo / license / takedown", open=False):
            gr.Markdown(DISCLAIMER_MD)

        # Wire up events
        example_btn.click(lambda: EXAMPLE_INPUT, outputs=input_box)
        refresh_btn.click(lambda: health_panel(), outputs=health_md)
        submit_btn.click(
            submit_and_wait,
            inputs=[input_box, tool_check],
            outputs=[summary_md, report_html],
        )

    return ui


if __name__ == "__main__":
    build_ui().queue(default_concurrency_limit=4).launch(
        server_name="0.0.0.0",
        server_port=int(os.environ.get("GRADIO_PORT", "7860")),
    )
