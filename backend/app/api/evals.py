"""Evals API — run the benchmark and fetch results."""
from __future__ import annotations

import json

from fastapi import APIRouter, HTTPException

from ..evals.reports import reports_dir
from ..evals.runner import run_evals

router = APIRouter(prefix="/evals", tags=["evals"])


@router.post("/run")
def run() -> dict:
    report = run_evals()
    return report.to_dict()


@router.get("/results")
def results() -> dict:
    latest = reports_dir() / "latest.json"
    if not latest.exists():
        raise HTTPException(status_code=404, detail="No eval results yet. Run /evals/run first.")
    return json.loads(latest.read_text())
