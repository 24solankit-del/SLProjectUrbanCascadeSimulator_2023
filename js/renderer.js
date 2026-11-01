/* =============================================================
   URBAN CASCADE SIMULATOR — 3D RENDERER
   Three.js scene, camera, controls, node meshes, edge curves,
   data packet VFX, shockwave effects
   ============================================================= */

class Renderer3D {
    constructor(containerId) {
        this.container = document.getElementById(containerId);
        this.scene = null;
        this.camera = null;
        this.renderer = null;
        this.controls = null;

        this.nodeMeshes = new Map();  // nodeId -> {group, sphere, ring, sphereMat, ringMat, sprite}
        this.edgeLines = [];          // [{mesh, curve, material, u, v}]
        this.shockwaves = [];         // [{mesh, scale, opacity}]

        // Data packet particles
        this.packetPoints = null;
        this.packetData = [];
        this.PACKET_COUNT = 80;

        // Raycasting
        this.raycaster = new THREE.Raycaster();
        this.mouse = new THREE.Vector2();
        this.onNodeClick = null;      // Callback(nodeId)

        this._init();
    }

    /* ---------------------------------------------------------
       INITIALIZATION
       --------------------------------------------------------- */
    _init() {
        // Scene
        this.scene = new THREE.Scene();
        this.scene.fog = new THREE.FogExp2(0x030712, 0.015);

        // Camera
        this.camera = new THREE.PerspectiveCamera(
            45,
            window.innerWidth / window.innerHeight,
            0.1,
            1000
        );
        this.camera.position.set(0, 45, 60);

        // Renderer
        this.renderer = new THREE.WebGLRenderer({ antialias: true, alpha: false });
        this.renderer.setSize(window.innerWidth, window.innerHeight);
        this.renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
        this.renderer.toneMapping = THREE.ACESFilmicToneMapping;
        this.renderer.toneMappingExposure = 1.2;
        this.container.appendChild(this.renderer.domElement);

        // Orbit Controls
        this.controls = new THREE.OrbitControls(this.camera, this.renderer.domElement);
        this.controls.enableDamping = true;
        this.controls.dampingFactor = 0.05;
        this.controls.maxPolarAngle = Math.PI / 2.1;
        this.controls.minDistance = 15;
        this.controls.maxDistance = 120;
        this.controls.target.set(0, 0, 0);

        // Lighting
        const ambientLight = new THREE.AmbientLight(0xffffff, 0.4);
        this.scene.add(ambientLight);

        const dirLight = new THREE.DirectionalLight(0x00d2ff, 0.8);
        dirLight.position.set(30, 50, 20);
        this.scene.add(dirLight);

        // City grid floor
        this._buildCityGrid();

        // Raycaster click handler
        this.renderer.domElement.addEventListener('pointerdown', (e) => this._onPointerDown(e));

        // Window resize
        window.addEventListener('resize', () => this._onResize());
    }

    /* ---------------------------------------------------------
       CITY FLOOR GRID
       --------------------------------------------------------- */
    _buildCityGrid() {
        const gridHelper = new THREE.GridHelper(100, 50, 0x00d2ff, 0x112240);
        gridHelper.position.y = -0.5;
        this.scene.add(gridHelper);

        // Zero Mile Nagpur holographic marker
        const markerGeo = new THREE.RingGeometry(1.5, 2.0, 32);
        const markerMat = new THREE.MeshBasicMaterial({
            color: 0x00d2ff,
            side: THREE.DoubleSide,
            transparent: true,
            opacity: 0.6
        });
        const zeroMarker = new THREE.Mesh(markerGeo, markerMat);
        zeroMarker.rotation.x = -Math.PI / 2;
        zeroMarker.position.set(0, 0, 0);
        this.scene.add(zeroMarker);
    }

    /* ---------------------------------------------------------
       BUILD 3D GRAPH (Nodes + Edges)
       --------------------------------------------------------- */

    /**
     * Build or rebuild the full 3D graph from the engine state
     * @param {GraphEngine} engine
     * @param {SeedEngine} seedEngine
     */
    buildGraph(engine, seedEngine) {
        // Clear existing meshes
        this.nodeMeshes.forEach(m => this.scene.remove(m.group));
        this.nodeMeshes.clear();
        this.edgeLines.forEach(l => this.scene.remove(l.mesh));
        this.edgeLines = [];

        // ─── NODES ────────────────────────────────────────────
        engine.nodes.forEach(node => {
            const group = new THREE.Group();
            group.position.set(node.pos[0], node.pos[1], node.pos[2]);

            // Core sphere
            const sphereGeo = new THREE.SphereGeometry(1.4, 32, 32);
            const sphereMat = new THREE.MeshStandardMaterial({
                color: COLOR_MAP[node.state],
                emissive: COLOR_MAP[node.state],
                emissiveIntensity: 0.6,
                roughness: 0.2,
                metalness: 0.8
            });
            const sphere = new THREE.Mesh(sphereGeo, sphereMat);
            sphere.userData = { id: node.id };
            group.add(sphere);

            // Pulsing halo ring
            const ringGeo = new THREE.RingGeometry(1.8, 2.2, 32);
            const ringMat = new THREE.MeshBasicMaterial({
                color: COLOR_MAP[node.state],
                side: THREE.DoubleSide,
                transparent: true,
                opacity: 0.5
            });
            const ring = new THREE.Mesh(ringGeo, ringMat);
            ring.rotation.x = Math.PI / 2;
            group.add(ring);

            // Vertical pillar
            const pillarGeo = new THREE.CylinderGeometry(0.1, 0.1, node.pos[1] + 0.5, 16);
            const pillarMat = new THREE.MeshBasicMaterial({
                color: 0x00d2ff,
                transparent: true,
                opacity: 0.25
            });
            const pillar = new THREE.Mesh(pillarGeo, pillarMat);
            pillar.position.y = -(node.pos[1] + 0.5) / 2;
            group.add(pillar);

            // Text label sprite
            const sprite = this._createTextSprite(node.name);
            sprite.position.y = 2.4;
            group.add(sprite);

            this.scene.add(group);
            this.nodeMeshes.set(node.id, { group, sphere, ring, sphereMat, ringMat, sprite });
        });

        // ─── EDGES (Bezier Curves) ──────────────────────────
        engine.edges.forEach(edge => {
            const uNode = engine.nodes.get(edge.u);
            const vNode = engine.nodes.get(edge.v);
            if (!uNode || !vNode) return;

            const p1 = new THREE.Vector3(...uNode.pos);
            const p2 = new THREE.Vector3(...vNode.pos);
            const mid = new THREE.Vector3().addVectors(p1, p2).multiplyScalar(0.5);
            mid.y += p1.distanceTo(p2) * 0.2;

            const curve = new THREE.QuadraticBezierCurve3(p1, mid, p2);
            const points = curve.getPoints(30);
            const geometry = new THREE.BufferGeometry().setFromPoints(points);

            const material = new THREE.LineBasicMaterial({
                color: 0x00d2ff,
                transparent: true,
                opacity: 0.35 + edge.weight * 0.3,
                linewidth: 2
            });

            const line = new THREE.Line(geometry, material);
            this.scene.add(line);
            this.edgeLines.push({ mesh: line, curve, material, u: edge.u, v: edge.v });
        });

        // ─── PARTICLE VFX ───────────────────────────────────
        this._initParticleVFX(seedEngine);
    }

    /* ---------------------------------------------------------
       TEXT SPRITE CREATION
       --------------------------------------------------------- */
    _createTextSprite(text) {
        const canvas = document.createElement('canvas');
        canvas.width = 256;
        canvas.height = 64;
        const ctx = canvas.getContext('2d');

        ctx.fillStyle = 'rgba(11, 19, 43, 0.85)';
        ctx.roundRect(0, 0, 256, 64, 8);
        ctx.fill();
        ctx.strokeStyle = '#00d2ff';
        ctx.lineWidth = 2;
        ctx.stroke();

        ctx.fillStyle = '#ffffff';
        ctx.font = 'bold 20px Inter, sans-serif';
        ctx.textAlign = 'center';
        ctx.fillText(text, 128, 40);

        const texture = new THREE.CanvasTexture(canvas);
        const spriteMaterial = new THREE.SpriteMaterial({ map: texture, transparent: true });
        const sprite = new THREE.Sprite(spriteMaterial);
        sprite.scale.set(6, 1.5, 1);
        return sprite;
    }

    /* ---------------------------------------------------------
       NODE VISUAL UPDATES
       --------------------------------------------------------- */

    /** Update a single node's visual color/emissive based on its engine state */
    updateNodeVisual(nodeId, engine) {
        const node = engine.nodes.get(nodeId);
        const meshObj = this.nodeMeshes.get(nodeId);
        if (!node || !meshObj) return;

        const targetColor = COLOR_MAP[node.state];
        meshObj.sphereMat.color.setHex(targetColor);
        meshObj.sphereMat.emissive.setHex(targetColor);
        meshObj.ringMat.color.setHex(targetColor);

        meshObj.sphereMat.emissiveIntensity = (node.state === STATUS.FAIL) ? 1.2 : 0.6;
    }

    /** Update ALL node visuals (used after reset) */
    updateAllNodeVisuals(engine) {
        engine.nodes.forEach((node, id) => this.updateNodeVisual(id, engine));
    }

    /* ---------------------------------------------------------
       PARTICLE VFX (Data Packets flowing along edges)
       --------------------------------------------------------- */
    _initParticleVFX(seedEngine) {
        // Remove old particles
        if (this.packetPoints) {
            this.scene.remove(this.packetPoints);
        }
        this.packetData = [];

        if (this.edgeLines.length === 0) return;

        const geo = new THREE.BufferGeometry();
        const positions = new Float32Array(this.PACKET_COUNT * 3);
        const colors = new Float32Array(this.PACKET_COUNT * 3);

        for (let i = 0; i < this.PACKET_COUNT; i++) {
            const randomEdge = this.edgeLines[Math.floor(seedEngine.next() * this.edgeLines.length)];
            this.packetData.push({
                edge: randomEdge,
                t: seedEngine.next(),
                speed: 0.004 + seedEngine.next() * 0.006
            });
            positions[i * 3] = 0;
            positions[i * 3 + 1] = 0;
            positions[i * 3 + 2] = 0;
            colors[i * 3] = 0.0;
            colors[i * 3 + 1] = 0.8;
            colors[i * 3 + 2] = 1.0;
        }

        geo.setAttribute('position', new THREE.BufferAttribute(positions, 3));
        geo.setAttribute('color', new THREE.BufferAttribute(colors, 3));

        const mat = new THREE.PointsMaterial({
            size: 0.8,
            vertexColors: true,
            transparent: true,
            opacity: 0.9,
            blending: THREE.AdditiveBlending
        });

        this.packetPoints = new THREE.Points(geo, mat);
        this.scene.add(this.packetPoints);
    }

    /* ---------------------------------------------------------
       SHOCKWAVE VFX
       --------------------------------------------------------- */

    /** Create a red expanding shockwave ring at a node's position */
    createShockwave(pos) {
        const geo = new THREE.RingGeometry(0.5, 1.2, 32);
        const mat = new THREE.MeshBasicMaterial({
            color: 0xef4444,
            side: THREE.DoubleSide,
            transparent: true,
            opacity: 1.0
        });
        const ring = new THREE.Mesh(geo, mat);
        ring.position.set(pos[0], pos[1], pos[2]);
        ring.rotation.x = Math.PI / 2;
        this.scene.add(ring);
        this.shockwaves.push({ mesh: ring, scale: 1.0, opacity: 1.0 });
    }

    /* ---------------------------------------------------------
       RAYCASTING (Click to select node)
       --------------------------------------------------------- */
    _onPointerDown(event) {
        this.mouse.x = (event.clientX / window.innerWidth) * 2 - 1;
        this.mouse.y = -(event.clientY / window.innerHeight) * 2 + 1;
        this.raycaster.setFromCamera(this.mouse, this.camera);

        const spheres = Array.from(this.nodeMeshes.values()).map(m => m.sphere);
        const intersects = this.raycaster.intersectObjects(spheres);

        if (intersects.length > 0) {
            const hitNodeId = intersects[0].object.userData.id;
            if (this.onNodeClick) this.onNodeClick(hitNodeId);
        }
    }

    /* ---------------------------------------------------------
       RESIZE HANDLER
       --------------------------------------------------------- */
    _onResize() {
        this.camera.aspect = window.innerWidth / window.innerHeight;
        this.camera.updateProjectionMatrix();
        this.renderer.setSize(window.innerWidth, window.innerHeight);
    }

    /* ---------------------------------------------------------
       ANIMATION LOOP (called every frame)
       --------------------------------------------------------- */

    /**
     * Single frame update — call this from requestAnimationFrame
     * @param {GraphEngine} engine - For reading node states
     * @param {SeedEngine} seedEngine - For deterministic packet reassignment
     */
    animate(engine, seedEngine) {
        // Orbit controls
        this.controls.update();

        // Halo ring rotation
        this.nodeMeshes.forEach(meshObj => {
            meshObj.ring.rotation.z += 0.01;
        });

        // Data packet animation
        if (this.packetPoints && this.edgeLines.length > 0) {
            const positions = this.packetPoints.geometry.attributes.position.array;
            const colors = this.packetPoints.geometry.attributes.color.array;

            for (let i = 0; i < this.PACKET_COUNT; i++) {
                const p = this.packetData[i];
                if (!p || !p.edge) continue;

                p.t += p.speed;
                if (p.t > 1.0) {
                    p.t = 0.0;
                    p.edge = this.edgeLines[Math.floor(seedEngine.next() * this.edgeLines.length)];
                }

                if (p.edge && p.edge.curve) {
                    const pt = p.edge.curve.getPoint(p.t);
                    positions[i * 3] = pt.x;
                    positions[i * 3 + 1] = pt.y;
                    positions[i * 3 + 2] = pt.z;

                    // Color based on source node state
                    const sourceNode = engine.nodes.get(p.edge.u);
                    if (sourceNode && sourceNode.state === STATUS.FAIL) {
                        colors[i * 3] = 1.0; colors[i * 3 + 1] = 0.2; colors[i * 3 + 2] = 0.2;
                    } else if (sourceNode && sourceNode.state === STATUS.DEG) {
                        colors[i * 3] = 0.0; colors[i * 3 + 1] = 0.8; colors[i * 3 + 2] = 1.0;
                    } else {
                        colors[i * 3] = 0.1; colors[i * 3 + 1] = 0.9; colors[i * 3 + 2] = 0.5;
                    }
                }
            }
            this.packetPoints.geometry.attributes.position.needsUpdate = true;
            this.packetPoints.geometry.attributes.color.needsUpdate = true;
        }

        // Shockwave expansion
        for (let i = this.shockwaves.length - 1; i >= 0; i--) {
            const sw = this.shockwaves[i];
            sw.scale += 0.15;
            sw.opacity -= 0.02;
            sw.mesh.scale.set(sw.scale, sw.scale, sw.scale);
            sw.mesh.material.opacity = sw.opacity;

            if (sw.opacity <= 0) {
                this.scene.remove(sw.mesh);
                this.shockwaves.splice(i, 1);
            }
        }

        // Render
        this.renderer.render(this.scene, this.camera);
    }
}
