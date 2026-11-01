"""
Urban Cascade Simulator — Configuration
Contains all Nagpur infrastructure node definitions, edge topology,
scenario presets, and department metadata matching the frontend config.js.
"""

# ── Status Constants ────────────────────────────────────────────────
STATUS_OP = "OPERATIONAL"
STATUS_DEG = "DEGRADED"
STATUS_REC = "RECOVERING"
STATUS_FAIL = "FAILED"

# ── Department Colors (for analytics charts) ────────────────────────
DEPT_COLORS = {
    "Power": "#f59e0b",
    "Water": "#3b82f6",
    "Telecom": "#8b5cf6",
    "Transport": "#06b6d4",
    "Health": "#ef4444",
    "Admin": "#6b7280",
    "Emergency": "#f97316",
}

# ── 18 Nagpur Infrastructure Nodes ──────────────────────────────────
INITIAL_NODES = [
    # Power Infrastructure
    {"id": "KORADI_POWER",     "name": "Koradi Thermal Power Stn",      "dept": "Power",     "pos": [-28, 4, -30], "thresh": 0.8,  "desc": "Central Power Generation Hub"},
    {"id": "KHAPARKHEDA_SUB",  "name": "Khaparkheda Substation",        "dept": "Power",     "pos": [-18, 3, -22], "thresh": 0.7,  "desc": "Primary 400kV Stepdown Grid"},
    {"id": "DHARAMPETH_SUB",   "name": "Dharampeth Power Substation",   "dept": "Power",     "pos": [-10, 2, -5],  "thresh": 0.6,  "desc": "West Nagpur Electricity Feeder"},
    {"id": "BUTIBORI_GRID",    "name": "Butibori Industrial Substation", "dept": "Power",    "pos": [-24, 2, 26],  "thresh": 0.65, "desc": "Industrial Zone Feeder"},
    # Water Infrastructure
    {"id": "GOREWADA_WATER",   "name": "Gorewada Water Filtration",     "dept": "Water",     "pos": [-26, 3, -12], "thresh": 0.75, "desc": "Primary Potable Water Treatment"},
    {"id": "AMBAZARI_RESERVOIR","name": "Ambazari Sluice & Reservoir",  "dept": "Water",     "pos": [-14, 2, 12],  "thresh": 0.6,  "desc": "Municipal Drainage & Water Head"},
    {"id": "KANHAN_PUMP",      "name": "Kanhan Water Pumping Line",     "dept": "Water",     "pos": [22, 2, -26],  "thresh": 0.7,  "desc": "East Nagpur Water Supply Line"},
    # Telecom / Data Infrastructure
    {"id": "MIHAN_DATACENTER", "name": "MIHAN Cyber Data Hub",          "dept": "Telecom",   "pos": [-6, 3, 30],   "thresh": 0.85, "desc": "Fiber Internet & Municipal Cloud"},
    {"id": "SADAR_TELCO",      "name": "Sadar BSNL Telecom Tower",      "dept": "Telecom",   "pos": [2, 3, -8],    "thresh": 0.6,  "desc": "Core Telecom & Emergency Radio"},
    # Transport Infrastructure
    {"id": "SITABULDI_METRO",  "name": "Sitabuldi Interchange Metro",   "dept": "Transport", "pos": [0, 2, 0],     "thresh": 0.7,  "desc": "Urban Rapid Transit Nerve"},
    {"id": "NAGPUR_RLY_JN",    "name": "Nagpur Central Railway Jn",     "dept": "Transport", "pos": [12, 2, -4],   "thresh": 0.65, "desc": "Logistics & Heavy Transport Hub"},
    {"id": "AIRPORT_SONEGAON", "name": "Dr. Ambedkar Intl Airport",     "dept": "Transport", "pos": [-12, 2, 22],  "thresh": 0.8,  "desc": "Civil Aviation & Air Cargo"},
    {"id": "ZERO_MILE_TRAFFIC","name": "Zero Mile Traffic Control",     "dept": "Transport", "pos": [4, 2, 2],     "thresh": 0.55, "desc": "Automated Signaling Network"},
    # Health Infrastructure
    {"id": "AIIMS_NAGPUR",     "name": "AIIMS Nagpur Super-Speciality", "dept": "Health",    "pos": [8, 3, 26],    "thresh": 0.85, "desc": "Tertiary Trauma & Critical Care"},
    {"id": "GMC_HOSPITAL",     "name": "Govt Medical College (GMC)",    "dept": "Health",    "pos": [8, 2, 8],     "thresh": 0.75, "desc": "Emergency Surgical & ICU Base"},
    # Admin & Emergency Services
    {"id": "NMC_HQ_CIVIL",    "name": "NMC Municipal HQ Civil Lines",  "dept": "Admin",     "pos": [-4, 3, -4],   "thresh": 0.6,  "desc": "Disaster Command & Coordination"},
    {"id": "POLICE_HQ_CIVIL", "name": "Nagpur Police Commissionerate", "dept": "Emergency", "pos": [-2, 2, -10],  "thresh": 0.7,  "desc": "Law, Order & Crisis Mobilization"},
    {"id": "FIRE_HQ_SADAR",   "name": "Central Fire Rescue HQ Sadar",  "dept": "Emergency", "pos": [6, 2, -14],   "thresh": 0.65, "desc": "Hazardous Response Units"},
]

# ── Directed Dependency Edges (source → target, weight) ─────────────
INITIAL_EDGES = [
    # Power cascade chain
    {"u": "KORADI_POWER",     "v": "KHAPARKHEDA_SUB",  "weight": 0.95},
    {"u": "KHAPARKHEDA_SUB",  "v": "DHARAMPETH_SUB",   "weight": 0.9},
    {"u": "KHAPARKHEDA_SUB",  "v": "BUTIBORI_GRID",    "weight": 0.85},
    {"u": "KHAPARKHEDA_SUB",  "v": "KANHAN_PUMP",      "weight": 0.8},
    # Dharampeth distribution
    {"u": "DHARAMPETH_SUB",   "v": "GOREWADA_WATER",   "weight": 0.85},
    {"u": "DHARAMPETH_SUB",   "v": "SADAR_TELCO",      "weight": 0.75},
    {"u": "DHARAMPETH_SUB",   "v": "ZERO_MILE_TRAFFIC","weight": 0.8},
    {"u": "DHARAMPETH_SUB",   "v": "SITABULDI_METRO",  "weight": 0.9},
    # Butibori industrial zone
    {"u": "BUTIBORI_GRID",    "v": "MIHAN_DATACENTER", "weight": 0.9},
    {"u": "BUTIBORI_GRID",    "v": "AIRPORT_SONEGAON", "weight": 0.85},
    {"u": "BUTIBORI_GRID",    "v": "AIIMS_NAGPUR",     "weight": 0.9},
    # Water dependencies
    {"u": "GOREWADA_WATER",   "v": "AIIMS_NAGPUR",     "weight": 0.6},
    {"u": "GOREWADA_WATER",   "v": "GMC_HOSPITAL",     "weight": 0.75},
    {"u": "GOREWADA_WATER",   "v": "NMC_HQ_CIVIL",    "weight": 0.5},
    # Ambazari cross-dependencies
    {"u": "AMBAZARI_RESERVOIR","v": "DHARAMPETH_SUB",   "weight": 0.7},
    {"u": "AMBAZARI_RESERVOIR","v": "SITABULDI_METRO",  "weight": 0.65},
    # Telecom cascades
    {"u": "MIHAN_DATACENTER", "v": "ZERO_MILE_TRAFFIC","weight": 0.85},
    {"u": "MIHAN_DATACENTER", "v": "NMC_HQ_CIVIL",    "weight": 0.75},
    {"u": "MIHAN_DATACENTER", "v": "POLICE_HQ_CIVIL",  "weight": 0.8},
    {"u": "SADAR_TELCO",      "v": "POLICE_HQ_CIVIL",  "weight": 0.7},
    {"u": "SADAR_TELCO",      "v": "FIRE_HQ_SADAR",    "weight": 0.85},
    # Transport → Services
    {"u": "ZERO_MILE_TRAFFIC","v": "GMC_HOSPITAL",     "weight": 0.6},
    {"u": "ZERO_MILE_TRAFFIC","v": "FIRE_HQ_SADAR",    "weight": 0.7},
    {"u": "SITABULDI_METRO",  "v": "NAGPUR_RLY_JN",    "weight": 0.6},
    # Emergency cross-links
    {"u": "POLICE_HQ_CIVIL",  "v": "NMC_HQ_CIVIL",    "weight": 0.5},
    {"u": "FIRE_HQ_SADAR",    "v": "AIIMS_NAGPUR",     "weight": 0.5},
]

# ── Scenario Presets ─────────────────────────────────────────────────
SCENARIOS = {
    "flood": {
        "name": "Ambazari Flood",
        "description": "Monsoon surge causes sluice breach at Ambazari Reservoir",
        "failNodes": ["AMBAZARI_RESERVOIR"],
        "severity": "HIGH",
        "affectedSectors": ["Water", "Transport", "Power"],
    },
    "cyber": {
        "name": "MIHAN Cyberattack",
        "description": "Coordinated ransomware attack on the MIHAN Cyber Data Hub",
        "failNodes": ["MIHAN_DATACENTER"],
        "severity": "CRITICAL",
        "affectedSectors": ["Telecom", "Transport", "Emergency", "Admin"],
    },
    "grid": {
        "name": "Koradi Power Outage",
        "description": "Severe transformer fire at Koradi Thermal Power Station",
        "failNodes": ["KORADI_POWER"],
        "severity": "CATASTROPHIC",
        "affectedSectors": ["Power", "Water", "Telecom", "Transport", "Health", "Emergency", "Admin"],
    },
    "compound": {
        "name": "Flood + Cyberattack",
        "description": "Simultaneous Ambazari flood and MIHAN cyberattack",
        "failNodes": ["AMBAZARI_RESERVOIR", "MIHAN_DATACENTER"],
        "severity": "CATASTROPHIC",
        "affectedSectors": ["Water", "Telecom", "Power", "Transport", "Health", "Emergency", "Admin"],
    },
}

# ── Web Scraping URLs (real-time Nagpur data sources) ────────────────
SCRAPE_SOURCES = {
    "weather": {
        "url": "https://wttr.in/Nagpur?format=j1",
        "description": "Weather data for Nagpur (JSON API)",
        "type": "api_json",
    },
    "air_quality": {
        "url": "https://api.waqi.info/feed/nagpur/?token=demo",
        "description": "Air Quality Index for Nagpur",
        "type": "api_json",
    },
    "earthquake": {
        "url": "https://earthquake.usgs.gov/fdsnws/event/1/query?format=geojson&latitude=21.1458&longitude=79.0882&maxradiuskm=500&limit=10&orderby=time",
        "description": "Recent seismic activity near Nagpur (USGS)",
        "type": "api_json",
    },
}
