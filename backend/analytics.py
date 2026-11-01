"""
Urban Cascade Simulator — Analytics Engine
Generates analytics from simulation data and scraped city data.
Exports results to CSV/Excel and generates matplotlib charts.
"""

import os
import logging
from datetime import datetime
from typing import Optional

import pandas as pd
import matplotlib
matplotlib.use("Agg")  # Non-interactive backend for server use
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker

from .config import DEPT_COLORS, SCENARIOS, STATUS_OP, STATUS_FAIL, STATUS_DEG, STATUS_REC
from .graph_engine import GraphEngine

logger = logging.getLogger(__name__)

# Default output directory
OUTPUT_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "output")
os.makedirs(OUTPUT_DIR, exist_ok=True)


class AnalyticsEngine:
    """
    Processes simulation results and scraped data into analytics,
    CSV/Excel exports, and chart images.
    """

    def __init__(self, output_dir: str = None):
        self.output_dir = output_dir or OUTPUT_DIR
        os.makedirs(self.output_dir, exist_ok=True)

    # ═══════════════════════════════════════════════════════════════
    #  SIMULATION ANALYTICS
    # ═══════════════════════════════════════════════════════════════

    def run_all_scenarios_analysis(self, engine: GraphEngine = None) -> dict:
        """
        Run all 4 scenarios to completion and generate comparative analytics.
        Returns dict of results per scenario.
        """
        engine = engine or GraphEngine()
        results = {}

        for scenario_key in SCENARIOS:
            state = engine.run_scenario_to_completion(scenario_key)
            results[scenario_key] = {
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
            }

        return results

    # ═══════════════════════════════════════════════════════════════
    #  CSV / EXCEL EXPORT
    # ═══════════════════════════════════════════════════════════════

    def export_event_log_csv(self, event_log: list, filename: str = None) -> str:
        """Export event log to CSV file."""
        filename = filename or f"cascade_event_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        filepath = os.path.join(self.output_dir, filename)

        df = pd.DataFrame(event_log)
        df.to_csv(filepath, index=False)
        logger.info(f"Event log exported to {filepath}")
        return filepath

    def export_scenario_comparison_csv(self, results: dict, filename: str = None) -> str:
        """Export scenario comparison summary to CSV."""
        filename = filename or f"scenario_comparison_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        filepath = os.path.join(self.output_dir, filename)

        rows = []
        for key, data in results.items():
            rows.append({
                "Scenario": data["scenario_name"],
                "Severity": data["severity"],
                "Total_Ticks": data["final_tick"],
                "Peak_Failures": data["peak_fail_count"],
                "Max_Cascade_Depth": data["cascade_depth"],
                "Total_Events": data["event_count"],
                "Final_Resilience_%": data["final_resilience"],
                "Final_Operational": data["final_status_counts"]["op"],
                "Final_Degraded": data["final_status_counts"]["deg"],
                "Final_Recovering": data["final_status_counts"]["rec"],
                "Final_Failed": data["final_status_counts"]["fail"],
            })

        df = pd.DataFrame(rows)
        df.to_csv(filepath, index=False)
        logger.info(f"Scenario comparison exported to {filepath}")
        return filepath

    def export_node_status_csv(self, results: dict, filename: str = None) -> str:
        """Export node-by-node status across all scenarios to CSV."""
        filename = filename or f"node_status_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        filepath = os.path.join(self.output_dir, filename)

        rows = []
        for scenario_key, data in results.items():
            for node in data["nodes"]:
                rows.append({
                    "Scenario": data["scenario_name"],
                    "Node_ID": node["id"],
                    "Node_Name": node["name"],
                    "Department": node["dept"],
                    "Final_State": node["state"],
                    "Threshold": node["thresh"],
                    "Stress_Level": node["inStress"],
                    "Failed_At_Tick": node["failTick"] if node["failTick"] else "N/A",
                })

        df = pd.DataFrame(rows)
        df.to_csv(filepath, index=False)
        logger.info(f"Node status exported to {filepath}")
        return filepath

    def export_all_to_excel(self, results: dict, scraped_data: dict = None, filename: str = None) -> str:
        """
        Export comprehensive analytics to a multi-sheet Excel workbook.
        Sheets: Summary, Event Log, Node Status, Tick Snapshots, Scraped Data.
        """
        filename = filename or f"urban_cascade_analytics_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        filepath = os.path.join(self.output_dir, filename)

        with pd.ExcelWriter(filepath, engine="openpyxl") as writer:
            # Sheet 1: Scenario Comparison Summary
            summary_rows = []
            for key, data in results.items():
                summary_rows.append({
                    "Scenario": data["scenario_name"],
                    "Severity": data["severity"],
                    "Total_Ticks": data["final_tick"],
                    "Peak_Failures": data["peak_fail_count"],
                    "Max_Cascade_Depth": data["cascade_depth"],
                    "Total_Events": data["event_count"],
                    "Final_Resilience_%": data["final_resilience"],
                })
            pd.DataFrame(summary_rows).to_excel(writer, sheet_name="Summary", index=False)

            # Sheet 2: All Event Logs (combined)
            all_events = []
            for key, data in results.items():
                for event in data["event_log"]:
                    all_events.append({"Scenario": data["scenario_name"], **event})
            pd.DataFrame(all_events).to_excel(writer, sheet_name="Event Log", index=False)

            # Sheet 3: Node Status
            node_rows = []
            for key, data in results.items():
                for node in data["nodes"]:
                    node_rows.append({
                        "Scenario": data["scenario_name"],
                        "Node_ID": node["id"],
                        "Node_Name": node["name"],
                        "Department": node["dept"],
                        "Final_State": node["state"],
                        "Threshold": node["thresh"],
                        "Stress": round(node["inStress"], 4),
                    })
            pd.DataFrame(node_rows).to_excel(writer, sheet_name="Node Status", index=False)

            # Sheet 4: Tick-by-Tick Snapshots
            snap_rows = []
            for key, data in results.items():
                for snap in data["tick_snapshots"]:
                    snap_rows.append({"Scenario": data["scenario_name"], **snap})
            pd.DataFrame(snap_rows).to_excel(writer, sheet_name="Tick Snapshots", index=False)

            # Sheet 5: Scraped Data (if available)
            if scraped_data:
                scraped_rows = []
                for source, info in scraped_data.items():
                    if isinstance(info, dict):
                        scraped_rows.append({
                            "Source": source,
                            "Data": str(info)[:500],
                            "Fetched_At": info.get("timestamp", "N/A"),
                        })
                pd.DataFrame(scraped_rows).to_excel(writer, sheet_name="Scraped Data", index=False)

        logger.info(f"Full analytics exported to {filepath}")
        return filepath

    # ═══════════════════════════════════════════════════════════════
    #  CHART GENERATION (matplotlib)
    # ═══════════════════════════════════════════════════════════════

    def _apply_dark_theme(self, fig, ax):
        """Apply dark HUD-style theme to match the frontend aesthetic."""
        fig.patch.set_facecolor("#0b132b")
        ax.set_facecolor("#0b132b")
        ax.tick_params(colors="#9ca3af", labelsize=8)
        ax.xaxis.label.set_color("#9ca3af")
        ax.yaxis.label.set_color("#9ca3af")
        ax.title.set_color("#22d3ee")
        for spine in ax.spines.values():
            spine.set_color("#1f2937")

    def generate_resilience_chart(self, results: dict, filename: str = None) -> str:
        """Generate resilience index over time chart for all scenarios."""
        filename = filename or "chart_resilience_over_time.png"
        filepath = os.path.join(self.output_dir, filename)

        fig, ax = plt.subplots(figsize=(12, 6))
        self._apply_dark_theme(fig, ax)

        colors = ["#22d3ee", "#f87171", "#fbbf24", "#34d399"]
        for i, (key, data) in enumerate(results.items()):
            ticks = [s["tick"] for s in data["tick_snapshots"]]
            resilience = [s["resilience"] for s in data["tick_snapshots"]]
            ax.plot(ticks, resilience, color=colors[i % len(colors)],
                    linewidth=2, label=data["scenario_name"], marker="o", markersize=4)

        ax.set_xlabel("Simulation Tick", fontsize=10)
        ax.set_ylabel("Resilience Index (%)", fontsize=10)
        ax.set_title("RESILIENCE INDEX OVER TIME — ALL SCENARIOS", fontsize=12, fontweight="bold")
        ax.legend(facecolor="#1f2937", edgecolor="#374151", labelcolor="#f3f4f6", fontsize=8)
        ax.set_ylim(0, 105)
        ax.grid(True, alpha=0.15, color="#374151")
        ax.axhline(y=50, color="#f87171", linestyle="--", alpha=0.4, label="Critical Threshold")

        plt.tight_layout()
        fig.savefig(filepath, dpi=150, bbox_inches="tight", facecolor=fig.get_facecolor())
        plt.close(fig)
        logger.info(f"Resilience chart saved to {filepath}")
        return filepath

    def generate_cascade_depth_chart(self, results: dict, filename: str = None) -> str:
        """Generate cascade depth comparison bar chart."""
        filename = filename or "chart_cascade_depth.png"
        filepath = os.path.join(self.output_dir, filename)

        fig, ax = plt.subplots(figsize=(10, 6))
        self._apply_dark_theme(fig, ax)

        scenarios = [data["scenario_name"] for data in results.values()]
        depths = [data["cascade_depth"] for data in results.values()]
        colors = ["#3b82f6", "#ef4444", "#f59e0b", "#8b5cf6"]

        bars = ax.bar(scenarios, depths, color=colors[:len(scenarios)], edgecolor="#1f2937", linewidth=1.5)
        for bar, depth in zip(bars, depths):
            ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.1,
                    str(depth), ha="center", va="bottom", color="#f3f4f6", fontsize=11, fontweight="bold")

        ax.set_xlabel("Scenario", fontsize=10)
        ax.set_ylabel("Max Cascade Depth (Hops)", fontsize=10)
        ax.set_title("CASCADE DEPTH COMPARISON", fontsize=12, fontweight="bold")
        ax.yaxis.set_major_locator(mticker.MaxNLocator(integer=True))
        ax.grid(True, axis="y", alpha=0.15, color="#374151")

        plt.tight_layout()
        fig.savefig(filepath, dpi=150, bbox_inches="tight", facecolor=fig.get_facecolor())
        plt.close(fig)
        logger.info(f"Cascade depth chart saved to {filepath}")
        return filepath

    def generate_department_impact_chart(self, results: dict, filename: str = None) -> str:
        """Generate department-wise failure heatmap for all scenarios."""
        filename = filename or "chart_department_impact.png"
        filepath = os.path.join(self.output_dir, filename)

        # Build data: for each scenario, count failed nodes per department
        dept_data = {}
        for key, data in results.items():
            scenario_name = data["scenario_name"]
            dept_counts = {}
            for node in data["nodes"]:
                dept = node["dept"]
                if dept not in dept_counts:
                    dept_counts[dept] = {"total": 0, "failed": 0}
                dept_counts[dept]["total"] += 1
                if node["state"] == STATUS_FAIL:
                    dept_counts[dept]["failed"] += 1
            dept_data[scenario_name] = dept_counts

        depts = sorted(set(d for sc in dept_data.values() for d in sc.keys()))
        scenarios = list(dept_data.keys())

        fig, ax = plt.subplots(figsize=(12, 6))
        self._apply_dark_theme(fig, ax)

        x = range(len(depts))
        width = 0.2
        colors = ["#22d3ee", "#f87171", "#fbbf24", "#34d399"]

        for i, scenario in enumerate(scenarios):
            values = [dept_data[scenario].get(d, {}).get("failed", 0) for d in depts]
            offset = (i - len(scenarios) / 2 + 0.5) * width
            ax.bar([xi + offset for xi in x], values, width,
                   label=scenario, color=colors[i % len(colors)], edgecolor="#1f2937")

        ax.set_xlabel("Department", fontsize=10)
        ax.set_ylabel("Failed Nodes", fontsize=10)
        ax.set_title("DEPARTMENT IMPACT ANALYSIS — ALL SCENARIOS", fontsize=12, fontweight="bold")
        ax.set_xticks(list(x))
        ax.set_xticklabels(depts, rotation=30, ha="right", fontsize=8)
        ax.legend(facecolor="#1f2937", edgecolor="#374151", labelcolor="#f3f4f6", fontsize=7)
        ax.yaxis.set_major_locator(mticker.MaxNLocator(integer=True))
        ax.grid(True, axis="y", alpha=0.15, color="#374151")

        plt.tight_layout()
        fig.savefig(filepath, dpi=150, bbox_inches="tight", facecolor=fig.get_facecolor())
        plt.close(fig)
        logger.info(f"Department impact chart saved to {filepath}")
        return filepath

    def generate_failure_timeline_chart(self, results: dict, scenario_key: str = "grid", filename: str = None) -> str:
        """Generate failure timeline (affected nodes over ticks) for a specific scenario."""
        filename = filename or f"chart_failure_timeline_{scenario_key}.png"
        filepath = os.path.join(self.output_dir, filename)

        data = results.get(scenario_key)
        if not data:
            return ""

        fig, ax = plt.subplots(figsize=(12, 6))
        self._apply_dark_theme(fig, ax)

        snaps = data["tick_snapshots"]
        ticks = [s["tick"] for s in snaps]
        failed = [s["fail"] for s in snaps]
        degraded = [s["deg"] for s in snaps]
        recovering = [s["rec"] for s in snaps]
        operational = [s["op"] for s in snaps]

        ax.fill_between(ticks, 0, failed, alpha=0.8, color="#ef4444", label="Failed")
        ax.fill_between(ticks, failed, [f + d for f, d in zip(failed, degraded)],
                        alpha=0.7, color="#22d3ee", label="Degraded")
        ax.fill_between(ticks, [f + d for f, d in zip(failed, degraded)],
                        [f + d + r for f, d, r in zip(failed, degraded, recovering)],
                        alpha=0.7, color="#fbbf24", label="Recovering")
        ax.fill_between(ticks, [f + d + r for f, d, r in zip(failed, degraded, recovering)],
                        [f + d + r + o for f, d, r, o in zip(failed, degraded, recovering, operational)],
                        alpha=0.6, color="#10b981", label="Operational")

        ax.set_xlabel("Simulation Tick", fontsize=10)
        ax.set_ylabel("Node Count", fontsize=10)
        ax.set_title(f"FAILURE TIMELINE — {data['scenario_name'].upper()}", fontsize=12, fontweight="bold")
        ax.legend(facecolor="#1f2937", edgecolor="#374151", labelcolor="#f3f4f6", fontsize=8)
        ax.grid(True, alpha=0.15, color="#374151")

        plt.tight_layout()
        fig.savefig(filepath, dpi=150, bbox_inches="tight", facecolor=fig.get_facecolor())
        plt.close(fig)
        logger.info(f"Failure timeline chart saved to {filepath}")
        return filepath

    # ═══════════════════════════════════════════════════════════════
    #  GENERATE ALL
    # ═══════════════════════════════════════════════════════════════

    def generate_full_report(self, scraped_data: dict = None) -> dict:
        """
        Run all scenarios, generate all charts and exports.
        Returns dict with file paths of all generated artifacts.
        """
        engine = GraphEngine()
        results = self.run_all_scenarios_analysis(engine)

        generated = {
            "charts": [],
            "csv_files": [],
            "excel_file": None,
        }

        # Generate charts
        generated["charts"].append(self.generate_resilience_chart(results))
        generated["charts"].append(self.generate_cascade_depth_chart(results))
        generated["charts"].append(self.generate_department_impact_chart(results))
        for scenario_key in SCENARIOS:
            generated["charts"].append(
                self.generate_failure_timeline_chart(results, scenario_key)
            )

        # Generate CSV files
        for key, data in results.items():
            generated["csv_files"].append(
                self.export_event_log_csv(data["event_log"], f"events_{key}.csv")
            )
        generated["csv_files"].append(self.export_scenario_comparison_csv(results))
        generated["csv_files"].append(self.export_node_status_csv(results))

        # Generate Excel workbook
        generated["excel_file"] = self.export_all_to_excel(results, scraped_data)

        return {
            "results": results,
            "generated_files": generated,
        }
