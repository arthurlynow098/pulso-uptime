from __future__ import annotations

import argparse
import asyncio
import json
import time
import urllib.request
from pathlib import Path

from .checker import append_history, check_all, load_sites, uptime
from .page import render


def notify(webhook: str, down: list) -> None:
    """Manda um aviso para um webhook do Discord (formato simples de content)."""
    text = "\n".join(f"🔴 {r.name} fora do ar, {r.error or r.status}" for r in down)
    req = urllib.request.Request(webhook, data=json.dumps({"content": text}).encode(),
                                 headers={"Content-Type": "application/json"})
    try:
        urllib.request.urlopen(req, timeout=10).close()
    except OSError as exc:
        print(f"  não consegui avisar no webhook ({exc})")


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="pulso", description="Monitor de disponibilidade com página de status.")
    p.add_argument("config", help="arquivo JSON com a lista de sites")
    p.add_argument("--historico", default="historico.json")
    p.add_argument("--pagina", default="status/index.html", help="onde salvar a página de status")
    p.add_argument("--intervalo", type=int, default=0, help="segundos entre rodadas, 0 roda uma vez só")
    p.add_argument("--webhook", help="URL de webhook do Discord para avisar quando cair")
    return p


def run_once(args, sites) -> bool:
    results = asyncio.run(check_all(sites))
    history = append_history(args.historico, results)
    Path(args.pagina).parent.mkdir(parents=True, exist_ok=True)
    Path(args.pagina).write_text(render(history), encoding="utf-8")
    print()
    for r in results:
        mark = "UP  " if r.up else "DOWN"
        lat = f"{r.latency_ms:>7.0f} ms" if r.latency_ms is not None else "       --"
        print(f"  {mark} {r.name:<22}{lat}   uptime {uptime(history[r.name]):>6}%  {r.error}")
    down = [r for r in results if not r.up]
    if down and args.webhook:
        notify(args.webhook, down)
    print(f"\n  página gerada em {args.pagina}")
    return not down


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    sites = load_sites(args.config)
    if not args.intervalo:
        return 0 if run_once(args, sites) else 1
    while True:
        run_once(args, sites)
        time.sleep(args.intervalo)
