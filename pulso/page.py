"""Gera a página de status em HTML estático, pronta para publicar em qualquer lugar."""
from __future__ import annotations

from datetime import datetime
from html import escape

from .checker import uptime

TEMPLATE = """<!doctype html>
<html lang="pt-BR"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Status</title>
<style>
:root{{--f:#0b0b0b;--p:#151515;--l:#262626;--t:#f5f1e6;--m:#8a867c;--ok:#22c55e;--no:#f43f5e}}
*{{box-sizing:border-box}}body{{margin:0;background:var(--f);color:var(--t);font:16px/1.5 system-ui,sans-serif}}
main{{max-width:820px;margin:0 auto;padding:40px 16px}}h1{{margin:0;font-size:32px;letter-spacing:-1px}}
.geral{{padding:16px 20px;border-radius:12px;margin:24px 0;font-weight:700}}
.verde{{background:#0f2e1b;border:1px solid var(--ok)}}.vermelho{{background:#3a1220;border:1px solid var(--no)}}
.site{{background:var(--p);border:1px solid var(--l);border-radius:12px;padding:16px 20px;margin-bottom:12px}}
.cab{{display:flex;justify-content:space-between;gap:12px;flex-wrap:wrap}}.m{{color:var(--m);font-size:14px}}
.barras{{display:flex;gap:2px;margin-top:12px;height:28px}}.b{{flex:1;border-radius:2px;background:var(--ok)}}.b.x{{background:var(--no)}}
.b.v{{background:var(--l)}}footer{{color:var(--m);font-size:13px;margin-top:32px}}
</style></head><body><main>
<h1>Status dos serviços</h1><p class="m">atualizado em {updated}</p>
<div class="geral {general_class}">{general}</div>
{sites}
<footer>gerado pelo pulso-uptime</footer>
</main></body></html>
"""


def render(history: dict[str, list[dict]], bars: int = 60) -> str:
    blocks, all_up = [], True
    for name, entries in sorted(history.items()):
        last = entries[-1]
        all_up &= last["up"]
        recent = entries[-bars:]
        cells = ['<div class="b v"></div>'] * (bars - len(recent)) + [
            f'<div class="b{"" if e["up"] else " x"}" title="{escape(e["checked_at"])}"></div>' for e in recent
        ]
        state = "operacional" if last["up"] else f"fora do ar ({escape(last.get('error') or str(last.get('status')))})"
        latency = f'{last["latency_ms"]:.0f} ms' if last.get("latency_ms") is not None else "sem resposta"
        blocks.append(
            f'<div class="site"><div class="cab"><strong>{escape(name)}</strong>'
            f'<span class="m">{state} · {latency} · {uptime(entries)}% de uptime</span></div>'
            f'<div class="barras">{"".join(cells)}</div></div>'
        )
    return TEMPLATE.format(
        updated=datetime.now().strftime("%d/%m/%Y %H:%M"),
        general_class="verde" if all_up else "vermelho",
        general="Todos os sistemas operacionais" if all_up else "Algum serviço está com problema",
        sites="\n".join(blocks),
    )
