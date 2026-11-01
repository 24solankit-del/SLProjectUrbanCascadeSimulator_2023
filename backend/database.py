"""
Urban Cascade Simulator — Database Layer
SQLite database for persisting simulation runs, scraped data, and analytics.
Acts as the project's persistent data store.
"""

import os
import json
import sqlite3
import logging
from datetime import datetime
from typing import Optional

logger = logging.getLogger(__name__)

DB_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
os.makedirs(DB_DIR, exist_ok=True)
DB_PATH = os.path.join(DB_DIR, "cascade_simulator.db")


class Database:
    """SQLite database for the Urban Cascade Simulator."""

    def __init__(self, db_path: str = None):
        self.db_path = db_path or DB_PATH
        self._init_db()

    def _get_conn(self) -> sqlite3.Connection:
        """Get a database connection with row_factory."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        """Initialize database tables."""
        conn = self._get_conn()
        cursor = conn.cursor()

        cursor.executescript("""
            CREATE TABLE IF NOT EXISTS simulation_runs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                scenario_key TEXT NOT NULL,
                scenario_name TEXT NOT NULL,
                severity TEXT,
                total_ticks INTEGER,
                peak_fail_count INTEGER,
                max_cascade_depth INTEGER,
                final_resilience REAL,
                total_events INTEGER,
                status_counts_json TEXT,
                created_at TEXT DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS event_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id INTEGER NOT NULL,
                tick INTEGER,
                node_id TEXT,
                node_name TEXT,
                department TEXT,
                event_text TEXT,
                from_state TEXT,
                to_state TEXT,
                cascade_depth INTEGER DEFAULT 0,
                FOREIGN KEY (run_id) REFERENCES simulation_runs(id)
            );

            CREATE TABLE IF NOT EXISTS scraped_data (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source_type TEXT NOT NULL,
                data_json TEXT NOT NULL,
                risk_level TEXT,
                fetched_at TEXT DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS node_snapshots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id INTEGER NOT NULL,
                node_id TEXT,
                node_name TEXT,
                department TEXT,
                final_state TEXT,
                threshold REAL,
                stress_level REAL,
                fail_tick INTEGER,
                FOREIGN KEY (run_id) REFERENCES simulation_runs(id)
            );

            CREATE TABLE IF NOT EXISTS tick_snapshots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id INTEGER NOT NULL,
                tick INTEGER,
                operational INTEGER,
                degraded INTEGER,
                recovering INTEGER,
                failed INTEGER,
                resilience REAL,
                cascade_depth INTEGER,
                affected INTEGER,
                FOREIGN KEY (run_id) REFERENCES simulation_runs(id)
            );
        """)

        conn.commit()
        conn.close()
        logger.info(f"Database initialized at {self.db_path}")

    # ── Simulation Run Storage ──────────────────────────────────────

    def save_simulation_run(self, scenario_key: str, results: dict) -> int:
        """
        Save a complete simulation run (summary + events + nodes + ticks).
        Returns the run_id.
        """
        conn = self._get_conn()
        cursor = conn.cursor()

        data = results[scenario_key]

        # Insert run summary
        cursor.execute("""
            INSERT INTO simulation_runs
            (scenario_key, scenario_name, severity, total_ticks, peak_fail_count,
             max_cascade_depth, final_resilience, total_events, status_counts_json)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            scenario_key,
            data["scenario_name"],
            data["severity"],
            data["final_tick"],
            data["peak_fail_count"],
            data["cascade_depth"],
            data["final_resilience"],
            data["event_count"],
            json.dumps(data["final_status_counts"]),
        ))
        run_id = cursor.lastrowid

        # Insert event logs
        for event in data["event_log"]:
            cursor.execute("""
                INSERT INTO event_logs
                (run_id, tick, node_id, node_name, department, event_text, from_state, to_state, cascade_depth)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                run_id,
                event.get("tick"),
                event.get("nodeId"),
                event.get("nodeName"),
                event.get("dept"),
                event.get("event"),
                event.get("fromState"),
                event.get("toState"),
                event.get("cascadeDepth", 0),
            ))

        # Insert node snapshots
        for node in data["nodes"]:
            cursor.execute("""
                INSERT INTO node_snapshots
                (run_id, node_id, node_name, department, final_state, threshold, stress_level, fail_tick)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                run_id,
                node["id"],
                node["name"],
                node["dept"],
                node["state"],
                node["thresh"],
                node["inStress"],
                node["failTick"],
            ))

        # Insert tick snapshots
        for snap in data["tick_snapshots"]:
            cursor.execute("""
                INSERT INTO tick_snapshots
                (run_id, tick, operational, degraded, recovering, failed, resilience, cascade_depth, affected)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                run_id,
                snap.get("tick"),
                snap.get("op", 0),
                snap.get("deg", 0),
                snap.get("rec", 0),
                snap.get("fail", 0),
                snap.get("resilience", 100),
                snap.get("cascadeDepth", 0),
                snap.get("affected", 0),
            ))

        conn.commit()
        conn.close()
        logger.info(f"Simulation run saved: {scenario_key} (run_id={run_id})")
        return run_id

    def save_all_simulation_runs(self, results: dict) -> list:
        """Save all scenario results. Returns list of run_ids."""
        run_ids = []
        for key in results:
            run_id = self.save_simulation_run(key, results)
            run_ids.append(run_id)
        return run_ids

    # ── Scraped Data Storage ────────────────────────────────────────

    def save_scraped_data(self, source_type: str, data: dict, risk_level: str = None):
        """Save scraped city data to database."""
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO scraped_data (source_type, data_json, risk_level)
            VALUES (?, ?, ?)
        """, (source_type, json.dumps(data), risk_level))
        conn.commit()
        conn.close()

    # ── Query Methods ───────────────────────────────────────────────

    def get_all_runs(self) -> list:
        """Get all simulation runs."""
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM simulation_runs ORDER BY created_at DESC")
        rows = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return rows

    def get_run_details(self, run_id: int) -> dict:
        """Get full details of a simulation run."""
        conn = self._get_conn()
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM simulation_runs WHERE id = ?", (run_id,))
        run = dict(cursor.fetchone()) if cursor.fetchone() else None

        if not run:
            conn.close()
            return {}

        # Re-fetch since fetchone consumed it
        cursor.execute("SELECT * FROM simulation_runs WHERE id = ?", (run_id,))
        run = dict(cursor.fetchone())

        cursor.execute("SELECT * FROM event_logs WHERE run_id = ? ORDER BY tick", (run_id,))
        events = [dict(row) for row in cursor.fetchall()]

        cursor.execute("SELECT * FROM node_snapshots WHERE run_id = ?", (run_id,))
        nodes = [dict(row) for row in cursor.fetchall()]

        cursor.execute("SELECT * FROM tick_snapshots WHERE run_id = ? ORDER BY tick", (run_id,))
        ticks = [dict(row) for row in cursor.fetchall()]

        conn.close()

        return {
            "run": run,
            "events": events,
            "nodes": nodes,
            "tick_snapshots": ticks,
        }

    def get_scraped_data_history(self, source_type: str = None, limit: int = 20) -> list:
        """Get scraped data history."""
        conn = self._get_conn()
        cursor = conn.cursor()

        if source_type:
            cursor.execute(
                "SELECT * FROM scraped_data WHERE source_type = ? ORDER BY fetched_at DESC LIMIT ?",
                (source_type, limit),
            )
        else:
            cursor.execute(
                "SELECT * FROM scraped_data ORDER BY fetched_at DESC LIMIT ?",
                (limit,),
            )

        rows = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return rows

    def get_statistics(self) -> dict:
        """Get overall database statistics."""
        conn = self._get_conn()
        cursor = conn.cursor()

        stats = {}
        cursor.execute("SELECT COUNT(*) as count FROM simulation_runs")
        stats["total_runs"] = cursor.fetchone()["count"]

        cursor.execute("SELECT COUNT(*) as count FROM event_logs")
        stats["total_events"] = cursor.fetchone()["count"]

        cursor.execute("SELECT COUNT(*) as count FROM scraped_data")
        stats["total_scraped_records"] = cursor.fetchone()["count"]

        cursor.execute("""
            SELECT scenario_name, COUNT(*) as run_count, 
                   AVG(final_resilience) as avg_resilience,
                   AVG(peak_fail_count) as avg_peak_failures
            FROM simulation_runs 
            GROUP BY scenario_key
        """)
        stats["scenario_stats"] = [dict(row) for row in cursor.fetchall()]

        conn.close()
        return stats
