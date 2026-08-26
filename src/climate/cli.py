"""climate pipeline CLI: acquire → ingest → check → analyze → export."""

import typer

app = typer.Typer(no_args_is_help=True, help=__doc__)

REGION_HELP = "Region id from stations/*.yaml (e.g. la) or 'all'"


@app.command()
def acquire(
    region: str = typer.Option("all", help=REGION_HELP),
    refresh: bool = typer.Option(False, help="Re-fetch files that changed upstream (nightly)"),
    force: bool = typer.Option(False, help="Re-download everything"),
) -> None:
    """Download GHCN-Daily station files and record provenance manifests."""
    from climate.acquire.ghcnd import run_acquire

    run_acquire(region=region, refresh=refresh, force=force)


@app.command()
def stations(
    region: str = typer.Option("us", help="Region id to (re)generate, e.g. us"),
    min_span: int = typer.Option(50, help="Minimum years spanned by TMAX and TMIN"),
    tier: str = typer.Option("", help="'hourly' generates stations/hourly.yaml from GHCNh"),
) -> None:
    """Generate stations/<region>.yaml (or stations/isd.yaml) from NOAA's inventories."""
    if tier == "hourly":
        from climate.ghcnh import write_list

        n = write_list(min_years=20)
        print(f"  wrote stations/hourly.yaml with {n} stations")
        return
    from climate.stations import write_region

    n = write_region(region_id=region, min_span=min_span)
    print(f"  wrote stations/{region}.yaml with {n} stations")


@app.command()
def hourly(
    stage: str = typer.Argument(..., help="acquire | ingest | analyze | export"),
    only: str = typer.Option("", help="Comma-separated WBANs or GHCN ids to restrict to"),
    refresh: bool = typer.Option(False, help="Re-fetch the current year's files"),
) -> None:
    """The ISD hourly tier: same stages, separate data."""
    from climate.hourly import run_stage

    run_stage(stage, only=[x for x in only.split(",") if x], refresh=refresh)


@app.command()
def ingest(region: str = typer.Option("all", help=REGION_HELP)) -> None:
    """Parse raw files into Parquet + DuckDB views."""
    from climate.ingest.runner import run_ingest

    run_ingest(region=region)


@app.command()
def check(
    strict: bool = typer.Option(False, help="Exit 1 on any anomaly (gates the nightly deploy)"),
) -> None:
    """Run data-quality checks and regenerate DATA_QUALITY.md."""
    from climate.quality.runner import run_checks

    run_checks(strict=strict)


@app.command()
def analyze(region: str = typer.Option("all", help=REGION_HELP)) -> None:
    """Compute annual/monthly/daily metrics per station."""
    from climate.analysis.runner import run_analysis

    run_analysis(region=region)


@app.command()
def export(region: str = typer.Option("all", help=REGION_HELP)) -> None:
    """Write the site's JSON (site/static/data/)."""
    from climate.analysis.export import run_export

    run_export(region=region)


if __name__ == "__main__":
    app()
