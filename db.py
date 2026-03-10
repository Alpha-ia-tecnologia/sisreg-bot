import json
import os
import sqlite3

DB_PATH = os.getenv("DB_PATH", "bot_data.db")

COLUMNS = [
    "codigo_solicitacao",
    "nome",
    "telefone",
    "procedimento",
    "local",
    "data",
    "hora",
]


def _get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Create all tables if they don't exist."""
    with _get_conn() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS not_notified (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                codigo_solicitacao TEXT,
                nome TEXT,
                telefone TEXT,
                procedimento TEXT,
                local_ TEXT,
                data TEXT,
                hora TEXT
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS executions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                started_at TEXT NOT NULL,
                finished_at TEXT,
                total_messages INTEGER DEFAULT 0,
                sent_messages INTEGER DEFAULT 0,
                failed_messages INTEGER DEFAULT 0,
                status TEXT DEFAULT 'running',
                logs TEXT DEFAULT '[]'
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS execution_records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                execution_id INTEGER NOT NULL,
                codigo_solicitacao TEXT,
                nome TEXT,
                telefone TEXT,
                procedimento TEXT,
                local_ TEXT,
                data TEXT,
                hora TEXT,
                message_status TEXT DEFAULT 'pending',
                FOREIGN KEY (execution_id) REFERENCES executions(id)
            )
        """)


def clear_records():
    """Delete all records from the table."""
    with _get_conn() as conn:
        conn.execute("DELETE FROM not_notified")


def insert_records(records: list[dict]):
    """Insert a list of record dicts into the table."""
    with _get_conn() as conn:
        conn.executemany(
            """
            INSERT INTO not_notified (codigo_solicitacao, nome, telefone, procedimento, local_, data, hora)
            VALUES (:codigo_solicitacao, :nome, :telefone, :procedimento, :local, :data, :hora)
            """,
            records,
        )


def get_all_records() -> list[dict]:
    """Return all records as a list of dicts."""
    with _get_conn() as conn:
        rows = conn.execute(
            "SELECT codigo_solicitacao, nome, telefone, procedimento, local_ AS local, data, hora FROM not_notified"
        ).fetchall()
        return [dict(row) for row in rows]


# ─── Execution history ────────────────────────────────────────────────


def create_execution(started_at: str) -> int:
    """Create a new execution record and return its id."""
    with _get_conn() as conn:
        cursor = conn.execute(
            "INSERT INTO executions (started_at) VALUES (?)",
            (started_at,),
        )
        return cursor.lastrowid


def finish_execution(
    execution_id: int,
    finished_at: str,
    total: int,
    sent: int,
    failed: int,
    status: str,
    logs: list[dict],
    records: list[dict],
    message_status: dict[str, str],
):
    """Persist final execution data."""
    with _get_conn() as conn:
        conn.execute(
            """
            UPDATE executions
            SET finished_at = ?, total_messages = ?, sent_messages = ?,
                failed_messages = ?, status = ?, logs = ?
            WHERE id = ?
            """,
            (finished_at, total, sent, failed, status, json.dumps(logs, ensure_ascii=False), execution_id),
        )
        for rec in records:
            ms = message_status.get(str(rec.get("codigo_solicitacao", "")), "pending")
            conn.execute(
                """
                INSERT INTO execution_records
                    (execution_id, codigo_solicitacao, nome, telefone, procedimento, local_, data, hora, message_status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    execution_id,
                    rec.get("codigo_solicitacao"),
                    rec.get("nome"),
                    rec.get("telefone"),
                    rec.get("procedimento"),
                    rec.get("local"),
                    rec.get("data"),
                    rec.get("hora"),
                    ms,
                ),
            )


def get_executions() -> list[dict]:
    """Return all executions ordered by most recent first (summary only)."""
    with _get_conn() as conn:
        rows = conn.execute(
            "SELECT id, started_at, finished_at, total_messages, sent_messages, failed_messages, status "
            "FROM executions ORDER BY id DESC"
        ).fetchall()
        return [dict(row) for row in rows]


def get_execution_detail(execution_id: int) -> dict | None:
    """Return full execution detail including logs and records."""
    with _get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM executions WHERE id = ?", (execution_id,)
        ).fetchone()
        if row is None:
            return None
        result = dict(row)
        result["logs"] = json.loads(result.get("logs") or "[]")
        records = conn.execute(
            """
            SELECT codigo_solicitacao, nome, telefone, procedimento,
                   local_ AS local, data, hora, message_status
            FROM execution_records
            WHERE execution_id = ?
            """,
            (execution_id,),
        ).fetchall()
        result["records"] = [dict(r) for r in records]
        return result
