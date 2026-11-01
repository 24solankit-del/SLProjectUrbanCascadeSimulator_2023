"""
Urban Cascade Simulator — Graph Engine (Python Backend)
Core simulation engine: DiGraph, BFS cascade propagation, recovery, metrics.
This is a Python port of the frontend's graph-engine.js.
"""

from collections import deque
from typing import Callable, Optional

from .config import (
    STATUS_OP, STATUS_DEG, STATUS_REC, STATUS_FAIL,
    INITIAL_NODES, INITIAL_EDGES, SCENARIOS,
)


class GraphEngine:
    """
    Directed graph engine that simulates cascading failures
    across interdependent infrastructure nodes.
    """

    def __init__(self, nodes_data=None, edges_data=None):
        """
        Initialize the graph with node and edge definitions.

        Args:
            nodes_data: List of node definition dicts (defaults to INITIAL_NODES)
            edges_data: List of edge dicts {u, v, weight} (defaults to INITIAL_EDGES)
        """
        self.nodes = {}           # id -> node dict
        self.edges = []           # list of {u, v, weight}
        self.tick = 0
        self.recovery_queue = {}  # node_id -> recovery completion tick
        self.event_log = []       # [{tick, nodeId, nodeName, dept, event, fromState, toState, cascadeDepth}]
        self.failure_origins = {} # node_id -> {depth, is_direct_fail}
        self.max_cascade_depth = 0
        self.peak_fail_count = 0

        nodes_data = nodes_data or INITIAL_NODES
        edges_data = edges_data or INITIAL_EDGES

        for n in nodes_data:
            self.nodes[n["id"]] = {
                **n,
                "state": STATUS_OP,
                "failTick": None,
                "recoveryTick": None,
                "inStress": 0.0,
                "baselineNoise": 0.0,
            }

        for e in edges_data:
            self.edges.append({**e})

    # ── Graph Query Methods ─────────────────────────────────────────

    def get_in_edges(self, node_id: str) -> list:
        """Get all edges pointing INTO this node (upstream providers)."""
        return [e for e in self.edges if e["v"] == node_id]

    def get_out_edges(self, node_id: str) -> list:
        """Get all edges pointing OUT from this node (downstream dependents)."""
        return [e for e in self.edges if e["u"] == node_id]

    def get_upstream(self, node_id: str) -> list:
        """Get upstream provider node IDs."""
        return [e["u"] for e in self.get_in_edges(node_id)]

    def get_downstream(self, node_id: str) -> list:
        """Get downstream dependent node IDs."""
        return [e["v"] for e in self.get_out_edges(node_id)]

    # ── Cascade Depth (BFS) ─────────────────────────────────────────

    def _compute_cascade_depth_from(self, origin_id: str) -> int:
        """Compute BFS cascade depth from a given origin node."""
        visited = set()
        queue = deque([(origin_id, 0)])
        max_depth = 0

        while queue:
            node_id, depth = queue.popleft()
            if node_id in visited:
                continue
            visited.add(node_id)

            node = self.nodes.get(node_id)
            if not node:
                continue
            if depth > 0 and node["state"] not in (STATUS_FAIL, STATUS_DEG):
                continue

            max_depth = max(max_depth, depth)

            for edge in self.get_out_edges(node_id):
                if edge["v"] not in visited:
                    target = self.nodes.get(edge["v"])
                    if target and target["state"] in (STATUS_FAIL, STATUS_DEG):
                        queue.append((edge["v"], depth + 1))

        return max_depth

    def get_cascade_depth(self) -> int:
        """Get maximum cascade depth across all failure origins."""
        max_depth = 0
        for node_id, node in self.nodes.items():
            if node["state"] == STATUS_FAIL and node_id in self.failure_origins:
                origin = self.failure_origins[node_id]
                if origin.get("is_direct_fail"):
                    max_depth = max(max_depth, self._compute_cascade_depth_from(node_id))

        if max_depth == 0:
            for node_id, node in self.nodes.items():
                if node["state"] in (STATUS_FAIL, STATUS_DEG):
                    max_depth = max(max_depth, self._compute_cascade_depth_from(node_id))

        self.max_cascade_depth = max_depth
        return max_depth

    # ── Metrics Queries ─────────────────────────────────────────────

    def get_affected_count(self) -> int:
        """Count of non-OPERATIONAL nodes."""
        return sum(1 for n in self.nodes.values() if n["state"] != STATUS_OP)

    def get_total_recovery_time(self) -> int:
        """Sum of remaining recovery ticks."""
        total = 0
        for node_id, finish_tick in self.recovery_queue.items():
            remaining = finish_tick - self.tick
            if remaining > 0:
                total += remaining
        for node_id, node in self.nodes.items():
            if node["state"] == STATUS_FAIL and node_id not in self.recovery_queue:
                total += 3
        return total

    def get_status_counts(self) -> dict:
        """Get counts by status."""
        counts = {"op": 0, "deg": 0, "rec": 0, "fail": 0}
        for n in self.nodes.values():
            if n["state"] == STATUS_OP:
                counts["op"] += 1
            elif n["state"] == STATUS_DEG:
                counts["deg"] += 1
            elif n["state"] == STATUS_REC:
                counts["rec"] += 1
            elif n["state"] == STATUS_FAIL:
                counts["fail"] += 1
        return counts

    def get_resilience_index(self) -> float:
        """Resilience index: weighted percentage of operational capacity."""
        total = len(self.nodes)
        counts = self.get_status_counts()
        return ((counts["op"] * 1.0 + counts["deg"] * 0.5 + counts["rec"] * 0.7) / total) * 100

    def get_event_log(self) -> list:
        """Get the structured event log."""
        return list(self.event_log)

    # ── Core Simulation Step ────────────────────────────────────────

    def step(self, auto_recovery: bool = True, on_state_change: Optional[Callable] = None) -> bool:
        """
        Advance simulation by one tick.

        Args:
            auto_recovery: Whether auto-recovery is active
            on_state_change: Optional callback(node_id, new_state, msg, color, is_shockwave)

        Returns:
            Whether any state change occurred this tick
        """
        self.tick += 1
        new_states = {}
        event_triggered = False

        # 1. AUTO-RECOVERY
        if auto_recovery:
            for node_id, node in self.nodes.items():
                if node["state"] == STATUS_FAIL:
                    in_edges = self.get_in_edges(node_id)
                    failed_providers = [e for e in in_edges if self.nodes[e["u"]]["state"] == STATUS_FAIL]
                    if len(failed_providers) == 0:
                        new_states[node_id] = {
                            "state": STATUS_REC,
                            "msg": f"[T+{self.tick}] Node {node['name']} entered RECOVERY state.",
                            "color": "log-yellow",
                        }
                        self.recovery_queue[node_id] = self.tick + 2
                        event_triggered = True

                elif node["state"] == STATUS_REC:
                    finish_tick = self.recovery_queue.get(node_id, 0)
                    if self.tick >= finish_tick:
                        new_states[node_id] = {
                            "state": STATUS_OP,
                            "msg": f"[T+{self.tick}] Node {node['name']} fully RESTORED to Operational.",
                            "color": "log-green",
                        }
                        self.recovery_queue.pop(node_id, None)
                        self.failure_origins.pop(node_id, None)
                        event_triggered = True

        # 2. CASCADE FAILURE & DEGRADATION PROPAGATION
        for node_id, node in self.nodes.items():
            if node["state"] == STATUS_FAIL:
                continue

            in_edges = self.get_in_edges(node_id)
            if not in_edges:
                continue

            total_fail_stress = node.get("baselineNoise", 0.0)
            total_deg_stress = 0.0

            for edge in in_edges:
                source = self.nodes[edge["u"]]
                if source["state"] == STATUS_FAIL:
                    total_fail_stress += edge["weight"]
                elif source["state"] == STATUS_DEG:
                    total_deg_stress += edge["weight"] * 0.5

            total_stress = max(0, total_fail_stress + total_deg_stress)
            node["inStress"] = total_stress

            # FAILURE threshold check
            if total_fail_stress >= node["thresh"]:
                if node["state"] != STATUS_FAIL and node_id not in new_states:
                    cascade_depth = 1
                    failed_upstream = [e for e in in_edges if self.nodes[e["u"]]["state"] == STATUS_FAIL]
                    for e in failed_upstream:
                        if e["u"] in self.failure_origins:
                            cascade_depth = max(cascade_depth, self.failure_origins[e["u"]]["depth"] + 1)

                    self.failure_origins[node_id] = {"depth": cascade_depth, "is_direct_fail": False}
                    new_states[node_id] = {
                        "state": STATUS_FAIL,
                        "msg": f"[T+{self.tick}] CASCADE HIT: {node['name']} FAILED! Strain: {total_fail_stress:.2f} >= Thresh {node['thresh']}",
                        "color": "log-red",
                        "is_shockwave": True,
                        "cascade_depth": cascade_depth,
                    }
                    event_triggered = True

            # DEGRADATION threshold check
            elif total_stress >= node["thresh"] * 0.45:
                if node["state"] == STATUS_OP and node_id not in new_states:
                    new_states[node_id] = {
                        "state": STATUS_DEG,
                        "msg": f"[T+{self.tick}] DEGRADED: {node['name']} entered DEGRADED state. Strain: {total_stress:.2f}",
                        "color": "log-cyan",
                    }
                    event_triggered = True

        # 3. APPLY STATE CHANGES
        for node_id, change in new_states.items():
            node = self.nodes[node_id]
            from_state = node["state"]
            node["state"] = change["state"]
            if change["state"] == STATUS_FAIL:
                node["failTick"] = self.tick

            self.event_log.append({
                "tick": self.tick,
                "nodeId": node_id,
                "nodeName": node["name"],
                "dept": node["dept"],
                "event": change["msg"],
                "fromState": from_state,
                "toState": change["state"],
                "cascadeDepth": change.get("cascade_depth", 0),
            })

            if on_state_change:
                on_state_change(
                    node_id, change["state"], change["msg"],
                    change["color"], change.get("is_shockwave", False)
                )

        # Update peak failure count
        current_fails = self.get_status_counts()["fail"]
        self.peak_fail_count = max(self.peak_fail_count, current_fails)

        return event_triggered

    # ── Direct Failure Injection ────────────────────────────────────

    def fail_node(self, node_id: str, log_msg: str = None, on_state_change: Optional[Callable] = None):
        """Directly fail a node (user-triggered or scenario-triggered)."""
        node = self.nodes.get(node_id)
        if not node:
            return

        from_state = node["state"]
        node["state"] = STATUS_FAIL
        node["failTick"] = self.tick

        self.failure_origins[node_id] = {"depth": 0, "is_direct_fail": True}

        msg = log_msg or f"[T+{self.tick}] DISRUPTION: {node['name']} directly FAILED."

        self.event_log.append({
            "tick": self.tick,
            "nodeId": node_id,
            "nodeName": node["name"],
            "dept": node["dept"],
            "event": msg,
            "fromState": from_state,
            "toState": STATUS_FAIL,
            "cascadeDepth": 0,
        })

        if on_state_change:
            on_state_change(node_id, STATUS_FAIL, msg, "log-red-bold", True)

    # ── Scenario Injection ──────────────────────────────────────────

    def inject_scenario(self, scenario_key: str, on_state_change: Optional[Callable] = None):
        """Inject a predefined scenario (flood, cyber, grid, compound)."""
        scenario = SCENARIOS.get(scenario_key)
        if not scenario:
            return

        for node_id in scenario["failNodes"]:
            self.fail_node(node_id, on_state_change=on_state_change)

    # ── Reset ───────────────────────────────────────────────────────

    def reset(self):
        """Reset the entire graph to initial OPERATIONAL state."""
        for node_id, node in self.nodes.items():
            node["state"] = STATUS_OP
            node["failTick"] = None
            node["recoveryTick"] = None
            node["inStress"] = 0.0
            node["baselineNoise"] = 0.0

        self.tick = 0
        self.recovery_queue.clear()
        self.event_log.clear()
        self.failure_origins.clear()
        self.max_cascade_depth = 0
        self.peak_fail_count = 0

    # ── Export State ────────────────────────────────────────────────

    def export_state(self) -> dict:
        """Export the full simulation state as a JSON-serializable dict."""
        nodes_list = []
        for node_id, node in self.nodes.items():
            nodes_list.append({
                "id": node["id"],
                "name": node["name"],
                "dept": node["dept"],
                "state": node["state"],
                "thresh": node["thresh"],
                "inStress": round(node["inStress"], 4),
                "failTick": node["failTick"],
                "desc": node["desc"],
            })

        return {
            "tick": self.tick,
            "nodes": nodes_list,
            "edges": [{"u": e["u"], "v": e["v"], "weight": e["weight"]} for e in self.edges],
            "eventLog": self.event_log,
            "metrics": {
                "cascadeDepth": self.get_cascade_depth(),
                "affectedCount": self.get_affected_count(),
                "recoveryETA": self.get_total_recovery_time(),
                "resilienceIndex": round(self.get_resilience_index(), 2),
                "statusCounts": self.get_status_counts(),
                "peakFailCount": self.peak_fail_count,
            },
        }

    # ── Run Full Scenario (auto-step until stable) ──────────────────

    def run_scenario_to_completion(self, scenario_key: str, max_ticks: int = 50) -> dict:
        """
        Inject a scenario and run the simulation until no more changes occur.
        Returns the final simulation state.
        """
        self.reset()
        self.inject_scenario(scenario_key)

        tick_snapshots = []
        for _ in range(max_ticks):
            snap = {
                "tick": self.tick,
                **self.get_status_counts(),
                "resilience": round(self.get_resilience_index(), 2),
                "cascadeDepth": self.get_cascade_depth(),
                "affected": self.get_affected_count(),
            }
            tick_snapshots.append(snap)

            changed = self.step()
            if not changed:
                # Capture final state
                tick_snapshots.append({
                    "tick": self.tick,
                    **self.get_status_counts(),
                    "resilience": round(self.get_resilience_index(), 2),
                    "cascadeDepth": self.get_cascade_depth(),
                    "affected": self.get_affected_count(),
                })
                break

        state = self.export_state()
        state["tickSnapshots"] = tick_snapshots
        return state
