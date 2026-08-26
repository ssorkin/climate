"""Run all data-quality checks and generate DATA_QUALITY.md."""

from __future__ import annotations

from pathlib import Path

import yaml

from climate.analysis.metrics import today_utc
from climate.paths import KNOWN_ISSUES_DIR, REPO_ROOT
from climate.quality.checks import ALL_CHECKS, Finding

REPORT_PATH = REPO_ROOT / "DATA_QUALITY.md"

SEVERITY_ORDER = {"anomaly": 0, "warning": 1, "info": 2}
SEVERITY_MARK = {"anomaly": "🔴", "warning": "🟡", "info": "ℹ️"}


def load_known_issues() -> list[dict]:
    return [yaml.safe_load(p.read_text()) for p in sorted(KNOWN_ISSUES_DIR.glob("*.yaml"))]


def render(findings: list[Finding], issues: list[dict]) -> str:
    lines = [
        "# Data Quality Report",
        "",
        (
            f"Generated {today_utc().isoformat()} by `clim check`. "
            "Problems in the source data are surfaced here and in `known_issues/`, never "
            "silently patched. Anomalies block the nightly deploy."
        ),
        "",
        "## Known issues (documented registry)",
        "",
    ]
    for issue in issues:
        years = ", ".join(str(y) for y in issue.get("years", []))
        lines += [
            f"### {issue['title']}",
            "",
            f"*{issue['kind']}, {issue['dataset']} {years}* — id `{issue['id']}`",
            "",
            " ".join(issue["description"].split()),
            "",
            f"**Handling:** {' '.join(issue['handling'].split())}",
            "",
        ]
    lines += ["## Check findings", ""]
    current = None
    for f in findings:
        if f.check != current:
            current = f.check
            lines += [f"### {f.check}", ""]
        year = f" **{f.year}**" if f.year else ""
        lines.append(f"- {SEVERITY_MARK[f.severity]}{year} {f.message}")
        for ex in f.details.get("examples", []):
            lines.append(f"  - {ex}")
    lines.append("")
    return "\n".join(lines)


def run_checks(strict: bool = False, report_path: Path = REPORT_PATH) -> list[Finding]:
    findings: list[Finding] = []
    for check in ALL_CHECKS:
        print(f"  running {check.__name__} …")
        findings.extend(check())
    findings.sort(key=lambda f: (SEVERITY_ORDER[f.severity], f.check, f.entity, f.year or 0))
    report_path.write_text(render(findings, load_known_issues()))
    n_anom = sum(1 for f in findings if f.severity == "anomaly")
    n_warn = sum(1 for f in findings if f.severity == "warning")
    print(f"  {len(findings)} findings ({n_anom} anomalies, {n_warn} warnings)")
    print(f"  wrote {report_path.relative_to(REPO_ROOT)}")
    if strict and n_anom:
        raise SystemExit(f"check --strict: {n_anom} anomalies — not deploying")
    return findings
