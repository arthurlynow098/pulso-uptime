"""Checagem de disponibilidade com asyncio.

Uso asyncio aqui (e não threads, como no portscan) para praticar a outra
forma de fazer I/O concorrente em Python. Para chamadas HTTP bloqueantes
do urllib eu uso asyncio.to_thread, e o Semaphore limita quantas rodam juntas.
"""
from __future__ import annotations

import asyncio
import json
import ssl
import time
import urllib.error
import urllib.request
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path


@dataclass
class Site:
    name: str
    url: str
    expect_status: int = 200
    expect_text: str = ""
    timeout: float = 10.0


@dataclass
class Result:
    name: str
    url: str
    up: bool
    status: int | None
    latency_ms: float | None
    error: str = ""
    checked_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat(timespec="seconds"))


def load_sites(path: str | Path) -> list[Site]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    return [Site(**item) for item in data["sites"]]


def check_sync(site: Site) -> Result:
    req = urllib.request.Request(site.url, headers={"User-Agent": "pulso-uptime/1.0"})
    started = time.perf_counter()
    try:
        with urllib.request.urlopen(req, timeout=site.timeout, context=ssl.create_default_context()) as resp:
            body = resp.read(200_000).decode("utf-8", errors="replace")
            status = resp.status
    except urllib.error.HTTPError as err:
        status, body = err.code, ""
    except (urllib.error.URLError, TimeoutError, OSError) as err:
        reason = getattr(err, "reason", err)
        return Result(site.name, site.url, False, None, None, str(reason)[:120])
    latency = round((time.perf_counter() - started) * 1000, 1)
    if status != site.expect_status:
        return Result(site.name, site.url, False, status, latency, f"esperava {site.expect_status}")
    if site.expect_text and site.expect_text not in body:
        return Result(site.name, site.url, False, status, latency, f"texto {site.expect_text!r} não encontrado")
    return Result(site.name, site.url, True, status, latency)


async def check_all(sites: list[Site], concurrency: int = 10, check=check_sync) -> list[Result]:
    sem = asyncio.Semaphore(concurrency)

    async def one(site: Site) -> Result:
        async with sem:
            return await asyncio.to_thread(check, site)

    return list(await asyncio.gather(*(one(s) for s in sites)))


def append_history(path: str | Path, results: list[Result], keep: int = 500) -> dict[str, list[dict]]:
    """Guarda as últimas N checagens de cada site em JSON, para calcular uptime."""
    path = Path(path)
    history: dict[str, list[dict]] = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    for r in results:
        history.setdefault(r.name, []).append(asdict(r))
        history[r.name] = history[r.name][-keep:]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(history, ensure_ascii=False, indent=1), encoding="utf-8")
    return history


def uptime(entries: list[dict]) -> float:
    return round(100 * sum(e["up"] for e in entries) / len(entries), 2) if entries else 0.0
