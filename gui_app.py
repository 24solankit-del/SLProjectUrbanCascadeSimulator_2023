"""
Urban Cascade Simulator — Tkinter Desktop GUI
A compact control panel for running simulations, scraping data,
viewing analytics, and managing exports.
"""

import os
import sys
import json
import threading
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import webbrowser
import logging

# Add parent to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.graph_engine import GraphEngine
from backend.scraper import NagpurDataScraper
from backend.analytics import AnalyticsEngine
from backend.database import Database
from backend.config import SCENARIOS, DEPT_COLORS, STATUS_OP, STATUS_FAIL, STATUS_DEG, STATUS_REC

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class CascadeSimulatorGUI:
    """Tkinter-based control panel for the Urban Cascade Simulator."""

    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("🏙 Urban Cascade Simulator — Nagpur | Backend Control Panel")
        self.root.geometry("1050x720")
        self.root.configure(bg="#0b132b")
        self.root.resizable(True, True)

        # Core components
        self.engine = GraphEngine()
        self.scraper = NagpurDataScraper()
        self.analytics = AnalyticsEngine()
        self.db = Database()

        # State
        self.current_results = None
        self.scraped_data = None
        self.auto_play_active = False

        # Style
        self._setup_style()
        self._build_ui()
        self._update_status("Ready. Select a scenario or action to begin.")

    # ═══════════════════════════════════════════════════════════
    #  STYLING
    # ═══════════════════════════════════════════════════════════

    def _setup_style(self):
        """Configure ttk style to match the dark HUD aesthetic."""
        style = ttk.Style()
        style.theme_use("clam")

        # Colors
        self.bg = "#0b132b"
        self.bg_panel = "#111b33"
        self.bg_entry = "#1a2744"
        self.fg = "#f3f4f6"
        self.fg_dim = "#9ca3af"
        self.cyan = "#22d3ee"
        self.red = "#f87171"
        self.green = "#34d399"
        self.yellow = "#fbbf24"
        self.blue = "#3b82f6"

        style.configure("Dark.TFrame", background=self.bg_panel)
        style.configure("Dark.TLabel", background=self.bg_panel, foreground=self.fg, font=("Inter", 9))
        style.configure("Header.TLabel", background=self.bg, foreground=self.cyan,
                        font=("JetBrains Mono", 14, "bold"))
        style.configure("SubHeader.TLabel", background=self.bg_panel, foreground=self.cyan,
                        font=("JetBrains Mono", 10, "bold"))
        style.configure("Status.TLabel", background=self.bg, foreground=self.fg_dim, font=("Inter", 8))

        style.configure("Accent.TButton", background="#0e4a6e", foreground=self.fg,
                        font=("Inter", 9, "bold"), padding=(10, 5))
        style.map("Accent.TButton",
                  background=[("active", "#0c3d5c"), ("pressed", "#082f49")])

        style.configure("Danger.TButton", background="#7f1d1d", foreground=self.fg,
                        font=("Inter", 9, "bold"), padding=(10, 5))
        style.map("Danger.TButton",
                  background=[("active", "#991b1b"), ("pressed", "#7f1d1d")])

        style.configure("Success.TButton", background="#064e3b", foreground=self.fg,
                        font=("Inter", 9, "bold"), padding=(10, 5))
        style.map("Success.TButton",
                  background=[("active", "#065f46"), ("pressed", "#064e3b")])

        style.configure("Dark.TNotebook", background=self.bg)
        style.configure("Dark.TNotebook.Tab", background=self.bg_panel, foreground=self.fg_dim,
                        padding=(12, 5), font=("Inter", 9))
        style.map("Dark.TNotebook.Tab",
                  background=[("selected", "#1a2744")],
                  foreground=[("selected", self.cyan)])

        # Treeview style
        style.configure("Dark.Treeview",
                        background=self.bg_entry, foreground=self.fg, fieldbackground=self.bg_entry,
                        font=("JetBrains Mono", 8), rowheight=22)
        style.configure("Dark.Treeview.Heading",
                        background="#1a2744", foreground=self.cyan,
                        font=("JetBrains Mono", 8, "bold"))
        style.map("Dark.Treeview",
                  background=[("selected", "#0e4a6e")],
                  foreground=[("selected", "#f3f4f6")])

    # ═══════════════════════════════════════════════════════════
    #  UI LAYOUT
    # ═══════════════════════════════════════════════════════════

    def _build_ui(self):
        """Build the complete GUI layout."""

        # ── Header ──────────────────────────────────────────────
        header_frame = tk.Frame(self.root, bg=self.bg, pady=8)
        header_frame.pack(fill="x", padx=15)

        ttk.Label(header_frame, text="⚡ URBAN CASCADE SIMULATOR", style="Header.TLabel").pack(side="left")
        ttk.Label(header_frame, text="S-03 • Nagpur • Team Arc Reactors",
                  style="Status.TLabel").pack(side="right", padx=10)

        # ── Main Notebook (Tabs) ────────────────────────────────
        self.notebook = ttk.Notebook(self.root, style="Dark.TNotebook")
        self.notebook.pack(fill="both", expand=True, padx=10, pady=(0, 5))

        self._build_simulation_tab()
        self._build_scraper_tab()
        self._build_analytics_tab()
        self._build_database_tab()

        # ── Status Bar ──────────────────────────────────────────
        self.status_var = tk.StringVar(value="Ready")
        status_bar = tk.Frame(self.root, bg="#050a18", height=24)
        status_bar.pack(fill="x", side="bottom")
        ttk.Label(status_bar, textvariable=self.status_var, style="Status.TLabel").pack(side="left", padx=10)

    # ── TAB 1: SIMULATION ───────────────────────────────────────

    def _build_simulation_tab(self):
        """Build the Simulation Control tab."""
        tab = ttk.Frame(self.notebook, style="Dark.TFrame")
        self.notebook.add(tab, text="  🎮 Simulation  ")

        # Top controls
        ctrl_frame = ttk.Frame(tab, style="Dark.TFrame")
        ctrl_frame.pack(fill="x", padx=10, pady=8)

        ttk.Label(ctrl_frame, text="SCENARIO:", style="SubHeader.TLabel").pack(side="left", padx=(0, 8))

        self.scenario_var = tk.StringVar(value="grid")
        scenario_menu = ttk.Combobox(ctrl_frame, textvariable=self.scenario_var,
                                      values=list(SCENARIOS.keys()), state="readonly", width=15)
        scenario_menu.pack(side="left", padx=5)

        ttk.Button(ctrl_frame, text="▶ Run Scenario", style="Accent.TButton",
                   command=self._run_scenario).pack(side="left", padx=5)
        ttk.Button(ctrl_frame, text="▶▶ Run All", style="Accent.TButton",
                   command=self._run_all_scenarios).pack(side="left", padx=5)
        ttk.Button(ctrl_frame, text="🔄 Reset", style="Danger.TButton",
                   command=self._reset_simulation).pack(side="left", padx=5)
        ttk.Button(ctrl_frame, text="⏭ Step", style="Accent.TButton",
                   command=self._step_simulation).pack(side="left", padx=5)

        # Metrics display
        metrics_frame = ttk.Frame(tab, style="Dark.TFrame")
        metrics_frame.pack(fill="x", padx=10, pady=5)

        self.metric_labels = {}
        metrics = [
            ("Tick", "0", self.cyan),
            ("Operational", "18", self.green),
            ("Degraded", "0", self.blue),
            ("Recovering", "0", self.yellow),
            ("Failed", "0", self.red),
            ("Resilience", "100.0%", self.green),
            ("Cascade Depth", "0", self.cyan),
        ]

        for name, default, color in metrics:
            card = tk.Frame(metrics_frame, bg="#111b33", bd=1, relief="solid",
                           highlightbackground="#1f2937", highlightthickness=1)
            card.pack(side="left", expand=True, fill="both", padx=3, pady=2)
            tk.Label(card, text=name.upper(), bg="#111b33", fg=self.fg_dim,
                    font=("Inter", 7, "bold")).pack(pady=(4, 0))
            lbl = tk.Label(card, text=default, bg="#111b33", fg=color,
                          font=("JetBrains Mono", 14, "bold"))
            lbl.pack(pady=(0, 4))
            self.metric_labels[name] = lbl

        # Event log
        log_frame = ttk.Frame(tab, style="Dark.TFrame")
        log_frame.pack(fill="both", expand=True, padx=10, pady=5)

        ttk.Label(log_frame, text="EVENT LOG", style="SubHeader.TLabel").pack(anchor="w", pady=(0, 4))

        self.event_tree = ttk.Treeview(log_frame, style="Dark.Treeview",
                                        columns=("Tick", "Node", "Dept", "From", "To", "Depth"),
                                        show="headings", height=12)
        for col in ("Tick", "Node", "Dept", "From", "To", "Depth"):
            self.event_tree.heading(col, text=col)
            self.event_tree.column(col, width=80 if col in ("Tick", "Depth") else 140)

        scrollbar = ttk.Scrollbar(log_frame, orient="vertical", command=self.event_tree.yview)
        self.event_tree.configure(yscrollcommand=scrollbar.set)
        self.event_tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

    # ── TAB 2: WEB SCRAPER ──────────────────────────────────────

    def _build_scraper_tab(self):
        """Build the Web Scraper tab."""
        tab = ttk.Frame(self.notebook, style="Dark.TFrame")
        self.notebook.add(tab, text="  🌐 Web Scraper  ")

        # Buttons
        btn_frame = ttk.Frame(tab, style="Dark.TFrame")
        btn_frame.pack(fill="x", padx=10, pady=8)

        ttk.Button(btn_frame, text="🌤 Fetch Weather", style="Accent.TButton",
                   command=lambda: self._fetch_data("weather")).pack(side="left", padx=4)
        ttk.Button(btn_frame, text="💨 Fetch AQI", style="Accent.TButton",
                   command=lambda: self._fetch_data("air_quality")).pack(side="left", padx=4)
        ttk.Button(btn_frame, text="🌍 Fetch Seismic", style="Accent.TButton",
                   command=lambda: self._fetch_data("seismic")).pack(side="left", padx=4)
        ttk.Button(btn_frame, text="📰 Scrape News", style="Accent.TButton",
                   command=lambda: self._fetch_data("news")).pack(side="left", padx=4)
        ttk.Button(btn_frame, text="🔄 Fetch ALL", style="Success.TButton",
                   command=lambda: self._fetch_data("all")).pack(side="left", padx=4)

        # Data display
        self.scraper_text = tk.Text(tab, bg=self.bg_entry, fg=self.fg, insertbackground=self.fg,
                                     font=("JetBrains Mono", 9), wrap="word", padx=10, pady=10)
        self.scraper_text.pack(fill="both", expand=True, padx=10, pady=5)
        self.scraper_text.insert("1.0", "Click a button above to fetch real-time Nagpur city data.\n\n"
                                         "Available sources:\n"
                                         "  • Weather (wttr.in) — Temperature, humidity, wind, rain\n"
                                         "  • Air Quality (WAQI) — AQI, pollutants, health advisory\n"
                                         "  • Seismic (USGS) — Recent earthquakes near Nagpur\n"
                                         "  • News (Google News) — Infrastructure-related headlines\n")

    # ── TAB 3: ANALYTICS ────────────────────────────────────────

    def _build_analytics_tab(self):
        """Build the Analytics & Export tab."""
        tab = ttk.Frame(self.notebook, style="Dark.TFrame")
        self.notebook.add(tab, text="  📊 Analytics & Export  ")

        # Buttons
        btn_frame = ttk.Frame(tab, style="Dark.TFrame")
        btn_frame.pack(fill="x", padx=10, pady=8)

        ttk.Button(btn_frame, text="📊 Generate Full Report", style="Success.TButton",
                   command=self._generate_full_report).pack(side="left", padx=4)
        ttk.Button(btn_frame, text="📁 Export CSV", style="Accent.TButton",
                   command=self._export_csv).pack(side="left", padx=4)
        ttk.Button(btn_frame, text="📗 Export Excel", style="Accent.TButton",
                   command=self._export_excel).pack(side="left", padx=4)
        ttk.Button(btn_frame, text="📂 Open Output Folder", style="Accent.TButton",
                   command=self._open_output_folder).pack(side="left", padx=4)

        # Report display
        self.analytics_text = tk.Text(tab, bg=self.bg_entry, fg=self.fg, insertbackground=self.fg,
                                       font=("JetBrains Mono", 9), wrap="word", padx=10, pady=10)
        self.analytics_text.pack(fill="both", expand=True, padx=10, pady=5)
        self.analytics_text.insert("1.0", "Click 'Generate Full Report' to run all scenarios,\n"
                                           "generate charts, and export CSV/Excel files.\n\n"
                                           "Generated files will be saved to:\n"
                                           f"  {self.analytics.output_dir}/\n")

    # ── TAB 4: DATABASE ─────────────────────────────────────────

    def _build_database_tab(self):
        """Build the Database Viewer tab."""
        tab = ttk.Frame(self.notebook, style="Dark.TFrame")
        self.notebook.add(tab, text="  🗄 Database  ")

        btn_frame = ttk.Frame(tab, style="Dark.TFrame")
        btn_frame.pack(fill="x", padx=10, pady=8)

        ttk.Button(btn_frame, text="🔄 Refresh", style="Accent.TButton",
                   command=self._refresh_db_view).pack(side="left", padx=4)
        ttk.Button(btn_frame, text="💾 Save Current to DB", style="Success.TButton",
                   command=self._save_to_db).pack(side="left", padx=4)
        ttk.Button(btn_frame, text="📊 DB Statistics", style="Accent.TButton",
                   command=self._show_db_stats).pack(side="left", padx=4)

        # Run history tree
        tree_frame = ttk.Frame(tab, style="Dark.TFrame")
        tree_frame.pack(fill="both", expand=True, padx=10, pady=5)

        ttk.Label(tree_frame, text="SIMULATION RUN HISTORY", style="SubHeader.TLabel").pack(anchor="w", pady=(0, 4))

        self.db_tree = ttk.Treeview(tree_frame, style="Dark.Treeview",
                                     columns=("ID", "Scenario", "Severity", "Ticks", "Peaks", "Resilience", "Date"),
                                     show="headings", height=10)
        for col, width in [("ID", 40), ("Scenario", 160), ("Severity", 100), ("Ticks", 60),
                           ("Peaks", 60), ("Resilience", 80), ("Date", 150)]:
            self.db_tree.heading(col, text=col)
            self.db_tree.column(col, width=width)

        db_scroll = ttk.Scrollbar(tree_frame, orient="vertical", command=self.db_tree.yview)
        self.db_tree.configure(yscrollcommand=db_scroll.set)
        self.db_tree.pack(side="left", fill="both", expand=True)
        db_scroll.pack(side="right", fill="y")

        # Info panel
        self.db_info_text = tk.Text(tab, bg=self.bg_entry, fg=self.fg, font=("JetBrains Mono", 8),
                                     wrap="word", height=8, padx=8, pady=8)
        self.db_info_text.pack(fill="x", padx=10, pady=5)

    # ═══════════════════════════════════════════════════════════
    #  SIMULATION ACTIONS
    # ═══════════════════════════════════════════════════════════

    def _run_scenario(self):
        """Run the selected scenario."""
        self._update_status("Running scenario...")
        self.engine.reset()
        scenario_key = self.scenario_var.get()

        def task():
            state = self.engine.run_scenario_to_completion(scenario_key)
            self.current_results = {scenario_key: {
                "scenario_name": SCENARIOS[scenario_key]["name"],
                "severity": SCENARIOS[scenario_key]["severity"],
                "final_tick": state["tick"],
                "peak_fail_count": state["metrics"]["peakFailCount"],
                "cascade_depth": state["metrics"]["cascadeDepth"],
                "affected_count": state["metrics"]["affectedCount"],
                "final_resilience": state["metrics"]["resilienceIndex"],
                "event_count": len(state["eventLog"]),
                "tick_snapshots": state["tickSnapshots"],
                "event_log": state["eventLog"],
                "final_status_counts": state["metrics"]["statusCounts"],
                "nodes": state["nodes"],
            }}
            self.root.after(0, lambda: self._update_ui_after_run(state))

        threading.Thread(target=task, daemon=True).start()

    def _run_all_scenarios(self):
        """Run all scenarios and store results."""
        self._update_status("Running all 4 scenarios...")

        def task():
            engine = GraphEngine()
            results = self.analytics.run_all_scenarios_analysis(engine)
            self.current_results = results
            self.root.after(0, lambda: self._update_status(
                f"✅ All 4 scenarios completed. {sum(r['event_count'] for r in results.values())} total events."))
            # Show last scenario state
            last_key = list(results.keys())[-1]
            last = results[last_key]
            self.root.after(0, lambda: self._populate_event_tree(last["event_log"]))
            self.root.after(0, lambda: self._update_metrics_display({
                "tick": last["final_tick"],
                "metrics": {
                    "statusCounts": last["final_status_counts"],
                    "resilienceIndex": last["final_resilience"],
                    "cascadeDepth": last["cascade_depth"],
                },
            }))

        threading.Thread(target=task, daemon=True).start()

    def _step_simulation(self):
        """Step the simulation by one tick."""
        changed = self.engine.step()
        state = self.engine.export_state()
        self._update_metrics_display(state)
        self._populate_event_tree(state["eventLog"])
        if not changed:
            self._update_status(f"T+{state['tick']}: No state changes — simulation stable.")
        else:
            self._update_status(f"T+{state['tick']}: State changes propagated.")

    def _reset_simulation(self):
        """Reset the simulation."""
        self.engine.reset()
        state = self.engine.export_state()
        self._update_metrics_display(state)
        self.event_tree.delete(*self.event_tree.get_children())
        self._update_status("Simulation reset to initial state.")

    def _update_ui_after_run(self, state: dict):
        """Update UI after a scenario run completes."""
        self._update_metrics_display(state)
        self._populate_event_tree(state["eventLog"])
        counts = state["metrics"]["statusCounts"]
        self._update_status(
            f"✅ Scenario complete at T+{state['tick']} | "
            f"OP:{counts['op']} DEG:{counts['deg']} REC:{counts['rec']} FAIL:{counts['fail']} | "
            f"Resilience: {state['metrics']['resilienceIndex']:.1f}%"
        )

    def _update_metrics_display(self, state: dict):
        """Update the metric cards."""
        counts = state["metrics"]["statusCounts"]
        resilience = state["metrics"]["resilienceIndex"]
        cascade = state["metrics"].get("cascadeDepth", 0)

        self.metric_labels["Tick"].config(text=str(state["tick"]))
        self.metric_labels["Operational"].config(text=str(counts["op"]))
        self.metric_labels["Degraded"].config(text=str(counts["deg"]))
        self.metric_labels["Recovering"].config(text=str(counts["rec"]))
        self.metric_labels["Failed"].config(text=str(counts["fail"]))
        self.metric_labels["Resilience"].config(text=f"{resilience:.1f}%")
        self.metric_labels["Cascade Depth"].config(text=str(cascade))

        # Color coding for resilience
        if resilience < 30:
            self.metric_labels["Resilience"].config(fg=self.red)
        elif resilience < 60:
            self.metric_labels["Resilience"].config(fg=self.yellow)
        else:
            self.metric_labels["Resilience"].config(fg=self.green)

    def _populate_event_tree(self, events: list):
        """Populate the event log treeview."""
        self.event_tree.delete(*self.event_tree.get_children())
        for evt in events:
            self.event_tree.insert("", "end", values=(
                evt.get("tick", ""),
                evt.get("nodeName", ""),
                evt.get("dept", ""),
                evt.get("fromState", ""),
                evt.get("toState", ""),
                evt.get("cascadeDepth", 0),
            ))

    # ═══════════════════════════════════════════════════════════
    #  SCRAPER ACTIONS
    # ═══════════════════════════════════════════════════════════

    def _fetch_data(self, data_type: str):
        """Fetch data from web sources."""
        self._update_status(f"Fetching {data_type} data...")
        self.scraper_text.delete("1.0", "end")
        self.scraper_text.insert("1.0", f"⏳ Fetching {data_type} data for Nagpur...\n")

        def task():
            try:
                if data_type == "weather":
                    result = self.scraper.fetch_weather()
                elif data_type == "air_quality":
                    result = self.scraper.fetch_air_quality()
                elif data_type == "seismic":
                    result = self.scraper.fetch_seismic_data()
                elif data_type == "news":
                    result = self.scraper.scrape_nagpur_infrastructure_news()
                elif data_type == "all":
                    result = self.scraper.fetch_all_data()
                else:
                    result = {"error": "Unknown data type"}

                self.scraped_data = result

                # Save to DB
                risk = result.get("risk_assessment", {}).get("level", "N/A") if isinstance(result, dict) else "N/A"
                self.db.save_scraped_data(data_type, result, risk)

                formatted = json.dumps(result, indent=2, default=str)
                self.root.after(0, lambda: self._display_scraped_data(data_type, formatted))

            except Exception as e:
                self.root.after(0, lambda: self._display_scraped_data(data_type, f"Error: {e}"))

        threading.Thread(target=task, daemon=True).start()

    def _display_scraped_data(self, data_type: str, content: str):
        """Display scraped data in the text widget."""
        self.scraper_text.delete("1.0", "end")
        self.scraper_text.insert("1.0", f"═══ {data_type.upper()} DATA ═══\n\n{content}\n")
        self._update_status(f"✅ {data_type} data fetched and saved to database.")

    # ═══════════════════════════════════════════════════════════
    #  ANALYTICS ACTIONS
    # ═══════════════════════════════════════════════════════════

    def _generate_full_report(self):
        """Generate full analytics report with charts and exports."""
        self._update_status("Generating full report (charts + CSV + Excel)...")
        self.analytics_text.delete("1.0", "end")
        self.analytics_text.insert("1.0", "⏳ Running all scenarios and generating analytics...\n")

        def task():
            try:
                report = self.analytics.generate_full_report(self.scraped_data)
                self.current_results = report["results"]
                files = report["generated_files"]

                # Save to database
                self.db.save_all_simulation_runs(report["results"])

                output = "═══ FULL REPORT GENERATED ═══\n\n"
                output += "📊 Charts Generated:\n"
                for f in files["charts"]:
                    if f:
                        output += f"  • {os.path.basename(f)}\n"
                output += f"\n📁 CSV Files:\n"
                for f in files["csv_files"]:
                    if f:
                        output += f"  • {os.path.basename(f)}\n"
                output += f"\n📗 Excel Workbook:\n  • {os.path.basename(files['excel_file'])}\n"
                output += f"\n📂 Output folder: {self.analytics.output_dir}\n"
                output += "\n═══ SCENARIO COMPARISON ═══\n\n"

                for key, data in report["results"].items():
                    output += (
                        f"▸ {data['scenario_name']} [{data['severity']}]\n"
                        f"    Ticks: {data['final_tick']} | Peak Failures: {data['peak_fail_count']} | "
                        f"Cascade Depth: {data['cascade_depth']}\n"
                        f"    Final Resilience: {data['final_resilience']:.1f}% | Events: {data['event_count']}\n\n"
                    )

                self.root.after(0, lambda: self._show_report(output))

            except Exception as e:
                self.root.after(0, lambda: self._show_report(f"Error generating report: {e}"))

        threading.Thread(target=task, daemon=True).start()

    def _show_report(self, content: str):
        """Display report in analytics text widget."""
        self.analytics_text.delete("1.0", "end")
        self.analytics_text.insert("1.0", content)
        self._update_status("✅ Full report generated. Check the Analytics tab and output folder.")

    def _export_csv(self):
        """Export current results to CSV."""
        if not self.current_results:
            messagebox.showwarning("No Data", "Run a simulation first before exporting.")
            return

        for key, data in self.current_results.items():
            path = self.analytics.export_event_log_csv(data["event_log"], f"events_{key}.csv")
            self._update_status(f"✅ CSV exported: {os.path.basename(path)}")

        self.analytics.export_scenario_comparison_csv(self.current_results)
        self.analytics.export_node_status_csv(self.current_results)
        self._update_status("✅ All CSV files exported to output folder.")

    def _export_excel(self):
        """Export current results to Excel."""
        if not self.current_results:
            messagebox.showwarning("No Data", "Run a simulation first before exporting.")
            return

        path = self.analytics.export_all_to_excel(self.current_results, self.scraped_data)
        self._update_status(f"✅ Excel workbook exported: {os.path.basename(path)}")
        messagebox.showinfo("Export Complete", f"Excel file saved to:\n{path}")

    def _open_output_folder(self):
        """Open the output folder in file explorer."""
        import subprocess
        import platform
        path = self.analytics.output_dir
        if platform.system() == "Darwin":
            subprocess.run(["open", path])
        elif platform.system() == "Windows":
            subprocess.run(["explorer", path])
        else:
            subprocess.run(["xdg-open", path])

    # ═══════════════════════════════════════════════════════════
    #  DATABASE ACTIONS
    # ═══════════════════════════════════════════════════════════

    def _refresh_db_view(self):
        """Refresh the database run history view."""
        self.db_tree.delete(*self.db_tree.get_children())
        runs = self.db.get_all_runs()
        for run in runs:
            self.db_tree.insert("", "end", values=(
                run["id"],
                run["scenario_name"],
                run["severity"],
                run["total_ticks"],
                run["peak_fail_count"],
                f"{run['final_resilience']:.1f}%",
                run["created_at"],
            ))
        self._update_status(f"Database refreshed. {len(runs)} simulation runs found.")

    def _save_to_db(self):
        """Save current results to database."""
        if not self.current_results:
            messagebox.showwarning("No Data", "Run a simulation first before saving.")
            return

        run_ids = self.db.save_all_simulation_runs(self.current_results)
        self._update_status(f"✅ Saved {len(run_ids)} simulation runs to database.")
        self._refresh_db_view()

    def _show_db_stats(self):
        """Show database statistics."""
        stats = self.db.get_statistics()
        self.db_info_text.delete("1.0", "end")

        text = "═══ DATABASE STATISTICS ═══\n\n"
        text += f"Total Simulation Runs: {stats['total_runs']}\n"
        text += f"Total Events Logged: {stats['total_events']}\n"
        text += f"Scraped Data Records: {stats['total_scraped_records']}\n\n"

        if stats["scenario_stats"]:
            text += "Per-Scenario Averages:\n"
            for s in stats["scenario_stats"]:
                text += (
                    f"  ▸ {s['scenario_name']}: {s['run_count']} runs | "
                    f"Avg Resilience: {s['avg_resilience']:.1f}% | "
                    f"Avg Peak Failures: {s['avg_peak_failures']:.1f}\n"
                )

        self.db_info_text.insert("1.0", text)

    # ═══════════════════════════════════════════════════════════
    #  UTILITY
    # ═══════════════════════════════════════════════════════════

    def _update_status(self, msg: str):
        """Update the status bar."""
        self.status_var.set(f"  {msg}")
        logger.info(msg)


def main():
    """Launch the Tkinter GUI."""
    root = tk.Tk()
    app = CascadeSimulatorGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
