#!/usr/bin/env python3
"""Loopback-only, read-mostly Pala Workspace endpoint."""
from __future__ import annotations
import argparse, json, secrets
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

def snapshot(root: Path) -> dict[str, object]:
    return {"status": "passed", "root": root.name, "active_ticket": None, "next_action": "yerel durumu incele", "automation": "explicit-only", "hooks_trust": "configured-not-verified"}

def serve(root: Path, host: str = "127.0.0.1", port: int = 8765) -> str:
    token = secrets.token_urlsafe(24)
    payload = snapshot(root)
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            if self.path != "/snapshot": self.send_error(404); return
            body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            self.send_response(200); self.send_header("Content-Type", "application/json; charset=utf-8"); self.send_header("Content-Length", str(len(body))); self.end_headers(); self.wfile.write(body)
        def do_POST(self):
            self.send_error(403, "mutation requires explicit local authorization")
        def log_message(self, *_): pass
    server = ThreadingHTTPServer((host, port), Handler)
    server.token = token  # type: ignore[attr-defined]
    print(json.dumps({"status":"passed","host":host,"port":port,"token":token}, ensure_ascii=False))
    server.serve_forever()
    return token

def main() -> int:
    p=argparse.ArgumentParser(description="Pala Workspace loopback server")
    p.add_argument("--cwd", default="."); p.add_argument("--port", type=int, default=8765)
    a=p.parse_args(); serve(Path(a.cwd).resolve(), port=a.port); return 0
if __name__ == "__main__": raise SystemExit(main())
