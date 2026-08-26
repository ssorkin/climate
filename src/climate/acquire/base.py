"""Shared download machinery: HTTP client, streaming downloads, provenance manifests.

Every downloaded file gets a manifest entry (manifests/<dataset>.json) recording the
exact URL, size, SHA-256, timestamps, so any published number can be traced back to a
byte-identical source file. Downloads are idempotent: a file whose manifest entry and
on-disk size match is skipped unless `refresh` (conditional re-fetch) or `force`.
"""

from __future__ import annotations

import hashlib
import json
import threading
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

import httpx

from climate.paths import MANIFEST_DIR, RAW_DIR

USER_AGENT = (
    "climate.sorkinlabs.com/0.1 (open-source climate data project; "
    "https://github.com/ssorkin/climate; ssorkin@gmail.com)"
)

_client: httpx.Client | None = None
_manifest_lock = threading.Lock()


def client() -> httpx.Client:
    global _client
    if _client is None:
        _client = httpx.Client(
            headers={"User-Agent": USER_AGENT},
            timeout=httpx.Timeout(30.0, read=300.0),
            follow_redirects=True,
        )
    return _client


@dataclass
class ManifestEntry:
    dataset: str
    filename: str
    url: str
    sha256: str
    size: int
    downloaded_at: str
    last_modified: str = ""
    note: str = ""


def _manifest_path(dataset: str) -> Path:
    return MANIFEST_DIR / f"{dataset}.json"


# Manifests are cached in memory during a run: bulk downloads (thousands of files) update
# them from several threads, and rewriting a multi-MB JSON per file is wasteful.
_manifests: dict[str, dict[str, dict]] = {}
_dirty: set[str] = set()
_since_flush = 0
FLUSH_EVERY = 50


def load_manifest(dataset: str) -> dict[str, dict]:
    with _manifest_lock:
        if dataset not in _manifests:
            path = _manifest_path(dataset)
            _manifests[dataset] = json.loads(path.read_text()) if path.exists() else {}
        return _manifests[dataset]


def save_manifest(dataset: str, manifest: dict[str, dict] | None = None) -> None:
    """Atomic write (tmp + rename) of the dataset's manifest."""
    with _manifest_lock:
        if manifest is not None:
            _manifests[dataset] = manifest
        data = _manifests.get(dataset, {})
        path = _manifest_path(dataset)
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(dict(sorted(data.items())), indent=2) + "\n")
        tmp.replace(path)
        _dirty.discard(dataset)


def flush_manifests() -> None:
    for dataset in list(_dirty):
        save_manifest(dataset)


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def download(
    dataset: str,
    url: str,
    filename: str | None = None,
    note: str = "",
    throttle_seconds: float = 1.0,
    force: bool = False,
    refresh: bool = False,
    quiet: bool = False,
) -> Path | None:
    """Stream-download url into data/raw/<dataset>/ and record a manifest entry.

    `refresh` sends If-Modified-Since from the manifest so unchanged upstream files
    cost one 304. Returns the local path, or None if the download failed — in which
    case the previous file and manifest entry are left untouched.
    """
    filename = filename or url.rsplit("/", 1)[-1]
    dest_dir = RAW_DIR / dataset
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / filename

    manifest = load_manifest(dataset)
    entry = manifest.get(filename)
    cached = bool(entry) and dest.exists() and dest.stat().st_size == entry["size"]
    if cached and not force and not refresh:
        return dest

    headers = {}
    if cached and refresh and not force and entry.get("last_modified"):
        headers["If-Modified-Since"] = entry["last_modified"]

    tmp = dest.with_suffix(dest.suffix + f".{threading.get_ident()}.part")
    last_error: Exception | None = None
    for attempt in range(3):
        h = hashlib.sha256()
        try:
            with client().stream("GET", url, headers=headers) as resp:
                if resp.status_code == 304:
                    return dest
                resp.raise_for_status()
                last_modified = resp.headers.get("last-modified", "")
                with tmp.open("wb") as f:
                    for chunk in resp.iter_bytes(1 << 20):
                        h.update(chunk)
                        f.write(chunk)
            last_error = None
            break
        except httpx.HTTPError as exc:
            tmp.unlink(missing_ok=True)
            last_error = exc
            if isinstance(exc, httpx.HTTPStatusError) and exc.response.status_code == 404:
                break
            time.sleep(2 * (attempt + 1))
    if last_error is not None:
        is404 = (
            isinstance(last_error, httpx.HTTPStatusError) and last_error.response.status_code == 404
        )
        if not (quiet and is404):
            print(f"  FAILED {url}: {last_error}", flush=True)
        return None

    tmp.replace(dest)
    global _since_flush
    manifest = load_manifest(dataset)
    with _manifest_lock:
        manifest[filename] = ManifestEntry(
            dataset=dataset,
            filename=filename,
            url=url,
            sha256=h.hexdigest(),
            size=dest.stat().st_size,
            downloaded_at=datetime.now(UTC).isoformat(timespec="seconds"),
            last_modified=last_modified,
            note=note,
        ).__dict__
        _dirty.add(dataset)
        _since_flush += 1
        flush = _since_flush >= FLUSH_EVERY
        if flush:
            _since_flush = 0
    if flush:
        save_manifest(dataset)
    if not quiet:
        print(f"  ok {filename} ({dest.stat().st_size:,} bytes)", flush=True)
    if throttle_seconds:
        time.sleep(throttle_seconds)
    return dest
