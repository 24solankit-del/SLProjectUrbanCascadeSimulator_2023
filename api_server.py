"""
Urban Cascade Simulator — Flask REST API Server
Serves as the backend API for the frontend web application.
Provides endpoints for simulation, web scraping, analytics, and database queries.
"""

import os
import sys
import json
import logging
from datetime import datetime

from flask import Flask, jsonify, request, send_file, send_from_directory
from flask_cors import CORS

# Add parent to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.graph_engine import GraphEngine
from backend.scraper import NagpurDataScraper
from backend.analytics import AnalyticsEngine
from backend.database import Database
from backend.config import SCENARIOS, INITIAL_NODES, INITIAL_EDGES

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger(__name__)

# ── Flask App Setup ─────────────────────────────────────────────────
app = Flask(__name__, static_folder=None)
CORS(app)  # Enable cross-origin requests from the frontend

# ── Shared Instances ────────────────────────────────────────────────
engine = GraphEngine()
scraper = NagpurDataScraper()
analytics = AnalyticsEngine()
db = Database()

# ── Frontend Serving (auto-detects root or frontend/ directory) ─────
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
if os.path.isfile(os.path.join(PROJECT_ROOT, "index.html")):
    FRONTEND_DIR = PROJECT_ROOT
elif os.path.isdir(os.path.join(PROJECT_ROOT, "frontend")):
    FRONTEND_DIR = os.path.join(PROJECT_ROOT, "frontend")
else:
    FRONTEND_DIR = PROJECT_ROOT
FRONTEND_DIR = os.environ.get("FRONTEND_DIR", FRONTEND_DIR)


@app.route("/")
def index():
    """Serve the frontend index.html."""
    if os.path.isfile(os.path.join(FRONTEND_DIR, "index.html")):
        return send_from_directory(FRONTEND_DIR, "index.html")
    return jsonify({
        "app": "Urban Cascade Simulator — Backend API",
        "version": "1.0.0",
        "team": "Arc Reactors | G H Raisoni Skilltech University",
        "endpoints": {
            "simulation": "/api/simulation/*",
            "scraper": "/api/scraper/*",
            "analytics": "/api/analytics/*",
            "database": "/api/db/*",
        },
    })


@app.route("/<path:filename>")
def serve_frontend(filename):
    """Serve frontend static files (css, js, etc.)."""
    return send_from_directory(FRONTEND_DIR, filename)


# ═══════════════════════════════════════════════════════════════════
#  SIMULATION API
# ═══════════════════════════════════════════════════════════════════

@app.route("/api/simulation/state", methods=["GET"])
def get_simulation_state():
    """Get the current simulation state."""
    return jsonify(engine.export_state())


@app.route("/api/simulation/step", methods=["POST"])
def step_simulation():
    """Advance simulation by one tick."""
    changed = engine.step()
    state = engine.export_state()
    state["changed"] = changed
    return jsonify(state)


@app.route("/api/simulation/inject/<scenario_key>", methods=["POST"])
def inject_scenario(scenario_key):
    """Inject a scenario (flood, cyber, grid, compound)."""
    if scenario_key not in SCENARIOS:
        return jsonify({"error": f"Unknown scenario: {scenario_key}"}), 400

    engine.reset()
    engine.inject_scenario(scenario_key)
    return jsonify(engine.export_state())


@app.route("/api/simulation/run/<scenario_key>", methods=["POST"])
def run_scenario(scenario_key):
    """Run a scenario to completion and return full results."""
    if scenario_key not in SCENARIOS:
        return jsonify({"error": f"Unknown scenario: {scenario_key}"}), 400

    max_ticks = request.args.get("max_ticks", 50, type=int)
    state = engine.run_scenario_to_completion(scenario_key, max_ticks)
    return jsonify(state)


@app.route("/api/simulation/run-all", methods=["POST"])
def run_all_scenarios():
    """Run all scenarios and return comparative results."""
    results = analytics.run_all_scenarios_analysis()

    # Auto-save to database
    db.save_all_simulation_runs(results)

    # Simplify output for API
    summary = {}
    for key, data in results.items():
        summary[key] = {
            "scenario_name": data["scenario_name"],
            "severity": data["severity"],
            "final_tick": data["final_tick"],
            "peak_fail_count": data["peak_fail_count"],
            "cascade_depth": data["cascade_depth"],
            "final_resilience": data["final_resilience"],
            "event_count": data["event_count"],
            "final_status_counts": data["final_status_counts"],
        }
    return jsonify(summary)


@app.route("/api/simulation/reset", methods=["POST"])
def reset_simulation():
    """Reset the simulation to initial state."""
    engine.reset()
    return jsonify(engine.export_state())


@app.route("/api/simulation/fail-node/<node_id>", methods=["POST"])
def fail_node(node_id):
    """Directly fail a specific node."""
    if node_id not in engine.nodes:
        return jsonify({"error": f"Unknown node: {node_id}"}), 400
    engine.fail_node(node_id)
    return jsonify(engine.export_state())


@app.route("/api/simulation/scenarios", methods=["GET"])
def list_scenarios():
    """List available scenarios."""
    return jsonify(SCENARIOS)


@app.route("/api/simulation/nodes", methods=["GET"])
def list_nodes():
    """List all infrastructure nodes."""
    return jsonify(INITIAL_NODES)


# ═══════════════════════════════════════════════════════════════════
#  WEB SCRAPER API
# ═══════════════════════════════════════════════════════════════════

@app.route("/api/scraper/weather", methods=["GET"])
def get_weather():
    """Fetch current Nagpur weather data."""
    data = scraper.fetch_weather()
    db.save_scraped_data("weather", data, data.get("risk_assessment", {}).get("level"))
    return jsonify(data)


@app.route("/api/scraper/air-quality", methods=["GET"])
def get_air_quality():
    """Fetch Nagpur AQI data."""
    data = scraper.fetch_air_quality()
    db.save_scraped_data("air_quality", data, data.get("risk_assessment", {}).get("level"))
    return jsonify(data)


@app.route("/api/scraper/seismic", methods=["GET"])
def get_seismic():
    """Fetch seismic data near Nagpur."""
    data = scraper.fetch_seismic_data()
    db.save_scraped_data("seismic", data, data.get("risk_assessment", {}).get("level"))
    return jsonify(data)


@app.route("/api/scraper/news", methods=["GET"])
def get_news():
    """Scrape infrastructure-related Nagpur news."""
    data = scraper.scrape_nagpur_infrastructure_news()
    db.save_scraped_data("news", data)
    return jsonify(data)


@app.route("/api/scraper/all", methods=["GET"])
def get_all_scraped():
    """Fetch all data sources."""
    data = scraper.fetch_all_data()
    return jsonify(data)


# ═══════════════════════════════════════════════════════════════════
#  ANALYTICS API
# ═══════════════════════════════════════════════════════════════════

@app.route("/api/analytics/full-report", methods=["POST"])
def generate_full_report():
    """Generate full analytics report (charts + CSV + Excel)."""
    report = analytics.generate_full_report(scraper.cache)
    db.save_all_simulation_runs(report["results"])

    # Return file paths (relative)
    files = report["generated_files"]
    return jsonify({
        "charts": [os.path.basename(f) for f in files["charts"] if f],
        "csv_files": [os.path.basename(f) for f in files["csv_files"] if f],
        "excel_file": os.path.basename(files["excel_file"]) if files["excel_file"] else None,
        "scenario_count": len(report["results"]),
    })


@app.route("/api/analytics/chart/<filename>", methods=["GET"])
def get_chart(filename):
    """Serve a generated chart image."""
    return send_from_directory(analytics.output_dir, filename)


@app.route("/api/analytics/download/<filename>", methods=["GET"])
def download_file(filename):
    """Download a generated CSV/Excel file."""
    return send_from_directory(analytics.output_dir, filename, as_attachment=True)


# ═══════════════════════════════════════════════════════════════════
#  DATABASE API
# ═══════════════════════════════════════════════════════════════════

@app.route("/api/db/runs", methods=["GET"])
def get_all_runs():
    """Get all simulation run history."""
    return jsonify(db.get_all_runs())


@app.route("/api/db/runs/<int:run_id>", methods=["GET"])
def get_run_details(run_id):
    """Get detailed info for a specific simulation run."""
    return jsonify(db.get_run_details(run_id))


@app.route("/api/db/scraped", methods=["GET"])
def get_scraped_history():
    """Get scraped data history."""
    source = request.args.get("source")
    limit = request.args.get("limit", 20, type=int)
    return jsonify(db.get_scraped_data_history(source, limit))


@app.route("/api/db/stats", methods=["GET"])
def get_db_stats():
    """Get database statistics."""
    return jsonify(db.get_statistics())


# ═══════════════════════════════════════════════════════════════════
#  MAIN
# ═══════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    debug = os.environ.get("DEBUG", "true").lower() == "true"

    logger.info(f"Starting Urban Cascade Simulator API on port {port}")
    logger.info(f"Frontend directory: {FRONTEND_DIR}")
    logger.info(f"Output directory: {analytics.output_dir}")

    app.run(host="0.0.0.0", port=port, debug=debug)
