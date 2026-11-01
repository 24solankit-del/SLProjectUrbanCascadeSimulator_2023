/* =============================================================
   URBAN CASCADE SIMULATOR — METRICS TRACKER
   Records time-series data for cascade depth, affected count,
   recovery time at each tick. Provides data for charts.
   ============================================================= */

class MetricsTracker {
    constructor() {
        this.history = [];       // [{tick, cascadeDepth, affectedCount, recoveryTime, resilience, failCount}]
        this.maxDepthEver = 0;
        this.maxAffectedEver = 0;
        this.maxRecoveryEver = 0;
    }

    /**
     * Record a snapshot of current metrics at a given tick
     * @param {GraphEngine} engine - The graph engine to query
     */
    record(engine) {
        const depth = engine.getCascadeDepth();
        const affected = engine.getAffectedCount();
        const recovery = engine.getTotalRecoveryTime();
        const resilience = engine.getResilienceIndex();
        const counts = engine.getStatusCounts();

        this.maxDepthEver = Math.max(this.maxDepthEver, depth);
        this.maxAffectedEver = Math.max(this.maxAffectedEver, affected);
        this.maxRecoveryEver = Math.max(this.maxRecoveryEver, recovery);

        this.history.push({
            tick: engine.tick,
            cascadeDepth: depth,
            affectedCount: affected,
            recoveryTime: recovery,
            resilience: resilience,
            failCount: counts.fail,
            degCount: counts.deg,
            recCount: counts.rec,
            opCount: counts.op
        });
    }

    /** Get the latest metrics snapshot */
    getLatest() {
        if (this.history.length === 0) {
            return {
                tick: 0, cascadeDepth: 0, affectedCount: 0,
                recoveryTime: 0, resilience: 100, failCount: 0,
                degCount: 0, recCount: 0, opCount: 0
            };
        }
        return this.history[this.history.length - 1];
    }

    /** Get time series for chart rendering (last N ticks) */
    getTimeSeries(maxPoints = 30) {
        const start = Math.max(0, this.history.length - maxPoints);
        return this.history.slice(start);
    }

    /** Get cascade velocity (average nodes failing per tick) */
    getCascadeVelocity() {
        if (this.history.length < 2) return 0;
        const recent = this.history.slice(-5);
        let totalDelta = 0;
        for (let i = 1; i < recent.length; i++) {
            totalDelta += Math.max(0, recent[i].failCount - recent[i - 1].failCount);
        }
        return totalDelta / (recent.length - 1);
    }

    /** Reset all recorded history */
    reset() {
        this.history = [];
        this.maxDepthEver = 0;
        this.maxAffectedEver = 0;
        this.maxRecoveryEver = 0;
    }

    /**
     * Draw a mini sparkline chart on a canvas element
     * @param {HTMLCanvasElement} canvas
     * @param {string} dataKey - Which metric to chart ('affectedCount', 'cascadeDepth', 'resilience', etc.)
     * @param {string} color - CSS color string
     */
    drawSparkline(canvas, dataKey, color) {
        if (!canvas) return;
        const ctx = canvas.getContext('2d');
        const w = canvas.width;
        const h = canvas.height;

        ctx.clearRect(0, 0, w, h);

        const data = this.getTimeSeries(30);
        if (data.length < 2) return;

        const values = data.map(d => d[dataKey] || 0);
        const max = Math.max(...values, 1);

        // Draw fill gradient
        const gradient = ctx.createLinearGradient(0, 0, 0, h);
        gradient.addColorStop(0, color.replace(')', ', 0.3)').replace('rgb', 'rgba'));
        gradient.addColorStop(1, 'rgba(0, 0, 0, 0)');

        ctx.beginPath();
        ctx.moveTo(0, h);

        const stepX = w / (values.length - 1);

        for (let i = 0; i < values.length; i++) {
            const x = i * stepX;
            const y = h - (values[i] / max) * (h - 4);
            if (i === 0) ctx.moveTo(x, y);
            else ctx.lineTo(x, y);
        }

        // Close path for fill
        ctx.lineTo(w, h);
        ctx.lineTo(0, h);
        ctx.fillStyle = gradient;
        ctx.fill();

        // Draw line on top
        ctx.beginPath();
        for (let i = 0; i < values.length; i++) {
            const x = i * stepX;
            const y = h - (values[i] / max) * (h - 4);
            if (i === 0) ctx.moveTo(x, y);
            else ctx.lineTo(x, y);
        }
        ctx.strokeStyle = color;
        ctx.lineWidth = 1.5;
        ctx.stroke();

        // Draw endpoint dot
        if (values.length > 0) {
            const lastX = (values.length - 1) * stepX;
            const lastY = h - (values[values.length - 1] / max) * (h - 4);
            ctx.beginPath();
            ctx.arc(lastX, lastY, 2.5, 0, Math.PI * 2);
            ctx.fillStyle = color;
            ctx.fill();
        }
    }

    /**
     * Draw the cascade progression chart on a larger canvas
     * Shows affected count, fail count, and resilience over time
     * @param {HTMLCanvasElement} canvas
     */
    drawProgressionChart(canvas) {
        if (!canvas) return;
        const ctx = canvas.getContext('2d');
        const w = canvas.width;
        const h = canvas.height;
        const padding = { top: 5, right: 5, bottom: 15, left: 25 };
        const chartW = w - padding.left - padding.right;
        const chartH = h - padding.top - padding.bottom;

        ctx.clearRect(0, 0, w, h);

        const data = this.getTimeSeries(40);
        if (data.length < 2) {
            ctx.fillStyle = 'rgba(107, 114, 128, 0.4)';
            ctx.font = '10px Inter, sans-serif';
            ctx.textAlign = 'center';
            ctx.fillText('Waiting for simulation data...', w / 2, h / 2);
            return;
        }

        const totalNodes = data[0].opCount + data[0].degCount + data[0].recCount + data[0].failCount;
        const maxVal = Math.max(totalNodes, 1);
        const stepX = chartW / (data.length - 1);

        // Draw grid lines
        ctx.strokeStyle = 'rgba(55, 65, 81, 0.3)';
        ctx.lineWidth = 0.5;
        for (let i = 0; i <= 4; i++) {
            const y = padding.top + (chartH / 4) * i;
            ctx.beginPath();
            ctx.moveTo(padding.left, y);
            ctx.lineTo(w - padding.right, y);
            ctx.stroke();
        }

        // Y-axis labels
        ctx.fillStyle = 'rgba(107, 114, 128, 0.6)';
        ctx.font = '8px JetBrains Mono, monospace';
        ctx.textAlign = 'right';
        for (let i = 0; i <= 4; i++) {
            const y = padding.top + (chartH / 4) * i;
            const val = Math.round(maxVal - (maxVal / 4) * i);
            ctx.fillText(val.toString(), padding.left - 4, y + 3);
        }

        // X-axis tick labels
        ctx.textAlign = 'center';
        const xLabelEvery = Math.max(1, Math.floor(data.length / 6));
        data.forEach((d, i) => {
            if (i % xLabelEvery === 0 || i === data.length - 1) {
                const x = padding.left + i * stepX;
                ctx.fillText(`T${d.tick}`, x, h - 2);
            }
        });

        // Helper: draw area chart line
        const drawArea = (key, strokeColor, fillColor) => {
            const values = data.map(d => d[key] || 0);

            // Fill
            ctx.beginPath();
            ctx.moveTo(padding.left, padding.top + chartH);
            values.forEach((v, i) => {
                const x = padding.left + i * stepX;
                const y = padding.top + chartH - (v / maxVal) * chartH;
                ctx.lineTo(x, y);
            });
            ctx.lineTo(padding.left + (values.length - 1) * stepX, padding.top + chartH);
            ctx.closePath();
            ctx.fillStyle = fillColor;
            ctx.fill();

            // Stroke
            ctx.beginPath();
            values.forEach((v, i) => {
                const x = padding.left + i * stepX;
                const y = padding.top + chartH - (v / maxVal) * chartH;
                if (i === 0) ctx.moveTo(x, y);
                else ctx.lineTo(x, y);
            });
            ctx.strokeStyle = strokeColor;
            ctx.lineWidth = 1.5;
            ctx.stroke();
        };

        // Draw layers (back to front)
        drawArea('affectedCount', 'rgba(239, 68, 68, 0.8)', 'rgba(239, 68, 68, 0.12)');
        drawArea('failCount', 'rgba(239, 68, 68, 1)', 'rgba(239, 68, 68, 0.2)');
        drawArea('degCount', 'rgba(0, 210, 255, 0.8)', 'rgba(0, 210, 255, 0.1)');
        drawArea('recCount', 'rgba(250, 204, 21, 0.8)', 'rgba(250, 204, 21, 0.1)');
    }
}
