# ⚡ Urban Cascade Simulator — Nagpur (S-03)

**Interdependent Urban Infrastructure Cascading Failure Simulation & Analytics Platform**  
*Team Arc Reactors | G H Raisoni Skilltech University*

---

## 📌 Overview

Urban infrastructure systems (Power, Water, Telecom, Transport, Healthcare, Emergency) are tightly coupled. A failure in one node (e.g., Koradi Thermal Power Station or Ambazari Reservoir) can trigger cascading outages across the entire municipal ecosystem.

This repository provides:
1. **Interactive 3D Web Frontend** (Three.js WebGL graph visualization with real-time HUD metrics, shockwave propagation animations, and interactive node inspector).
2. **Python Backend Core** (`GraphEngine` ported to Python with exact BFS cascade mechanics, stress modeling, and auto-recovery cycles).
3. **Desktop Tkinter GUI** (Control panel with dark HUD aesthetics for triggering scenarios, viewing metrics, stepping simulation ticks, and browsing event logs).
4. **Flask REST API Server** (Full API serving frontend static assets, handling simulation runs, dynamic node failure injection, and telemetry sync).
5. **Real-time Web Scraper & Environmental Risk Engine** (Gathers live weather from `wttr.in`, air quality from `WAQI`, seismic activity from `USGS`, and news headlines from Google News).
6. **Analytics & Automated Reporting Engine** (Generates comparative charts via `matplotlib` and exports full simulation logs, node states, and tick snapshots to **CSV** and multi-sheet **Excel (`.xlsx`)** workbooks).
7. **SQLite Persistent Database** (`cascade_simulator.db` storing historical simulation runs, event sequences, scraped environmental snapshots, and aggregate resilience statistics).

---

## 🗂 Repository Structure

```text
urban-cascade-backend/
├── run.py                     # Single-command launcher (GUI / API / Both)
├── gui_app.py                 # Tkinter Desktop GUI Control Panel
├── api_server.py              # Flask REST API Server (serves API & Frontend)
├── requirements.txt           # Python dependencies
├── README.md                  # Comprehensive documentation
│
├── backend/                   # Python Core Engine Package
│   ├── __init__.py
│   ├── config.py              # 18 Nagpur nodes, 26 edges, scenarios, colors
│   ├── graph_engine.py        # DiGraph, BFS cascade propagation, auto-recovery
│   ├── scraper.py             # Live data scraper (Weather, AQI, Seismic, News)
│   ├── analytics.py           # Matplotlib chart generator & CSV/Excel exporter
│   └── database.py            # SQLite schema, query helpers & persistence
│
├── frontend/                  # Web Frontend (Three.js 3D Simulator)
│   ├── index.html             # Main dashboard UI
│   ├── css/
│   │   └── styles.css         # Glassmorphism cyber-HUD styling
│   ├── js/
│   │   ├── app.js             # Entry point & bootstrap
│   │   ├── config.js          # Nodes, topology & scenario configs
│   │   ├── graph-engine.js    # Client-side BFS cascade logic
│   │   ├── metrics.js         # Telemetry & sparkline tracker
│   │   ├── prng.js            # Deterministic pseudo-random number generator
│   │   ├── renderer.js        # Three.js 3D scene & node renderer
│   │   └── ui-controller.js   # Event handling, inspector & HUD binder
│   └── scenarios/             # Scenario definitions (JSON)
│       ├── flood.json         # Ambazari Reservoir breach
│       ├── cyberattack.json   # MIHAN Cyber Data Hub attack
│       ├── powercut.json      # Koradi Thermal Power Station fire
│       └── compound.json      # Simultaneous flood + cyberattack
│
└── data/                      # Data storage & analytics output
    ├── cascade_simulator.db   # SQLite relational database
    └── output/                # Generated analytics artifacts
        ├── chart_resilience_over_time.png
        ├── chart_cascade_depth.png
        ├── chart_department_impact.png
        ├── chart_failure_timeline_*.png
        ├── events_*.csv
        ├── scenario_comparison_*.csv
        ├── node_status_*.csv
        └── urban_cascade_analytics_*.xlsx
```

---

## 🚀 How to Run Everything

### Step 1: Install Dependencies

Make sure Python 3.9+ is installed, then run:

```bash
pip install -r requirements.txt
```

*(Packages used: `flask`, `flask-cors`, `requests`, `beautifulsoup4`, `pandas`, `openpyxl`, `matplotlib`)*

---

### Step 2: Choose Your Execution Mode

Use the provided `run.py` unified launcher:

#### Option A: Launch Tkinter Desktop GUI (Default)
```bash
python run.py gui
```
*Opens the Tkinter desktop control panel where you can run simulations, fetch live scraped data, view logs, export Excel/CSV files, and check database stats.*

#### Option B: Launch Full Stack (API Server + 3D Web Frontend)
```bash
python run.py api
```
*Starts the Flask server on `http://localhost:5000`.*  
Open your browser and navigate to:
👉 **`http://localhost:5000`** to interact with the 3D Three.js cascade simulator!

#### Option C: Run Both GUI and Web API Simultaneously
```bash
python run.py both
```
*Launches the Flask web server in the background and opens the Tkinter desktop GUI immediately.*

---

## 📊 Analytics, CSV & Excel Exports

The analytics engine (`backend/analytics.py`) automatically evaluates failure propagation across all scenarios:

- **Excel Workbook (`.xlsx`)**: Contains 5 structured sheets:
  1. `Summary`: Comparative scenario metrics (Peak failures, ticks, resilience %).
  2. `Event Log`: Step-by-step cascade propagation logs.
  3. `Node Status`: Detailed stress levels and failure states per node.
  4. `Tick Snapshots`: Temporal progression of OP/DEG/REC/FAIL counts.
  5. `Scraped Data`: Environmental context captured during the run.
- **CSV Files**: Individual event logs, scenario comparisons, and node stress status.
- **Charts (`.png`)**:
  - `chart_resilience_over_time.png`: System resilience trajectories across ticks.
  - `chart_cascade_depth.png`: Maximum propagation hop distance per disruption.
  - `chart_department_impact.png`: Failure breakdown across Power, Water, Telecom, Transport, Health, and Emergency services.
  - `chart_failure_timeline_*.png`: Stacked state area diagrams over time.

---

## 🌐 Real-Time Web Scraping Integration

The scraper module (`backend/scraper.py`) queries live external endpoints:
- **Weather (`wttr.in`)**: Precipitation, wind speeds, and temperature to calculate monsoon flood risk for Ambazari Reservoir.
- **Air Quality (`WAQI`)**: PM2.5 / AQI indices to estimate stress on AIIMS and GMC hospital lifelines.
- **Seismic Activity (`USGS`)**: Earthquakes within a 500 km radius of Nagpur (21.1458° N, 79.0882° E).
- **Nagpur News**: RSS headlines regarding local municipal and power grid infrastructure.

---

## 🗄 SQLite Database

The database (`data/cascade_simulator.db`) automatically records:
- `simulation_runs`: Run metadata, peak failures, and final resilience index.
- `event_logs`: Individual failure propagation events with cascade depth.
- `node_snapshots`: Node stress and final states.
- `tick_snapshots`: Per-tick telemetry.
- `scraped_data`: Timestamped environmental readings and risk alerts.
