#!/usr/bin/env python3
"""PokoScrap MCP Stdio Server.
Connects Claude Desktop, Cursor, Antigravity, and other MCP clients
directly to PokoScrap via standard input/output (stdio JSON-RPC).

Usage:
  python3 -m server.mcp_server
or
  POKOSCRAP_API_KEY=psk_... POKOSCRAP_API_URL=http://127.0.0.1:8877 python3 server/mcp_server.py
"""
import sys
import json
import os
from pathlib import Path
import urllib.request
import urllib.error

# Ensure outputs/pokoscrap is in sys.path
root_dir = Path(__file__).resolve().parents[1]
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

API_URL = os.getenv("POKOSCRAP_API_URL", "").rstrip("/")
API_KEY = os.getenv("POKOSCRAP_API_KEY", "")


def send_response(response: dict):
    line = json.dumps(response, ensure_ascii=False)
    sys.stdout.write(line + "\n")
    sys.stdout.flush()


def forward_to_api(request_data: dict) -> dict:
    url = f"{API_URL}/api/mcp"
    headers = {
        "Content-Type": "application/json",
        "X-Poko-Request": "1"
    }
    if API_KEY:
        headers["Authorization"] = f"Bearer {API_KEY}"

    data = json.dumps(request_data).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        err_body = e.read().decode("utf-8", errors="replace")
        return {
            "jsonrpc": "2.0",
            "id": request_data.get("id"),
            "error": {
                "code": -32603,
                "message": f"HTTP {e.code}: {err_body}"
            }
        }
    except Exception as e:
        return {
            "jsonrpc": "2.0",
            "id": request_data.get("id"),
            "error": {
                "code": -32603,
                "message": f"Koneksi ke PokoScrap API ({url}) gagal: {str(e)}"
            }
        }


def handle_locally(request_data: dict) -> dict:
    from server import db, mcp
    with db.transaction(unscoped=True) as conn:
        org = conn.execute(db.organizations.select().limit(1)).mappings().first()
        tid = org["id"] if org else "local-tenant"
        user = {"name": "MCP Agent", "id": "mcp-agent", "tenant_id": tid, "roles": ["Owner", "Admin"]}
        token = db.tenant_context.set(tid)
        try:
            return mcp.handle_mcp_message(request_data, user)
        finally:
            db.tenant_context.reset(token)


def process_message(request_data: dict) -> dict:
    if API_URL and API_KEY:
        return forward_to_api(request_data)
    else:
        try:
            return handle_locally(request_data)
        except Exception:
            if API_URL:
                return forward_to_api(request_data)
            raise


def main():
    global API_KEY, API_URL
    args = sys.argv[1:]
    for i, arg in enumerate(args):
        if arg == "--api-key" and i + 1 < len(args):
            API_KEY = args[i + 1]
        elif arg == "--url" and i + 1 < len(args):
            API_URL = args[i + 1].rstrip("/")

    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            req = json.loads(line)
            res = process_message(req)
            send_response(res)
        except json.JSONDecodeError:
            send_response({
                "jsonrpc": "2.0",
                "id": None,
                "error": {"code": -32700, "message": "Invalid JSON format"}
            })
        except Exception as e:
            send_response({
                "jsonrpc": "2.0",
                "id": None,
                "error": {"code": -32603, "message": str(e)}
            })


if __name__ == "__main__":
    main()
