/* =============================================================
   URBAN CASCADE SIMULATOR — APP.JS
   Main entry point: Initializes all modules and wires them together
   ============================================================= */

// ─── GLOBAL INSTANCES ──────────────────────────────────
let seedEngine, graphEngine, renderer3d, metricsTracker, uiController;

// ─── INITIALIZATION ────────────────────────────────────
function initApp() {
    // 1. Seed Engine
    seedEngine = new SeedEngine('NAGPUR-SMART-2026');
    window.seedEngine = seedEngine; // Expose for export

    // 2. Graph Engine
    graphEngine = new GraphEngine(INITIAL_NODES, INITIAL_EDGES);

    // 3. Metrics Tracker
    metricsTracker = new MetricsTracker();

    // 4. 3D Renderer
    renderer3d = new Renderer3D('canvas3d');
    renderer3d.buildGraph(graphEngine, seedEngine);

    // 5. UI Controller
    uiController = new UIController(graphEngine, renderer3d, metricsTracker, seedEngine);

    // 6. Wire renderer click → inspector
    renderer3d.onNodeClick = (nodeId) => {
        uiController.inspectNode(nodeId);
    };

    // 7. Initial telemetry update
    uiController.updateTelemetryHUD();

    // 8. Start render loop
    function animate() {
        requestAnimationFrame(animate);
        renderer3d.animate(graphEngine, seedEngine);
    }
    animate();

    // 9. Log initialization
    uiController.addLog('[T+0] System initialized. Deterministic Seed loaded: NAGPUR-SMART-2026.', 'log-dim');
    uiController.addLog(`[T+0] ${graphEngine.nodes.size} Heterogeneous Infrastructure Lifelines synchronized.`, 'log-green');
}

// ─── GLOBAL HANDLERS (called from HTML onclick) ────────
function injectScenario(type)      { uiController.injectScenario(type); }
function manualFailSelectedNode()  { uiController.manualFailSelectedNode(); }
function stepCascadeWave()         { uiController.stepCascadeWave(); }
function toggleAutoPlay()          { uiController.toggleAutoPlay(); }
function resetSimulation()         { uiController.resetSimulation(); }
function applySeed()               { uiController.applySeed(); }
function toggleLiveData()          { uiController.toggleLiveData(); }
function dynamicAddNode()          { uiController.dynamicAddNode(); }
function clearLogs()               { uiController.clearLogs(); }
function exportSimulation()        { uiController.exportSimulation(); }
function exportCSV()               { uiController.exportCSV(); }

// ─── BOOT ──────────────────────────────────────────────
window.addEventListener('DOMContentLoaded', initApp);
