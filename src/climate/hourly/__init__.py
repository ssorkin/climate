"""ISD-Lite hourly tier: acquire -> ingest -> analyze -> export, separate from the daily pipeline."""

from __future__ import annotations


def run_stage(stage: str, only: list[str] | None = None, refresh: bool = False) -> None:
    only = only or None
    if stage == "acquire":
        from climate.hourly.acquire import run_acquire

        run_acquire(only=only, refresh=refresh)
    elif stage == "ingest":
        from climate.hourly.ingest import run_ingest

        run_ingest(only=only)
    elif stage == "analyze":
        from climate.hourly.analyze import run_analyze

        run_analyze(only=only)
    elif stage == "export":
        from climate.hourly.export import run_export

        run_export(only=only)
    else:
        raise SystemExit(f"unknown stage {stage!r}")
