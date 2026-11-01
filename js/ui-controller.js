/* =============================================================
   URBAN CASCADE SIMULATOR — UI CONTROLLER
   All DOM manipulation: HUD, inspector, metrics cards,
   timestep table, event log, dropdowns, controls
   ============================================================= */

class UIController {
    /**
     * @param {GraphEngine} engine
     * @param {Renderer3D} renderer
     * @param {MetricsTracker} metrics
     * @param {SeedEngine} seedEngine
     */
    constructor(engine, renderer, metrics, seedEngine) {
        this.engine = engine;
        this.renderer = renderer;
        this.metrics = metrics;
        this.seedEngine = seedEngine;

        this.selectedNodeId = null;
        this.autoPlayInterval = null;
        this.liveDataInterval = null;

        // Cache DOM references
        this.dom = {
            statOp:          document.getElementById('stat-op'),
            statDeg:         document.getElementById('stat-deg'),
            statRec:         document.getElementById('stat-rec'),
            statFail:        document.getElementById('stat-fail'),
            statResilience:  document.getElementById('stat-resilience'),
            currentTick:     document.getElementById('current-tick'),
            cascadeStateTag: document.getElementById('cascade-state-tag'),
            btnPlay:         document.getElementById('btn-play'),
            eventLog:        document.getElementById('event-log'),
            nodeTargetSel:   document.getElementById('node-target-select'),
            dynNodeName:     document.getElementById('dyn-node-name'),
            dynNodeDept:     document.getElementById('dyn-node-dept'),
            dynNodeParent:   document.getElementById('dyn-node-parent'),
            seedInput:       document.getElementById('seed-input'),
            toggleAutoRecov: document.getElementById('toggle-autorecovery'),
            toggleLiveData:  document.getElementById('toggle-livedata'),

            // Inspector
            inspName:     document.getElementById('insp-name'),
            inspBadge:    document.getElementById('insp-badge'),
            inspDept:     document.getElementById('insp-dept'),
            inspCoord:    document.getElementById('insp-coord'),
            inspThresh:   document.getElementById('insp-thresh'),
            inspParents:  document.getElementById('insp-parents'),
            inspChildren: document.getElementById('insp-children'),
            inspPercent:  document.getElementById('insp-percent'),
            inspTrouble:  document.getElementById('insp-trouble'),
            inspEta:      document.getElementById('insp-eta'),

            // Metrics cards
            metricDepthVal:    document.getElementById('metric-depth-val'),
            metricAffectedVal: document.getElementById('metric-affected-val'),
            metricRecoveryVal: document.getElementById('metric-recovery-val'),
            metricResilienceVal: document.getElementById('metric-resilience-val'),
            metricDepthSub:    document.getElementById('metric-depth-sub'),
            metricAffectedSub: document.getElementById('metric-affected-sub'),
            metricRecoverySub: document.getElementById('metric-recovery-sub'),

            // Sparkline canvases
            sparkDepth:    document.getElementById('spark-depth'),
            sparkAffected: document.getElementById('spark-affected'),
            sparkRecovery: document.getElementById('spark-recovery'),
            sparkResilience: document.getElementById('spark-resilience'),

            // Cascade chart
            chartCanvas: document.getElementById('cascade-chart-canvas'),

            // Timestep table
            timestepTableBody: document.getElementById('timestep-tbody')
        };

        // Populate dropdowns
        this.populateDropdowns();
    }

    /* ---------------------------------------------------------
       HEADER TELEMETRY HUD
       --------------------------------------------------------- */
    updateTelemetryHUD() {
        const counts = this.engine.getStatusCounts();
        this.dom.statOp.innerText = counts.op;
        this.dom.statDeg.innerText = counts.deg;
        this.dom.statRec.innerText = counts.rec;
        this.dom.statFail.innerText = counts.fail;
        this.dom.currentTick.innerText = `T+${this.engine.tick}`;

        const resilience = this.engine.getResilienceIndex();
        this.dom.statResilience.innerText = `${resilience.toFixed(1)}%`;

        // Update inspector if a node is selected
        if (this.selectedNodeId) this.inspectNode(this.selectedNodeId);

        // Update metrics cards
        this.updateMetricsCards();

        // Record metrics snapshot
        this.metrics.record(this.engine);

        // Update charts
        this.updateCharts();

        // Update timestep table
        this.updateTimestepTable();
    }

    /* ---------------------------------------------------------
       METRICS CARDS (Bottom Panel)
       --------------------------------------------------------- */
    updateMetricsCards() {
        const depth = this.engine.getCascadeDepth();
        const affected = this.engine.getAffectedCount();
        const recovery = this.engine.getTotalRecoveryTime();
        const resilience = this.engine.getResilienceIndex();
        const total = this.engine.nodes.size;

        // Cascade Depth
        if (this.dom.metricDepthVal) {
            this.dom.metricDepthVal.innerText = depth;
            this.dom.metricDepthSub.innerText = `max: ${this.metrics.maxDepthEver} hops`;
        }

        // Affected Services
        if (this.dom.metricAffectedVal) {
            this.dom.metricAffectedVal.innerText = affected;
            this.dom.metricAffectedSub.innerText = `of ${total} services`;
        }

        // Recovery ETA
        if (this.dom.metricRecoveryVal) {
            this.dom.metricRecoveryVal.innerText = recovery;
            this.dom.metricRecoverySub.innerText = recovery > 0 ? 'ticks remaining' : 'all clear';
        }

        // Resilience
        if (this.dom.metricResilienceVal) {
            this.dom.metricResilienceVal.innerText = `${resilience.toFixed(1)}%`;
        }
    }

    /* ---------------------------------------------------------
       SPARKLINE & PROGRESSION CHARTS
       --------------------------------------------------------- */
    updateCharts() {
        this.metrics.drawSparkline(this.dom.sparkDepth, 'cascadeDepth', 'rgb(34, 211, 238)');
        this.metrics.drawSparkline(this.dom.sparkAffected, 'affectedCount', 'rgb(239, 68, 68)');
        this.metrics.drawSparkline(this.dom.sparkRecovery, 'recoveryTime', 'rgb(250, 204, 21)');
        this.metrics.drawSparkline(this.dom.sparkResilience, 'resilience', 'rgb(52, 211, 153)');
        this.metrics.drawProgressionChart(this.dom.chartCanvas);
    }

    /* ---------------------------------------------------------
       TIMESTEP EVENT TABLE
       --------------------------------------------------------- */
    updateTimestepTable() {
        if (!this.dom.timestepTableBody) return;

        const events = this.engine.getEventLog();
        // Show last 50 events (newest first)
        const recent = events.slice(-50).reverse();

        let html = '';
        recent.forEach(evt => {
            let stateClass = '';
            if (evt.toState === STATUS.FAIL) stateClass = 'td-fail';
            else if (evt.toState === STATUS.DEG) stateClass = 'td-deg';
            else if (evt.toState === STATUS.REC) stateClass = 'td-rec';
            else if (evt.toState === STATUS.OP) stateClass = 'td-op';

            html += `<tr>
                <td>T+${evt.tick}</td>
                <td>${evt.nodeName}</td>
                <td>${evt.dept}</td>
                <td class="${stateClass}">${evt.toState}</td>
                <td>${evt.cascadeDepth || 0}</td>
            </tr>`;
        });

        this.dom.timestepTableBody.innerHTML = html;
    }

    /* ---------------------------------------------------------
       NODE INSPECTOR PANEL
       --------------------------------------------------------- */
    inspectNode(nodeId) {
        this.selectedNodeId = nodeId;
        const node = this.engine.nodes.get(nodeId);
        if (!node) return;

        this.dom.inspName.innerText = node.name;
        this.dom.inspDept.innerText = node.dept;
        this.dom.inspCoord.innerText = `[${node.pos[0]}, ${node.pos[2]}] (Nagpur Grid)`;
        this.dom.inspThresh.innerText = `${node.thresh.toFixed(2)} Strain Units`;

        const inNames = this.engine.getInEdges(nodeId).map(e => this.engine.nodes.get(e.u).name);
        const outNames = this.engine.getOutEdges(nodeId).map(e => this.engine.nodes.get(e.v).name);

        this.dom.inspParents.innerText = inNames.length ? inNames.join(', ') : 'None (Root Producer)';
        this.dom.inspChildren.innerText = outNames.length ? outNames.join(', ') : 'None (Terminal Lifeline)';

        // Badge
        this.dom.inspBadge.innerText = node.state;
        this.dom.inspBadge.className = `inspector-badge ${STATUS_CSS[node.state]}`;

        // Percent affected
        let percent = (node.inStress / node.thresh) * 100;
        if (node.state === STATUS.FAIL) percent = 100;
        if (percent < 0) percent = 0;
        this.dom.inspPercent.innerText = `${percent.toFixed(1)}%`;

        // Level of trouble
        let trouble = 'Nominal operation';
        if (node.state === STATUS.DEG) trouble = 'Capacity reduced due to upstream strain';
        if (node.state === STATUS.FAIL) trouble = 'Catastrophic failure. Service offline.';
        if (node.state === STATUS.REC) trouble = 'Repairs ongoing. Rebooting subsystems.';
        if (node.state === STATUS.OP && node.inStress > 0.1) trouble = 'Minor real-time load fluctuations';
        this.dom.inspTrouble.innerText = trouble;

        // Recovery ETA
        if (node.state === STATUS.REC) {
            const ticksLeft = this.engine.recoveryQueue.get(nodeId) - this.engine.tick;
            this.dom.inspEta.innerText = ticksLeft > 0 ? `${ticksLeft} Ticks` : 'Imminent';
        } else if (node.state === STATUS.FAIL) {
            this.dom.inspEta.innerText = 'Awaiting Upstream Fix';
        } else {
            this.dom.inspEta.innerText = 'N/A';
        }
    }

    /* ---------------------------------------------------------
       EVENT LOG
       --------------------------------------------------------- */
    addLog(msg, colorClass = 'log-dim') {
        const row = document.createElement('div');
        row.className = colorClass;
        row.innerText = msg;
        this.dom.eventLog.appendChild(row);
        this.dom.eventLog.scrollTop = this.dom.eventLog.scrollHeight;
    }

    clearLogs() {
        this.dom.eventLog.innerHTML = '';
    }

    /* ---------------------------------------------------------
       DROPDOWN POPULATION
       --------------------------------------------------------- */
    populateDropdowns() {
        this.dom.nodeTargetSel.innerHTML = '';
        this.dom.dynNodeParent.innerHTML = '';

        this.engine.nodes.forEach(node => {
            const opt1 = document.createElement('option');
            opt1.value = node.id;
            opt1.innerText = `${node.name} (${node.dept})`;
            this.dom.nodeTargetSel.appendChild(opt1);

            const opt2 = document.createElement('option');
            opt2.value = node.id;
            opt2.innerText = `${node.name} (${node.dept})`;
            this.dom.dynNodeParent.appendChild(opt2);
        });
    }

    /* ---------------------------------------------------------
       SIMULATION CONTROLS
       --------------------------------------------------------- */

    /** The onNodeStateChange callback wired into GraphEngine.step() */
    _onNodeStateChange(nodeId, newState, logMsg, logColor, isShockwave) {
        this.renderer.updateNodeVisual(nodeId, this.engine);
        if (logMsg) this.addLog(logMsg, logColor);
        if (isShockwave) {
            const node = this.engine.nodes.get(nodeId);
            if (node) this.renderer.createShockwave(node.pos);
        }
    }

    /** Step one cascade wave */
    stepCascadeWave() {
        const autoRecov = this.dom.toggleAutoRecov.checked;
        this.engine.step(autoRecov, (id, state, msg, color, shock) => {
            this._onNodeStateChange(id, state, msg, color, shock);
        });
        this.updateTelemetryHUD();
    }

    /** Toggle auto-play simulation */
    toggleAutoPlay() {
        if (this.autoPlayInterval) {
            clearInterval(this.autoPlayInterval);
            this.autoPlayInterval = null;
            this.dom.btnPlay.innerHTML = '<i class="fa-solid fa-play"></i> Auto Sim';
            this.dom.btnPlay.className = 'btn-sim play';
            this.dom.cascadeStateTag.innerText = 'PAUSED';
            this.dom.cascadeStateTag.className = 'cascade-state-tag';
        } else {
            this.dom.cascadeStateTag.innerText = 'RUNNING';
            this.dom.cascadeStateTag.className = 'cascade-state-tag running';
            this.dom.btnPlay.innerHTML = '<i class="fa-solid fa-pause"></i> Pause';
            this.dom.btnPlay.className = 'btn-sim play';
            this.dom.btnPlay.style.background = 'rgba(217, 119, 6, 0.7)';

            this.autoPlayInterval = setInterval(() => {
                const autoRecov = this.dom.toggleAutoRecov.checked;
                const active = this.engine.step(autoRecov, (id, state, msg, color, shock) => {
                    this._onNodeStateChange(id, state, msg, color, shock);
                });
                this.updateTelemetryHUD();

                if (!active && this.engine.recoveryQueue.size === 0) {
                    let failCount = 0;
                    this.engine.nodes.forEach(n => { if (n.state === STATUS.FAIL) failCount++; });
                    if (failCount === 0) {
                        this.toggleAutoPlay(); // Stop when stabilized
                    }
                }
            }, 1000);
        }
    }

    /** Reset simulation to baseline */
    resetSimulation() {
        if (this.autoPlayInterval) this.toggleAutoPlay();
        this.engine.reset((id, state) => {
            this.renderer.updateNodeVisual(id, this.engine);
        });
        this.metrics.reset();
        this.addLog('[T+0] Simulation graph reset to baseline.', 'log-cyan');
        this.updateTelemetryHUD();
        this.dom.btnPlay.style.background = '';
    }

    /** Inject a predefined scenario */
    injectScenario(type) {
        if (this.autoPlayInterval) this.toggleAutoPlay();
        this.engine.reset((id, state) => {
            this.renderer.updateNodeVisual(id, this.engine);
        });
        this.metrics.reset();

        const scenario = SCENARIOS[type];
        if (!scenario) return;

        scenario.failNodes.forEach(nodeId => {
            const msg = scenario.messages[nodeId] || null;
            this.engine.failNode(nodeId, msg, (id, state, logMsg, logColor, shock) => {
                this._onNodeStateChange(id, state, logMsg, logColor, shock);
            });
        });

        this.updateTelemetryHUD();
        this.toggleAutoPlay();
    }

    /** Manually fail the selected node */
    manualFailSelectedNode() {
        const nodeId = this.dom.nodeTargetSel.value;
        this.engine.failNode(nodeId, null, (id, state, msg, color, shock) => {
            this._onNodeStateChange(id, state, msg, color, shock);
        });
        this.updateTelemetryHUD();
        if (!this.autoPlayInterval) this.toggleAutoPlay();
    }

    /** Dynamically add a new node */
    dynamicAddNode() {
        const name = this.dom.dynNodeName.value.trim();
        const dept = this.dom.dynNodeDept.value;
        const parentId = this.dom.dynNodeParent.value;

        if (!name) return alert('Please enter a valid node name.');

        const newId = 'DYN_' + Date.now();
        const parentNode = this.engine.nodes.get(parentId);
        const newPos = [
            parentNode.pos[0] + (this.seedEngine.next() - 0.5) * 10,
            parentNode.pos[1],
            parentNode.pos[2] + (this.seedEngine.next() - 0.5) * 10
        ];

        this.engine.addNode({
            id: newId,
            name: name,
            dept: dept,
            pos: newPos,
            thresh: 0.65,
            desc: 'Dynamically injected node'
        });
        this.engine.addEdge(parentId, newId, 0.75);

        this.renderer.buildGraph(this.engine, this.seedEngine);
        this.populateDropdowns();
        this.addLog(`[DYNAMIC GRAPH] Injected new lifeline: "${name}" linked to ${parentNode.name}.`, 'log-cyan');
        this.dom.dynNodeName.value = '';
    }

    /** Apply a new seed */
    applySeed() {
        const newSeed = this.dom.seedInput.value.trim() || 'NAGPUR-SMART-2026';
        this.seedEngine.setSeed(newSeed);
        this.resetSimulation();
        this.addLog(`[SEED LOADED] Deterministic PRNG seeded with "${newSeed}". Exact reproducibility active.`, 'log-cyan');
    }

    /** Toggle live sensor data simulation */
    toggleLiveData() {
        const enabled = this.dom.toggleLiveData.checked;
        if (enabled) {
            this.liveDataInterval = setInterval(() => {
                if (!this.autoPlayInterval) {
                    this.engine.nodes.forEach(n => {
                        if (n.state === STATUS.OP) {
                            n.baselineNoise = (Math.random() * 0.15) - 0.05;
                            n.inStress = Math.max(0, n.baselineNoise);
                        }
                    });
                    if (this.selectedNodeId) this.inspectNode(this.selectedNodeId);
                }
            }, 1000);
        } else {
            clearInterval(this.liveDataInterval);
            this.engine.nodes.forEach(n => {
                n.baselineNoise = 0;
                if (n.state === STATUS.OP) n.inStress = 0;
            });
            if (this.selectedNodeId) this.inspectNode(this.selectedNodeId);
        }
    }

    /** Export simulation state as JSON download */
    exportSimulation() {
        const state = this.engine.exportState();
        const json = JSON.stringify(state, null, 2);
        const blob = new Blob([json], { type: 'application/json' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `cascade_sim_${state.seed}_T${state.tick}.json`;
        a.click();
        URL.revokeObjectURL(url);
        this.addLog(`[EXPORT] Simulation state exported as JSON (Tick: T+${state.tick}).`, 'log-green');
    }

    /** Export timestep log as CSV */
    exportCSV() {
        const events = this.engine.getEventLog();
        let csv = 'Tick,Node,Department,FromState,ToState,CascadeDepth,Event\n';
        events.forEach(evt => {
            csv += `${evt.tick},"${evt.nodeName}","${evt.dept}","${evt.fromState}","${evt.toState}",${evt.cascadeDepth || 0},"${evt.event}"\n`;
        });

        const blob = new Blob([csv], { type: 'text/csv' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `cascade_log_T${this.engine.tick}.csv`;
        a.click();
        URL.revokeObjectURL(url);
        this.addLog(`[EXPORT] Timestep log exported as CSV (${events.length} events).`, 'log-green');
    }
}
