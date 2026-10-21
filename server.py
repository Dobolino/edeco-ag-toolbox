#!/usr/bin/env python3
"""Lokale Toolbox. Start: python server.py --open"""

from __future__ import annotations

import argparse
import json
import mimetypes
import sys
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse

from toolbox import catalogue, updater
from toolbox.nova import groups_for, read_nzp, stencils_of
from toolbox.store import Store
from toolbox.version import label

def bundle_root() -> Path:
    if getattr(sys, "frozen", False):
        return Path(getattr(sys, "_MEIPASS"))
    return Path(__file__).resolve().parent

WEB = bundle_root() / "web"
PORT = 8770


class App:
    def __init__(self, store: Store):
        self.store = store
        self._dataset_key: tuple[str, int] | None = None
        self._dataset_info: dict | None = None
        self._symbols: list | None = None
        self.shutdown = lambda: None

    def dataset(self) -> tuple[dict, list]:
        path = Path(self.store.settings()["dataset"])
        if not str(path):
            raise ValueError("Zuerst den Pfad zum Nova-Datensatz speichern.")
        stamp = path.stat().st_mtime_ns
        key = (str(path), stamp)
        if self._dataset_key != key:
            self._dataset_info, self._symbols = read_nzp(path)
            self._dataset_key = key
        return self._dataset_info, self._symbols or []

    def catalogue_path(self) -> Path:
        raw = self.store.settings()["catalogue"]
        if not raw:
            raise ValueError("Zuerst den Pfad zum Steiger-Katalog speichern.")
        return Path(raw)


def make_handler(app: App):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, fmt: str, *args) -> None:
            return

        def do_GET(self) -> None:
            url = urlparse(self.path)
            query = parse_qs(url.query)
            try:
                if url.path == "/api/status":
                    return self._json({"name": "edeco Toolbox", "version_label": label()})
                if url.path == "/api/update":
                    return self._json(updater.check().to_dict())
                if url.path == "/api/bookmarks":
                    return self._json(app.store.bookmarks())
                if url.path == "/api/settings":
                    return self._json(_settings_view(app))
                if url.path == "/api/stencils":
                    info, symbols = app.dataset()
                    return self._json({"dataset": info, "stencils": stencils_of(symbols)})
                if url.path == "/api/groups":
                    _, symbols = app.dataset()
                    stencil = query.get("stencil", [""])[0]
                    return self._json({"groups": [group.to_dict() for group in groups_for(symbols, stencil)]})
                if url.path == "/api/links":
                    return self._json(app.store.links())
                if url.path == "/api/catalogue/search":
                    found = catalogue.search(app.catalogue_path(), query.get("q", [""])[0])
                    return self._json({"results": found})
                if url.path.startswith("/api/"):
                    return self._json({"error": "Unbekannte Schnittstelle"}, 404)
                self._file(url.path)
            except ValueError as exc:
                self._json({"error": str(exc)}, 400)
            except Exception:
                self._json({"error": "Die Anfrage konnte nicht verarbeitet werden."}, 500)

        def do_POST(self) -> None:
            try:
                body = self._body()
                path = urlparse(self.path).path
                if path == "/api/update/install":
                    return self._json(_install_update(app))
                if path == "/api/bookmarks":
                    return self._json(app.store.add_bookmark(body.get("title", ""), body.get("url", ""), body.get("note", "")))
                if path == "/api/bookmarks/update":
                    return self._json(app.store.update_bookmark(int(body["id"]), body.get("title", ""), body.get("url", ""), body.get("note", "")))
                if path == "/api/bookmarks/delete":
                    app.store.delete_bookmark(int(body["id"]))
                    return self._json({"ok": True})
                if path == "/api/bookmarks/restore":
                    return self._json(app.store.restore_seeds())
                if path == "/api/settings":
                    saved = app.store.save_settings(str(body.get("catalogue", "")), str(body.get("dataset", "")))
                    return self._json(_settings_view(app, saved))
                if path == "/api/links":
                    return self._json(_save_link(app, body))
                if path == "/api/links/delete":
                    app.store.delete_link(int(body["id"]))
                    return self._json({"ok": True})
                self._json({"error": "Unbekannte Schnittstelle"}, 404)
            except (ValueError, KeyError, TypeError) as exc:
                self._json({"error": str(exc)}, 400)
            except Exception:
                self._json({"error": "Die Anfrage konnte nicht verarbeitet werden."}, 500)

        def _body(self) -> dict:
            length = int(self.headers.get("Content-Length", "0"))
            if length <= 0 or length > 1_000_000:
                raise ValueError("Die Anfrage ist leer oder zu gross.")
            data = json.loads(self.rfile.read(length))
            if not isinstance(data, dict):
                raise ValueError("JSON-Objekt erwartet.")
            return data

        def _file(self, path: str) -> None:
            relative = unquote(path).lstrip("/") or "index.html"
            target = (WEB / relative).resolve()
            if not target.is_relative_to(WEB.resolve()) or not target.is_file():
                self._json({"error": "Seite nicht gefunden"}, 404)
                return
            content = target.read_bytes()
            kind = mimetypes.guess_type(target.name)[0] or "application/octet-stream"
            if target.suffix in {".html", ".js", ".css"}:
                kind += "; charset=utf-8"
            self.send_response(200)
            self.send_header("Content-Type", kind)
            self.send_header("Content-Length", str(len(content)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(content)

        def _json(self, payload, status: int = 200) -> None:
            data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(data)

    return Handler


def _settings_view(app: App, saved: dict | None = None) -> dict:
    settings = saved or app.store.settings()
    view = {**settings, "catalogue_status": "", "dataset_status": ""}
    if settings["catalogue"]:
        try:
            info = catalogue.summary(Path(settings["catalogue"]))
            view["catalogue_status"] = f"Katalog {info['year'] or 'ohne Jahr'}, {info['articles']} Artikel"
            view["catalogue_year"] = info["year"]
        except (ValueError, sqlite3_error()) as exc:
            view["catalogue_status"] = str(exc)
    if settings["dataset"]:
        try:
            info, symbols = app.dataset()
            view["dataset_status"] = f"{info['name']} {info['version']}, {len(symbols)} Symbole"
        except (ValueError, OSError) as exc:
            view["dataset_status"] = str(exc)
    return view


def sqlite3_error():
    import sqlite3
    return sqlite3.Error


def _save_link(app: App, body: dict) -> dict:
    checked = catalogue.require_variant(app.catalogue_path(), body.get("article_number", ""), body.get("va", ""))
    _, symbols = app.dataset()
    key = str(body.get("nova_key") or "")
    group = next((item for item in groups_for(symbols) if item.key == key), None)
    if group is None:
        raise ValueError("Dieses Nova-Symbol ist im geladenen Datensatz nicht vorhanden.")
    return app.store.save_link({
        "nova_key": group.key,
        "dataset": group.dataset,
        "title": group.title,
        "mounting": group.mounting or "",
        "items": group.items,
        "steiger_year": checked["year"],
        "article_number": checked["number"],
        "article_name": checked["name"],
        "va": checked["va"],
        "unit": body.get("unit", ""),
        "bkp": body.get("bkp", ""),
    })


def _install_update(app: App) -> dict:
    info = updater.check()
    if not info.available or not info.can_install:
        raise ValueError(info.message or "Kein Update bereit.")
    setup = updater.download(info)
    updater.install(setup, app.shutdown)
    return info.to_dict()


def _notify(message: str) -> None:
    if sys.platform == "win32":
        import ctypes
        ctypes.windll.user32.MessageBoxW(0, message, "edeco Toolbox", 0x10)
    else:
        print(message, file=sys.stderr, flush=True)


def serve(port: int = PORT, open_browser: bool = False, store: Store | None = None) -> int:
    app = App(store or Store())
    try:
        server = ThreadingHTTPServer(("127.0.0.1", port), make_handler(app))
    except OSError as exc:
        _notify(f"Die Toolbox läuft bereits oder Port {port} ist belegt.\n{exc}")
        return 1
    app.shutdown = server.shutdown
    url = f"http://127.0.0.1:{port}"
    print(f"edeco Toolbox: {url}  (Beenden mit Strg+C)", flush=True)
    if open_browser:
        webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="edeco Toolbox lokal starten")
    parser.add_argument("--port", type=int, default=PORT)
    parser.add_argument("--open", action="store_true")
    args = parser.parse_args()
    serve(args.port, args.open)
