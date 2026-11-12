"""Model Context Protocol (MCP) Implementation for PokoScrap.
Enables AI assistants (Claude, Cursor, Antigravity, ChatGPT, custom agents)
to interact directly with PokoScrap leads, jobs, pipelines, and exports.
"""
import json
import re
from typing import Any, Dict, List, Optional
from sqlalchemy import func, select, or_, and_

from . import db
from .core import COUNTRIES, PIPELINES, now, clean


MCP_TOOLS = [
    {
        "name": "pokoscrap_search_leads",
        "description": "Cari data lead bisnis di database PokoScrap berdasarkan kata kunci, negara asal, status pipeline, atau kelengkapan kontak (telepon, WhatsApp, email).",
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Kata kunci pencarian (nama bisnis, produk, kategori, alamat)"
                },
                "origin": {
                    "type": "string",
                    "description": "Kode 2 huruf negara asal lead (misal: ID untuk Indonesia, MY untuk Malaysia, US untuk Amerika Serikat)"
                },
                "destination": {
                    "type": "string",
                    "description": "Kode 2 huruf negara tujuan ekspor yang sudah terkonfirmasi"
                },
                "product": {
                    "type": "string",
                    "description": "Nama komoditas/produk yang diekspor (misal: kopi, furnitur, kelapa, rempah)"
                },
                "pipeline_status": {
                    "type": "string",
                    "enum": ["Baru", "Dihubungi", "Follow-up", "Deal", "Tolak"],
                    "description": "Filter tahapan pipeline CRM lead"
                },
                "has_phone": {
                    "type": "boolean",
                    "description": "True jika hanya ingin lead yang memiliki nomor telepon"
                },
                "has_whatsapp": {
                    "type": "boolean",
                    "description": "True jika hanya ingin lead yang memiliki nomor WhatsApp"
                },
                "has_email": {
                    "type": "boolean",
                    "description": "True jika hanya ingin lead yang memiliki email"
                },
                "limit": {
                    "type": "integer",
                    "default": 20,
                    "description": "Batas jumlah data lead yang dikembalikan (maksimal 100)"
                }
            }
        }
    },
    {
        "name": "pokoscrap_get_lead",
        "description": "Ambil data rincian lengkap 1 lead bisnis berdasarkan ID-nya, termasuk nomor telepon, nomor WhatsApp, email, rating Google Maps, website, dan riwayat bukti ekspor.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "lead_id": {
                    "type": "string",
                    "description": "ID unik lead di PokoScrap"
                }
            },
            "required": ["lead_id"]
        }
    },
    {
        "name": "pokoscrap_update_lead_pipeline",
        "description": "Perbarui status tahapan pipeline lead bisnis di PokoScrap (Baru, Dihubungi, Follow-up, Deal, Tolak).",
        "inputSchema": {
            "type": "object",
            "properties": {
                "lead_id": {
                    "type": "string",
                    "description": "ID unik lead yang ingin diperbarui"
                },
                "pipeline_status": {
                    "type": "string",
                    "enum": ["Baru", "Dihubungi", "Follow-up", "Deal", "Tolak"],
                    "description": "Status pipeline baru"
                },
                "note": {
                    "type": "string",
                    "description": "Catatan aktivitas pembaruan status (opsional)"
                }
            },
            "required": ["lead_id", "pipeline_status"]
        }
    },
    {
        "name": "pokoscrap_create_scrape_job",
        "description": "Buat job scraping Google Maps baru untuk mengumpulkan lead bisnis dari kata kunci dan lokasi geografis.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": "Nama job scraping (misal: 'Produsen Kopi Yogyakarta')"
                },
                "queries": {
                    "type": "string",
                    "description": "Daftar kata kunci pencarian Google Maps (pisahkan baris baru per query)"
                },
                "geo_mode": {
                    "type": "string",
                    "enum": ["point", "grid"],
                    "default": "point",
                    "description": "Mode pencarian geo: point (titik + radius) atau grid (bounding box)"
                },
                "latitude": {
                    "type": "number",
                    "description": "Garis lintang lokasi pusat (misal: -7.7956 untuk Yogyakarta)"
                },
                "longitude": {
                    "type": "number",
                    "description": "Garis bujur lokasi pusat (misal: 110.3695)"
                },
                "radius_m": {
                    "type": "integer",
                    "default": 3000,
                    "description": "Radius pencarian dalam meter"
                },
                "max_credits": {
                    "type": "integer",
                    "default": 20,
                    "description": "Batas alokasi kredit untuk job ini"
                },
                "email_enabled": {
                    "type": "boolean",
                    "default": True,
                    "description": "True untuk otomatis mendeteksi email dari website bisnis"
                }
            },
            "required": ["name", "queries"]
        }
    },
    {
        "name": "pokoscrap_get_job_status",
        "description": "Periksa status, log, dan progres job pencarian Google Maps di PokoScrap.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "job_id": {
                    "type": "string",
                    "description": "ID unik job scraping"
                }
            },
            "required": ["job_id"]
        }
    },
    {
        "name": "pokoscrap_get_stats",
        "description": "Dapatkan ringkasan statistik workspace: total lead, lead bertelepon, lead ber-WhatsApp, lead ber-email, jumlah job, dan sisa saldo kredit.",
        "inputSchema": {
            "type": "object",
            "properties": {}
        }
    },
    {
        "name": "pokoscrap_export_leads",
        "description": "Ekspor ringkasan daftar lead bisnis siap hubungi ke format CSV atau JSON.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "pipeline_status": {
                    "type": "string",
                    "enum": ["Baru", "Dihubungi", "Follow-up", "Deal", "Tolak"]
                },
                "origin": {
                    "type": "string"
                },
                "has_whatsapp": {
                    "type": "boolean"
                },
                "limit": {
                    "type": "integer",
                    "default": 50
                }
            }
        }
    }
]

MCP_RESOURCES = [
    {
        "uri": "pokoscrap://leads",
        "name": "PokoScrap Leads Database",
        "description": "Database lead bisnis dari Google Maps yang telah difilter dan divalidasi",
        "mimeType": "application/json"
    },
    {
        "uri": "pokoscrap://stats",
        "name": "PokoScrap Workspace Summary",
        "description": "Statistik workspace, saldo kredit, dan capaian discovery",
        "mimeType": "application/json"
    }
]


def execute_tool(name: str, arguments: Dict[str, Any], user: Dict[str, Any]) -> Dict[str, Any]:
    """Execute tool in the tenant context of the caller."""
    actor_name = user.get("name", "MCP Agent")

    if name == "pokoscrap_search_leads":
        limit = min(int(arguments.get("limit", 20)), 100)
        with db.transaction() as conn:
            stmt = db.leads.select().limit(limit)
            if arguments.get("origin"):
                stmt = stmt.where(db.leads.c.country_origin_code == arguments["origin"].upper())
            if arguments.get("pipeline_status"):
                stmt = stmt.where(db.leads.c.pipeline_status == arguments["pipeline_status"])

            rows = db.rows(conn, stmt)
            results = []
            q = (arguments.get("query") or "").lower()
            for r in rows:
                p = r["payload"]
                if q:
                    searchable = f"{r.get('business_name','')} {p.get('address','')} {p.get('category','')} {p.get('website_url','')}".lower()
                    if q not in searchable:
                        continue
                if arguments.get("has_phone") is True and not p.get("phone_normalized"):
                    continue
                if arguments.get("has_whatsapp") is True and not p.get("whatsapp_number"):
                    continue
                if arguments.get("has_email") is True and not p.get("emails"):
                    continue

                results.append({
                    "id": r["id"],
                    "business_name": r["business_name"],
                    "category": p.get("category", ""),
                    "address": p.get("address", ""),
                    "country_origin": r.get("country_origin_code", ""),
                    "phone": p.get("phone_normalized", ""),
                    "whatsapp": p.get("whatsapp_number", ""),
                    "emails": p.get("emails", []),
                    "website": p.get("website_url", ""),
                    "rating": p.get("rating"),
                    "review_count": p.get("review_count"),
                    "pipeline_status": r.get("pipeline_status", "Baru"),
                    "maps_url": p.get("maps_url", "")
                })

            return {
                "total_matched": len(results),
                "leads": results
            }

    elif name == "pokoscrap_get_lead":
        lead_id = arguments.get("lead_id")
        if not lead_id:
            raise ValueError("lead_id wajib disertakan.")
        with db.transaction() as conn:
            lead = db.one(conn, db.leads, db.leads.c.id == lead_id)
            if not lead:
                raise ValueError(f"Lead dengan ID '{lead_id}' tidak ditemukan di organisasi Anda.")
            ev_rows = db.rows(conn, db.evidence.select().where(db.evidence.c.lead_id == lead_id))
            act_rows = db.rows(conn, db.activities.select().where(db.activities.c.lead_id == lead_id).order_by(db.activities.c.created_at.desc()).limit(10))

            p = lead["payload"]
            return {
                "id": lead["id"],
                "business_name": lead["business_name"],
                "pipeline_status": lead["pipeline_status"],
                "category": p.get("category", ""),
                "address": p.get("address", ""),
                "city": p.get("city", ""),
                "country_origin_code": lead.get("country_origin_code", ""),
                "phone": p.get("phone_normalized", ""),
                "whatsapp": p.get("whatsapp_number", ""),
                "whatsapp_status": p.get("whatsapp_status", "unknown"),
                "emails": p.get("emails", []),
                "website": p.get("website_url", ""),
                "rating": p.get("rating"),
                "review_count": p.get("review_count"),
                "maps_url": p.get("maps_url", ""),
                "consent_basis": p.get("consent_basis", "none"),
                "first_seen_at": lead.get("first_seen_at", ""),
                "evidence": [
                    {
                        "kind": e["kind"],
                        "value": e["value"],
                        "status": e["status"],
                        "url": e["payload"].get("url", ""),
                        "snippet": e["payload"].get("snippet", "")
                    }
                    for e in ev_rows
                ],
                "recent_activities": [
                    {
                        "type": a["type"],
                        "actor": a["actor"],
                        "created_at": a["created_at"],
                        "payload": a["payload"]
                    }
                    for a in act_rows
                ]
            }

    elif name == "pokoscrap_update_lead_pipeline":
        lead_id = arguments.get("lead_id")
        status = arguments.get("pipeline_status")
        note = arguments.get("note", "")
        if status not in PIPELINES:
            raise ValueError(f"Status tidak valid. Pilihan: {', '.join(PIPELINES)}")

        with db.transaction() as conn:
            lead = db.one(conn, db.leads, db.leads.c.id == lead_id)
            if not lead:
                raise ValueError(f"Lead ID '{lead_id}' tidak ditemukan.")
            old_status = lead.get("pipeline_status")
            payload = {**lead["payload"], "pipeline_status": status}
            conn.execute(db.leads.update().where(db.leads.c.id == lead_id).values(pipeline_status=status, payload=payload))

            # Record activity
            conn.execute(db.activities.insert().values(
                id=db.uid(),
                lead_id=lead_id,
                actor=actor_name,
                type="pipeline_changed",
                created_at=now(),
                payload={"old": old_status, "new": status, "note": note, "source": "mcp"}
            ))

            return {
                "success": True,
                "lead_id": lead_id,
                "previous_status": old_status,
                "new_status": status,
                "message": f"Pipeline lead '{lead['business_name']}' berhasil diperbarui ke '{status}'."
            }

    elif name == "pokoscrap_create_scrape_job":
        from .app import save_job, get_job
        from .saas import reserve_job
        job_name = clean(arguments.get("name"))
        queries_raw = arguments.get("queries", "").strip()
        queries = list(dict.fromkeys(filter(None, [q.strip() for q in queries_raw.splitlines()])))
        if not job_name or not queries:
            raise ValueError("Nama job dan minimal 1 query pencarian wajib diisi.")

        geo_mode = arguments.get("geo_mode", "point")
        lat = arguments.get("latitude", -7.7956)
        lng = arguments.get("longitude", 110.3695)
        radius = int(arguments.get("radius_m", 3000))
        max_credits = min(int(arguments.get("max_credits", 20)), 100)
        email_enabled = bool(arguments.get("email_enabled", True))

        job_id = db.uid()
        payload = {
            "queries": queries,
            "geo_mode": geo_mode,
            "latitude": lat,
            "longitude": lng,
            "radius_m": radius,
            "email_enabled": email_enabled,
            "max_credits": max_credits,
            "found_count": 0,
            "inserted_count": 0,
            "duplicate_count": 0,
            "error_count": 0,
            "log_text": "",
            "source": "mcp"
        }

        with db.transaction() as conn:
            reserve_job(conn, max_credits, job_id)
            save_job(conn, job_id, name=job_name, status="queued", payload=payload, created_by=actor_name)

        return {
            "success": True,
            "job_id": job_id,
            "name": job_name,
            "queries": queries,
            "status": "queued",
            "message": f"Job scraping '{job_name}' berhasil dijadwalkan dalam antrean."
        }

    elif name == "pokoscrap_get_job_status":
        job_id = arguments.get("job_id")
        if not job_id:
            raise ValueError("job_id wajib diisi.")
        with db.transaction() as conn:
            job = db.one(conn, db.jobs, db.jobs.c.id == job_id)
            if not job:
                raise ValueError(f"Job scraping '{job_id}' tidak ditemukan.")
            p = job["payload"]
            return {
                "id": job["id"],
                "name": job["name"],
                "status": job["status"],
                "created_at": job["created_at"],
                "created_by": job.get("created_by", ""),
                "queries": p.get("queries", []),
                "found_count": p.get("found_count", 0),
                "inserted_count": p.get("inserted_count", 0),
                "duplicate_count": p.get("duplicate_count", 0),
                "error": p.get("error"),
                "log_summary": (p.get("log_text") or "")[-800:]
            }

    elif name == "pokoscrap_get_stats":
        from .saas import balance
        with db.transaction() as conn:
            total_leads = conn.scalar(select(func.count()).select_from(db.leads)) or 0
            total_jobs = conn.scalar(select(func.count()).select_from(db.jobs)) or 0
            curr_balance = balance(conn)

            # Sample leads to count phones/whatsapps/emails
            rows = db.rows(conn, db.leads.select().limit(500))
            phones = sum(1 for r in rows if r["payload"].get("phone_normalized"))
            was = sum(1 for r in rows if r["payload"].get("whatsapp_number"))
            emails = sum(1 for r in rows if r["payload"].get("emails"))

            return {
                "total_leads": total_leads,
                "total_jobs": total_jobs,
                "credit_balance": curr_balance,
                "sampled_leads": len(rows),
                "leads_with_phone": phones,
                "leads_with_whatsapp": was,
                "leads_with_email": emails,
                "pipelines": {
                    s: conn.scalar(select(func.count()).select_from(db.leads).where(db.leads.c.pipeline_status == s)) or 0
                    for s in PIPELINES
                }
            }

    elif name == "pokoscrap_export_leads":
        limit = min(int(arguments.get("limit", 50)), 200)
        with db.transaction() as conn:
            stmt = db.leads.select().limit(limit)
            if arguments.get("pipeline_status"):
                stmt = stmt.where(db.leads.c.pipeline_status == arguments["pipeline_status"])
            if arguments.get("origin"):
                stmt = stmt.where(db.leads.c.country_origin_code == arguments["origin"].upper())

            rows = db.rows(conn, stmt)
            items = []
            for r in rows:
                p = r["payload"]
                if arguments.get("has_whatsapp") and not p.get("whatsapp_number"):
                    continue
                items.append({
                    "id": r["id"],
                    "business_name": r["business_name"],
                    "phone": p.get("phone_normalized", ""),
                    "whatsapp": p.get("whatsapp_number", ""),
                    "email": (p.get("emails") or [""])[0],
                    "address": p.get("address", ""),
                    "pipeline_status": r["pipeline_status"]
                })

            return {
                "count": len(items),
                "data": items
            }

    else:
        raise ValueError(f"Tool '{name}' tidak didukung oleh PokoScrap MCP.")


def handle_mcp_message(message: Dict[str, Any], user: Dict[str, Any]) -> Dict[str, Any]:
    """Handle standard JSON-RPC 2.0 MCP request and produce JSON-RPC 2.0 response."""
    req_id = message.get("id")
    method = message.get("method")
    params = message.get("params") or {}

    if method == "initialize":
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {
                "protocolVersion": "2024-11-05",
                "capabilities": {
                    "tools": {"listChanged": False},
                    "resources": {"subscribe": False, "listChanged": False}
                },
                "serverInfo": {
                    "name": "pokoscrap-mcp",
                    "version": "1.0.0"
                }
            }
        }

    elif method == "ping":
        return {"jsonrpc": "2.0", "id": req_id, "result": {}}

    elif method == "tools/list":
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {
                "tools": MCP_TOOLS
            }
        }

    elif method == "tools/call":
        tool_name = params.get("name")
        arguments = params.get("arguments") or {}
        try:
            res = execute_tool(tool_name, arguments, user)
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "content": [
                        {
                            "type": "text",
                            "text": json.dumps(res, indent=2, ensure_ascii=False)
                        }
                    ],
                    "isError": False
                }
            }
        except Exception as e:
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "content": [
                        {
                            "type": "text",
                            "text": f"Galat MCP: {str(e)}"
                        }
                    ],
                    "isError": True
                }
            }

    elif method == "resources/list":
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {
                "resources": MCP_RESOURCES
            }
        }

    elif method == "resources/read":
        uri = params.get("uri", "")
        if uri == "pokoscrap://stats":
            res = execute_tool("pokoscrap_get_stats", {}, user)
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "contents": [
                        {
                            "uri": uri,
                            "mimeType": "application/json",
                            "text": json.dumps(res, indent=2, ensure_ascii=False)
                        }
                    ]
                }
            }
        elif uri == "pokoscrap://leads":
            res = execute_tool("pokoscrap_search_leads", {"limit": 50}, user)
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "contents": [
                        {
                            "uri": uri,
                            "mimeType": "application/json",
                            "text": json.dumps(res, indent=2, ensure_ascii=False)
                        }
                    ]
                }
            }
        else:
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "error": {
                    "code": -32602,
                    "message": f"Resource '{uri}' tidak ditemukan."
                }
            }

    else:
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "error": {
                "code": -32601,
                "message": f"Metode MCP '{method}' tidak didukung."
            }
        }
