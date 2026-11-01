/* =============================================================
   URBAN CASCADE SIMULATOR — GRAPH ENGINE
   Core simulation engine: DiGraph, BFS cascade, recovery, metrics
   ============================================================= */

class GraphEngine {
    /**
     * @param {Array} nodesData - Array of node definition objects
     * @param {Array} edgesData - Array of directed edge objects {u, v, weight}
     */
    constructor(nodesData, edgesData) {
        this.nodes = new Map();
        this.edges = [];
        this.tick = 0;
        this.recoveryQueue = new Map();   // nodeId -> recovery completion tick
        this.eventLog = [];               // Structured timestep log [{tick, nodeId, nodeName, event, fromState, toState, depth}]
        this.failureOrigins = new Map();  // nodeId -> {originId, depth} — tracks cascade provenance
        this.maxCascadeDepth = 0;
        this.peakFailCount = 0;

        // Initialize nodes with full state
        nodesData.forEach(n => {
            this.nodes.set(n.id, {
                ...n,
                state: STATUS.OP,
                failTick: null,
                recoveryTick: null,
                inStress: 0.0,
                baselineNoise: 0.0
            });
        });

        // Copy edges
        edgesData.forEach(e => this.edges.push({ ...e }));
    }

    /* ---------------------------------------------------------
       GRAPH QUERY METHODS
       --------------------------------------------------------- */

    /** Get all edges pointing INTO this node (upstream providers) */
    getInEdges(nodeId) {
        return this.edges.filter(e => e.v === nodeId);
    }

    /** Get all edges pointing OUT from this node (downstream dependents) */
    getOutEdges(nodeId) {
        return this.edges.filter(e => e.u === nodeId);
    }

    /** Get upstream provider node IDs */
    getUpstream(nodeId) {
        return this.getInEdges(nodeId).map(e => e.u);
    }

    /** Get downstream dependent node IDs */
    getDownstream(nodeId) {
        return this.getOutEdges(nodeId).map(e => e.v);
    }

    /* ---------------------------------------------------------
       CASCADE DEPTH CALCULATION (BFS from failure origins)
       --------------------------------------------------------- */

    /**
     * Compute BFS cascade depth from a given origin node
     * Returns the maximum number of hops the failure traveled
     */
    _computeCascadeDepthFrom(originId) {
        const visited = new Set();
        const queue = [{ id: originId, depth: 0 }];
        let maxDepth = 0;

        while (queue.length > 0) {
            const { id, depth } = queue.shift();
            if (visited.has(id)) continue;
            visited.add(id);

            const node = this.nodes.get(id);
            if (!node || (node.state !== STATUS.FAIL && node.state !== STATUS.DEG && depth > 0)) continue;

            maxDepth = Math.max(maxDepth, depth);

            // BFS through downstream edges
            this.getOutEdges(id).forEach(edge => {
                if (!visited.has(edge.v)) {
                    const target = this.nodes.get(edge.v);
                    if (target && (target.state === STATUS.FAIL || target.state === STATUS.DEG)) {
                        queue.push({ id: edge.v, depth: depth + 1 });
                    }
                }
            });
        }

        return maxDepth;
    }

    /** Get maximum cascade depth across all failure origins */
    getCascadeDepth() {
        let maxDepth = 0;
        // Find all nodes that were directly failed (not cascade-failed)
        this.nodes.forEach((node, id) => {
            if (node.state === STATUS.FAIL && this.failureOrigins.has(id)) {
                const origin = this.failureOrigins.get(id);
                if (origin.isDirectFail) {
                    maxDepth = Math.max(maxDepth, this._computeCascadeDepthFrom(id));
                }
            }
        });
        // Also check from any directly-failed node regardless
        if (maxDepth === 0) {
            this.nodes.forEach((node, id) => {
                if (node.state === STATUS.FAIL || node.state === STATUS.DEG) {
                    maxDepth = Math.max(maxDepth, this._computeCascadeDepthFrom(id));
                }
            });
        }
        this.maxCascadeDepth = maxDepth;
        return maxDepth;
    }

    /* ---------------------------------------------------------
       METRICS QUERIES
       --------------------------------------------------------- */

    /** Count of non-OPERATIONAL nodes */
    getAffectedCount() {
        let count = 0;
        this.nodes.forEach(n => {
            if (n.state !== STATUS.OP) count++;
        });
        return count;
    }

    /** Sum of remaining recovery ticks across all recovering/failed nodes */
    getTotalRecoveryTime() {
        let total = 0;
        this.recoveryQueue.forEach((finishTick, nodeId) => {
            const remaining = finishTick - this.tick;
            if (remaining > 0) total += remaining;
        });
        // Add estimated time for FAILED nodes not yet in recovery
        this.nodes.forEach((node, id) => {
            if (node.state === STATUS.FAIL && !this.recoveryQueue.has(id)) {
                total += 3; // Estimated: 1 tick to start recovery + 2 ticks to complete
            }
        });
        return total;
    }

    /** Get counts by status */
    getStatusCounts() {
        const counts = { op: 0, deg: 0, rec: 0, fail: 0 };
        this.nodes.forEach(n => {
            if (n.state === STATUS.OP) counts.op++;
            else if (n.state === STATUS.DEG) counts.deg++;
            else if (n.state === STATUS.REC) counts.rec++;
            else if (n.state === STATUS.FAIL) counts.fail++;
        });
        return counts;
    }

    /** Resilience index: weighted percentage of operational capacity */
    getResilienceIndex() {
        const total = this.nodes.size;
        const counts = this.getStatusCounts();
        return ((counts.op * 1.0 + counts.deg * 0.5 + counts.rec * 0.7) / total) * 100;
    }

    /** Get the structured event log */
    getEventLog() {
        return [...this.eventLog];
    }

    /* ---------------------------------------------------------
       CORE SIMULATION STEP
       BFS cascade propagation + recovery + event logging
       --------------------------------------------------------- */

    /**
     * Advance simulation by one tick
     * @param {boolean} autoRecoveryEnabled - Whether auto-recovery is active
     * @param {Function} onNodeStateChange - Callback(nodeId, newState, logMsg, logColor) for UI updates
     * @returns {boolean} Whether any state change occurred this tick
     */
    step(autoRecoveryEnabled = true, onNodeStateChange = null) {
        this.tick += 1;
        const newStates = new Map();
        let eventTriggered = false;

        // ─── 1. AUTO-RECOVERY ─────────────────────────────────────
        if (autoRecoveryEnabled) {
            this.nodes.forEach((node, id) => {
                if (node.state === STATUS.FAIL) {
                    // Check if all upstream providers have recovered
                    const inEdges = this.getInEdges(id);
                    const failedProviders = inEdges.filter(e => this.nodes.get(e.u).state === STATUS.FAIL);

                    if (failedProviders.length === 0) {
                        newStates.set(id, {
                            state: STATUS.REC,
                            msg: `[T+${this.tick}] Node ${node.name} entered RECOVERY state (Yellow).`,
                            color: 'log-yellow'
                        });
                        this.recoveryQueue.set(id, this.tick + 2);
                        eventTriggered = true;
                    }
                } else if (node.state === STATUS.REC) {
                    const finishTick = this.recoveryQueue.get(id);
                    if (this.tick >= finishTick) {
                        newStates.set(id, {
                            state: STATUS.OP,
                            msg: `[T+${this.tick}] Node ${node.name} fully RESTORED to Operational (Green).`,
                            color: 'log-green'
                        });
                        this.recoveryQueue.delete(id);
                        this.failureOrigins.delete(id);
                        eventTriggered = true;
                    }
                }
            });
        }

        // ─── 2. CASCADE FAILURE & DEGRADATION PROPAGATION ─────────
        this.nodes.forEach((node, id) => {
            if (node.state === STATUS.FAIL) return;

            const inEdges = this.getInEdges(id);
            if (inEdges.length === 0) return;

            let totalFailStress = node.baselineNoise || 0.0;
            let totalDegStress = 0.0;

            inEdges.forEach(edge => {
                const source = this.nodes.get(edge.u);
                if (source.state === STATUS.FAIL) {
                    totalFailStress += edge.weight;
                } else if (source.state === STATUS.DEG) {
                    totalDegStress += edge.weight * 0.5;
                }
            });

            const totalStress = Math.max(0, totalFailStress + totalDegStress);
            node.inStress = totalStress;

            // FAILURE threshold check
            if (totalFailStress >= node.thresh) {
                if (node.state !== STATUS.FAIL && !newStates.has(id)) {
                    // Track cascade provenance
                    let cascadeDepth = 1;
                    const failedUpstream = inEdges.filter(e => this.nodes.get(e.u).state === STATUS.FAIL);
                    failedUpstream.forEach(e => {
                        if (this.failureOrigins.has(e.u)) {
                            cascadeDepth = Math.max(cascadeDepth, this.failureOrigins.get(e.u).depth + 1);
                        }
                    });

                    this.failureOrigins.set(id, { depth: cascadeDepth, isDirectFail: false });

                    newStates.set(id, {
                        state: STATUS.FAIL,
                        msg: `[T+${this.tick}] CASCADE HIT: ${node.name} FAILED! Strain: ${totalFailStress.toFixed(2)} ≥ Thresh ${node.thresh}`,
                        color: 'log-red',
                        isShockwave: true,
                        cascadeDepth: cascadeDepth
                    });
                    eventTriggered = true;
                }
            }
            // DEGRADATION threshold check
            else if (totalStress >= node.thresh * 0.45) {
                if (node.state === STATUS.OP && !newStates.has(id)) {
                    newStates.set(id, {
                        state: STATUS.DEG,
                        msg: `[T+${this.tick}] DEGRADED: ${node.name} entered DEGRADED state (Blue). Strain: ${totalStress.toFixed(2)}`,
                        color: 'log-cyan'
                    });
                    eventTriggered = true;
                }
            }
        });

        // ─── 3. APPLY STATE CHANGES ─────────────────────────────
        newStates.forEach((change, id) => {
            const node = this.nodes.get(id);
            const fromState = node.state;
            node.state = change.state;
            if (change.state === STATUS.FAIL) node.failTick = this.tick;

            // Log structured event
            this.eventLog.push({
                tick: this.tick,
                nodeId: id,
                nodeName: node.name,
                dept: node.dept,
                event: change.msg,
                fromState: fromState,
                toState: change.state,
                cascadeDepth: change.cascadeDepth || 0
            });

            // Notify UI
            if (onNodeStateChange) {
                onNodeStateChange(id, change.state, change.msg, change.color, change.isShockwave);
            }
        });

        // Update peak failure count
        const currentFails = this.getStatusCounts().fail;
        this.peakFailCount = Math.max(this.peakFailCount, currentFails);

        return eventTriggered;
    }

    /* ---------------------------------------------------------
       DIRECT FAILURE INJECTION
       --------------------------------------------------------- */

    /**
     * Directly fail a node (user-triggered or scenario-triggered)
     * @param {string} nodeId
     * @param {string} logMsg - Optional custom log message
     * @param {Function} onNodeStateChange - UI callback
     */
    failNode(nodeId, logMsg = null, onNodeStateChange = null) {
        const node = this.nodes.get(nodeId);
        if (!node) return;

        const fromState = node.state;
        node.state = STATUS.FAIL;
        node.failTick = this.tick;

        // Mark as direct failure origin (depth 0)
        this.failureOrigins.set(nodeId, { depth: 0, isDirectFail: true });

        const msg = logMsg || `[T+${this.tick}] DISRUPTION: ${node.name} directly FAILED.`;

        this.eventLog.push({
            tick: this.tick,
            nodeId: nodeId,
            nodeName: node.name,
            dept: node.dept,
            event: msg,
            fromState: fromState,
            toState: STATUS.FAIL,
            cascadeDepth: 0
        });

        if (onNodeStateChange) {
            onNodeStateChange(nodeId, STATUS.FAIL, msg, 'log-red-bold', true);
        }
    }

    /* ---------------------------------------------------------
       SIMULATION RESET
       --------------------------------------------------------- */

    /**
     * Reset the entire graph to initial OPERATIONAL state
     * @param {Function} onNodeStateChange - UI callback
     */
    reset(onNodeStateChange = null) {
        this.tick = 0;
        this.recoveryQueue.clear();
        this.eventLog = [];
        this.failureOrigins.clear();
        this.maxCascadeDepth = 0;
        this.peakFailCount = 0;

        this.nodes.forEach((node, id) => {
            node.state = STATUS.OP;
            node.failTick = null;
            node.recoveryTick = null;
            node.inStress = 0.0;
            node.baselineNoise = 0.0;
            if (onNodeStateChange) {
                onNodeStateChange(id, STATUS.OP, null, null, false);
            }
        });
    }

    /* ---------------------------------------------------------
       STATE EXPORT / IMPORT (for reproducibility)
       --------------------------------------------------------- */

    /** Export simulation state to a serializable object */
    exportState() {
        const nodesState = {};
        this.nodes.forEach((node, id) => {
            nodesState[id] = {
                state: node.state,
                failTick: node.failTick,
                inStress: node.inStress
            };
        });

        return {
            version: '1.0',
            timestamp: new Date().toISOString(),
            seed: window.seedEngine ? window.seedEngine.getSeed() : 'unknown',
            tick: this.tick,
            nodes: nodesState,
            eventLog: this.eventLog,
            metrics: {
                cascadeDepth: this.getCascadeDepth(),
                affectedCount: this.getAffectedCount(),
                recoveryTime: this.getTotalRecoveryTime(),
                resilience: this.getResilienceIndex(),
                peakFailCount: this.peakFailCount
            }
        };
    }

    /** Add a dynamic node at runtime */
    addNode(nodeData) {
        this.nodes.set(nodeData.id, {
            ...nodeData,
            state: STATUS.OP,
            failTick: null,
            recoveryTick: null,
            inStress: 0.0,
            baselineNoise: 0.0
        });
    }

    /** Add a dynamic edge at runtime */
    addEdge(u, v, weight = 0.75) {
        this.edges.push({ u, v, weight });
    }
}
