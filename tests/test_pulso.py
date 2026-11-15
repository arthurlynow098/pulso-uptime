import asyncio
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

import pytest

from pulso.checker import Result, Site, append_history, check_all, check_sync, uptime
from pulso.page import render


class _Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/ok":
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"tudo certo por aqui")
        else:
            self.send_response(503)
            self.end_headers()

    def log_message(self, *a):
        pass


@pytest.fixture
def server():
    srv = HTTPServer(("127.0.0.1", 0), _Handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{srv.server_port}"
    srv.shutdown()


def test_site_no_ar(server):
    r = check_sync(Site("ok", f"{server}/ok", expect_text="tudo certo"))
    assert r.up and r.status == 200 and r.latency_ms is not None


def test_status_errado(server):
    r = check_sync(Site("ruim", f"{server}/quebrado"))
    assert not r.up and r.status == 503


def test_texto_esperado_ausente(server):
    r = check_sync(Site("ok", f"{server}/ok", expect_text="não tem isso"))
    assert not r.up and "não encontrado" in r.error


def test_host_inexistente():
    r = check_sync(Site("nada", "http://127.0.0.1:1/", timeout=2))
    assert not r.up and r.status is None


def test_concorrencia_mantem_a_ordem(server):
    sites = [Site(f"s{i}", f"{server}/ok") for i in range(8)]
    results = asyncio.run(check_all(sites, concurrency=3))
    assert [r.name for r in results] == [f"s{i}" for i in range(8)]


def test_historico_e_uptime(tmp_path):
    f = tmp_path / "pasta-nova" / "h.json"  # a pasta ainda não existe de propósito
    append_history(f, [Result("a", "u", True, 200, 10)])
    hist = append_history(f, [Result("a", "u", False, 500, 10)])
    assert uptime(hist["a"]) == 50.0


def test_pagina_escapa_nome():
    html = render({"<script>x</script>": [{"up": True, "status": 200, "latency_ms": 5, "checked_at": "agora"}]})
    assert "<script>x</script>" not in html and "&lt;script&gt;" in html
