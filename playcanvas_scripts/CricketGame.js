/**
 * CricketGame.js
 * AAA 3D Cricket Simulation, Hawk-Eye Visuals, Spatial Audio & Interactive Gameplay.
 * 
 * Features:
 * - Full 3D Stadium with pitch wear states (Day 1 Green, Day 3 Flat, Day 5 Dusty).
 * - Hawk-Eye 3D Ballistic Trajectory Tracers & Pitch Landing Impact Crater.
 * - Procedural Web Audio API sound triggers (willow crack, turf thud, stumps smash, crowd).
 * - Interactive 3D Drag-and-Drop: Click and drag any fielder with real-time sync.
 * - Animated Batter swing, Bowler release, and real-time Fielder chase/dive paths.
 * - Cinematic cameras with Hawk-Eye Slow-Motion Replay mode.
 */

var CricketGame = pc.createScript('cricketGame');

CricketGame.prototype.initialize = function () {
    this.serverUrl = 'ws://' + (window.location.hostname || 'localhost') + ':8765';
    this.ws = null;
    this.isConnected = false;

    // Entity maps
    this.fielderEntities = {};
    this.targetPositions = {};
    this.reactionRings = {};

    // Drag-and-drop state
    this.selectedFielder = null;
    this.isDragging = false;
    this.hoveredFielder = null;

    // Simulation & Replay state
    this.isSimulating = false;
    this.isReplay = false;
    this.simSpeedMultiplier = 1.0;
    this.simPhase = 'idle'; // 'delivery', 'shot', 'idle'
    this.simTime = 0.0;
    this.activeDeliveryTraj = [];
    this.activeShotTraj = [];
    this.activeFielderRuns = {};
    this.activeResult = null;
    this.lastResultData = null;

    // Build 3D stadium components
    this._createStadium();
    this._createPitch();
    this._createStumps();
    this._createPlayersAtCrease();
    this._createBall();
    this._createHawkEyeTracer();

    // Setup input listeners for 3D Drag and Drop
    this._initInput();

    // Connect to backend game engine
    this._connect();
};

// ─────────────────────────────────────────────────────────────────────────────
// 3D STADIUM & GROUND ENVIRONMENT
// ─────────────────────────────────────────────────────────────────────────────
CricketGame.prototype._createStadium = function () {
    // 1. Boundary Rope with Advertising Cushions (R = 68.0m)
    var ropeSegments = 120;
    var ropeRadius = 68.0;
    for (var i = 0; i < ropeSegments; i += 2) {
        var a1 = (i / ropeSegments) * Math.PI * 2;
        var a2 = ((i + 1) / ropeSegments) * Math.PI * 2;
        var mx = Math.sin((a1 + a2) * 0.5) * ropeRadius;
        var mz = Math.cos((a1 + a2) * 0.5) * ropeRadius;

        var cushion = new pc.Entity("BoundaryCushion_" + i);
        cushion.addComponent('model', { type: 'box' });
        cushion.setLocalScale(3.5, 0.35, 0.6);
        cushion.setPosition(mx, 0.15, mz);
        cushion.setEulerAngles(0, ((a1 + a2) * 0.5) * (180 / Math.PI) + 90, 0);

        var ropeMat = new pc.StandardMaterial();
        ropeMat.diffuse = (i % 4 === 0) ? new pc.Color(0.85, 0.15, 0.15) : new pc.Color(0.95, 0.95, 0.95);
        ropeMat.gloss = 0.4;
        ropeMat.update();
        cushion.model.material = ropeMat;
        this.app.root.addChild(cushion);
    }

    // 2. 30-Yard Infield White Circle (R = 27.43m)
    var circleEntity = new pc.Entity("InfieldCircle_30Yard");
    circleEntity.addComponent('model', { type: 'cylinder' });
    circleEntity.setLocalScale(54.86, 0.02, 54.86);
    circleEntity.setPosition(0, 0.01, 10.06);

    var circleMat = new pc.StandardMaterial();
    circleMat.diffuse = new pc.Color(1.0, 1.0, 1.0);
    circleMat.emissive = new pc.Color(0.6, 0.8, 1.0);
    circleMat.opacity = 0.15;
    circleMat.blendType = pc.BLEND_NORMAL;
    circleMat.depthWrite = false;
    circleMat.update();
    circleEntity.model.material = circleMat;
    this.app.root.addChild(circleEntity);
};

CricketGame.prototype._createPitch = function () {
    // Standard cricket pitch strip: 20.12m x 3.2m
    this.pitchEntity = new pc.Entity("Pitch_Strip");
    this.pitchEntity.addComponent('model', { type: 'box' });
    this.pitchEntity.setLocalScale(3.2, 0.02, 22.0);
    this.pitchEntity.setPosition(0, 0.015, 10.06);

    this.pitchMat = new pc.StandardMaterial();
    this.pitchMat.diffuse = new pc.Color(0.72, 0.64, 0.48); // Day 3 Flat Clay
    this.pitchMat.gloss = 0.2;
    this.pitchMat.update();
    this.pitchEntity.model.material = this.pitchMat;
    this.app.root.addChild(this.pitchEntity);

    // Crease Markings (White chalk)
    var makeChalk = function(x, z, sx, sz) {
        var line = new pc.Entity("ChalkLine");
        line.addComponent('model', { type: 'box' });
        line.setLocalScale(sx, 0.025, sz);
        line.setPosition(x, 0.026, z);
        var chalkMat = new pc.StandardMaterial();
        chalkMat.diffuse = new pc.Color(0.96, 0.96, 0.96);
        chalkMat.emissive = new pc.Color(0.25, 0.25, 0.25);
        chalkMat.update();
        line.model.material = chalkMat;
        return line;
    };

    this.app.root.addChild(makeChalk(0, 1.22, 3.66, 0.10));
    this.app.root.addChild(makeChalk(0, 0.0, 2.64, 0.08));
    this.app.root.addChild(makeChalk(0, 18.9, 3.66, 0.10));
    this.app.root.addChild(makeChalk(0, 20.12, 2.64, 0.08));

    // Pitch Landing Impact Crater
    this.pitchCrater = new pc.Entity("PitchImpactCrater");
    this.pitchCrater.addComponent('model', { type: 'cylinder' });
    this.pitchCrater.setLocalScale(0.45, 0.028, 0.45);
    this.pitchCrater.setPosition(0, 0.028, 6.8);
    var craterMat = new pc.StandardMaterial();
    craterMat.diffuse = new pc.Color(0.9, 0.2, 0.2);
    craterMat.emissive = new pc.Color(0.8, 0.1, 0.1);
    craterMat.opacity = 0.6;
    craterMat.blendType = pc.BLEND_ADDITIVE;
    craterMat.update();
    this.pitchCrater.model.material = craterMat;
    this.pitchCrater.enabled = false;
    this.app.root.addChild(this.pitchCrater);
};

CricketGame.prototype.updatePitchCondition = function (cond) {
    if (!this.pitchMat) return;
    if (cond === "day_1_green") {
        this.pitchMat.diffuse = new pc.Color(0.42, 0.58, 0.35); // Emerald seam grass
    } else if (cond === "day_5_dusty") {
        this.pitchMat.diffuse = new pc.Color(0.65, 0.52, 0.36); // Dusty dry cracks
    } else {
        this.pitchMat.diffuse = new pc.Color(0.72, 0.64, 0.48); // Day 3 flat
    }
    this.pitchMat.update();
};

CricketGame.prototype._createStumps = function () {
    var woodMat = new pc.StandardMaterial();
    woodMat.diffuse = new pc.Color(0.85, 0.68, 0.40);
    woodMat.gloss = 0.5;
    woodMat.update();

    var buildWicket = function (zPos, parent) {
        var stumpSpacing = 0.11;
        for (var i = -1; i <= 1; i++) {
            var stump = new pc.Entity("Stump_" + i);
            stump.addComponent('model', { type: 'cylinder' });
            stump.setLocalScale(0.045, 0.71, 0.045);
            stump.setPosition(i * stumpSpacing, 0.355, zPos);
            stump.model.material = woodMat;
            parent.addChild(stump);
        }
        var bails = new pc.Entity("Bails");
        bails.addComponent('model', { type: 'box' });
        bails.setLocalScale(0.24, 0.025, 0.03);
        bails.setPosition(0, 0.725, zPos);
        bails.model.material = woodMat;
        parent.addChild(bails);
    };

    this.batterWicket = new pc.Entity("BatterWicket");
    this.app.root.addChild(this.batterWicket);
    buildWicket(0.0, this.batterWicket);

    this.bowlerWicket = new pc.Entity("BowlerWicket");
    this.app.root.addChild(this.bowlerWicket);
    buildWicket(20.12, this.bowlerWicket);
};

CricketGame.prototype._createPlayersAtCrease = function () {
    // Batsman
    this.batterEntity = new pc.Entity("Batsman");
    this._buildHumanoidMesh(this.batterEntity, "batter", new pc.Color(0.2, 0.5, 0.9));
    this.batterEntity.setPosition(0.25, 0.0, 0.8);
    this.batterEntity.setEulerAngles(0, -90, 0);
    this.app.root.addChild(this.batterEntity);

    // Cricket Bat
    this.batEntity = new pc.Entity("CricketBat");
    this.batEntity.addComponent('model', { type: 'box' });
    this.batEntity.setLocalScale(0.12, 0.85, 0.04);
    this.batEntity.setPosition(0.25, 0.45, 0.4);
    this.batEntity.setEulerAngles(20, -90, 0);
    var batMat = new pc.StandardMaterial();
    batMat.diffuse = new pc.Color(0.75, 0.58, 0.35);
    batMat.gloss = 0.4;
    batMat.update();
    this.batEntity.model.material = batMat;
    this.batterEntity.addChild(this.batEntity);

    // Bowler
    this.bowlerEntity = new pc.Entity("ActiveBowler");
    this._buildHumanoidMesh(this.bowlerEntity, "bowler", new pc.Color(0.9, 0.2, 0.2));
    this.bowlerEntity.setPosition(0.5, 0.0, 20.2);
    this.bowlerEntity.setEulerAngles(0, 180, 0);
    this.app.root.addChild(this.bowlerEntity);
};

CricketGame.prototype._createBall = function () {
    this.ball = new pc.Entity("CricketBall");
    this.ball.addComponent('model', { type: 'sphere' });
    this.ball.setLocalScale(0.22, 0.22, 0.22);
    this.ball.setPosition(0.5, 2.2, 20.0);

    var ballMat = new pc.StandardMaterial();
    ballMat.diffuse = new pc.Color(0.95, 0.15, 0.15);
    ballMat.emissive = new pc.Color(0.35, 0.05, 0.05);
    ballMat.gloss = 0.8;
    ballMat.update();
    this.ball.model.material = ballMat;
    this.ball.enabled = false;
    this.app.root.addChild(this.ball);

    // Hit Flash Sparkle
    this.flashEntity = new pc.Entity("HitFlash");
    this.flashEntity.addComponent('model', { type: 'sphere' });
    this.flashEntity.setLocalScale(0.85, 0.85, 0.85);
    this.flashEntity.setPosition(0, 0.6, 0);
    var flashMat = new pc.StandardMaterial();
    flashMat.diffuse = new pc.Color(1, 1, 0.4);
    flashMat.emissive = new pc.Color(1, 1, 0.8);
    flashMat.opacity = 0.75;
    flashMat.blendType = pc.BLEND_ADDITIVE;
    flashMat.update();
    this.flashEntity.model.material = flashMat;
    this.flashEntity.enabled = false;
    this.app.root.addChild(this.flashEntity);
};

CricketGame.prototype._createHawkEyeTracer = function () {
    // Hawk-Eye Ballistic Line Nodes
    this.tracerPoints = [];
    this.tracerParent = new pc.Entity("HawkEyeTracers");
    this.app.root.addChild(this.tracerParent);

    var glowMat = new pc.StandardMaterial();
    glowMat.diffuse = new pc.Color(0.2, 0.8, 1.0);
    glowMat.emissive = new pc.Color(0.3, 0.9, 1.0);
    glowMat.opacity = 0.55;
    glowMat.blendType = pc.BLEND_ADDITIVE;
    glowMat.update();
    this.tracerMat = glowMat;
};

CricketGame.prototype._renderHawkEyeTracer = function (trajectory, color) {
    if (!this.tracerParent) return;
    while (this.tracerParent.children.length > 0) {
        this.tracerParent.children[0].destroy();
    }
    if (!trajectory || trajectory.length < 2) return;

    var step = Math.max(1, Math.floor(trajectory.length / 45));
    for (var i = 0; i < trajectory.length - step; i += step) {
        var p1 = trajectory[i];
        var p2 = trajectory[i + step];
        var v1 = new pc.Vec3(p1.x, p1.y, p1.z);
        var v2 = new pc.Vec3(p2.x, p2.y, p2.z);
        var dist = v1.distance(v2);
        if (dist < 0.02) continue;

        var seg = new pc.Entity("TracerNode_" + i);
        seg.addComponent('model', { type: 'cylinder' });
        seg.setLocalScale(0.06, dist, 0.06);

        var mid = new pc.Vec3().add2(v1, v2).scale(0.5);
        seg.setPosition(mid);

        seg.lookAt(v2);
        seg.rotateLocal(90, 0, 0);

        var segMat = new pc.StandardMaterial();
        segMat.diffuse = color;
        segMat.emissive = color;
        segMat.opacity = 0.7;
        segMat.blendType = pc.BLEND_ADDITIVE;
        segMat.depthWrite = false;
        segMat.update();
        seg.model.material = segMat;

        this.tracerParent.addChild(seg);
    }
};

// ─────────────────────────────────────────────────────────────────────────────
// HUMANOID PLAYER MESH BUILDER
// ─────────────────────────────────────────────────────────────────────────────
CricketGame.prototype._buildHumanoidMesh = function (parent, role, kitColor) {
    var kitMat = new pc.StandardMaterial();
    kitMat.diffuse = kitColor;
    kitMat.gloss = 0.3;
    kitMat.update();

    var whiteMat = new pc.StandardMaterial();
    whiteMat.diffuse = new pc.Color(0.94, 0.94, 0.94);
    whiteMat.update();

    var skinMat = new pc.StandardMaterial();
    skinMat.diffuse = new pc.Color(0.82, 0.63, 0.45);
    skinMat.update();

    var darkMat = new pc.StandardMaterial();
    darkMat.diffuse = new pc.Color(0.12, 0.12, 0.14);
    darkMat.update();

    var addBox = function (name, sx, sy, sz, ox, oy, oz, mat) {
        var b = new pc.Entity(name);
        b.addComponent('model', { type: 'box' });
        b.setLocalScale(sx, sy, sz);
        b.setLocalPosition(ox, oy, oz);
        b.model.material = mat;
        parent.addChild(b);
        return b;
    };

    // Legs with batting/fielding pads
    addBox("LegL", 0.22, 0.75, 0.22, -0.13, 0.50, 0, whiteMat);
    addBox("LegR", 0.22, 0.75, 0.22,  0.13, 0.50, 0, whiteMat);
    addBox("ShoeL", 0.22, 0.14, 0.38, -0.13, 0.07, 0.06, darkMat);
    addBox("ShoeR", 0.22, 0.14, 0.38,  0.13, 0.07, 0.06, darkMat);
    // Torso / Jersey
    addBox("Torso", 0.54, 0.64, 0.30, 0, 1.20, 0, kitMat);
    // Arms
    addBox("ArmL", 0.18, 0.65, 0.18, -0.38, 1.15, 0, kitMat);
    addBox("ArmR", 0.18, 0.65, 0.18,  0.38, 1.15, 0, kitMat);
    // Head / Cap
    var head = new pc.Entity("Head");
    head.addComponent('model', { type: 'sphere' });
    head.setLocalScale(0.36, 0.36, 0.36);
    head.setLocalPosition(0, 1.68, 0);
    head.model.material = skinMat;
    parent.addChild(head);

    var cap = new pc.Entity("Cap");
    cap.addComponent('model', { type: 'box' });
    cap.setLocalScale(0.38, 0.10, 0.44);
    cap.setLocalPosition(0, 1.84, 0.04);
    cap.model.material = kitMat;
    parent.addChild(cap);
};

// ─────────────────────────────────────────────────────────────────────────────
// 3D DRAG-AND-DROP FIELDER INTERACTION (MOUSE & TOUCH)
// ─────────────────────────────────────────────────────────────────────────────
CricketGame.prototype._initInput = function () {
    var self = this;
    var canvas = document.getElementById('application-canvas');

    var getGroundCoords = function (screenX, screenY) {
        var cam = self.app.root.findByName("MainCamera");
        if (!cam || !cam.camera) return null;
        var from = cam.camera.screenToWorld(screenX, screenY, cam.camera.nearClip);
        var to = cam.camera.screenToWorld(screenX, screenY, cam.camera.farClip);
        var dy = to.y - from.y;
        if (Math.abs(dy) < 1e-5) return null;
        var t = -from.y / dy;
        if (t <= 0) return null;
        return {
            x: from.x + t * (to.x - from.x),
            z: from.z + t * (to.z - from.z)
        };
    };

    var findNearestFielder = function (gx, gz, maxDist) {
        var bestName = null;
        var bestDist = maxDist || 4.5;
        for (var name in self.fielderEntities) {
            var ent = self.fielderEntities[name];
            var p = ent.getPosition();
            var d = Math.sqrt((p.x - gx) * (p.x - gx) + (p.z - gz) * (p.z - gz));
            if (d < bestDist) {
                bestDist = d;
                bestName = name;
            }
        }
        return bestName;
    };

    window.addEventListener('mousedown', function (e) {
        if (e.target.tagName !== 'CANVAS') return;
        var pt = getGroundCoords(e.clientX, e.clientY);
        if (!pt) return;

        var targetFielder = findNearestFielder(pt.x, pt.z, 3.8);
        if (targetFielder) {
            self.selectedFielder = targetFielder;
            self.isDragging = true;
            e.stopImmediatePropagation();
            self._highlightFielder(targetFielder, true);
        }
    }, true);

    window.addEventListener('mousemove', function (e) {
        var pt = getGroundCoords(e.clientX, e.clientY);
        if (!pt) return;

        if (self.isDragging && self.selectedFielder) {
            e.stopImmediatePropagation();
            var dist = Math.sqrt(pt.x * pt.x + pt.z * pt.z);
            if (dist > 67.0) {
                var s = 67.0 / dist;
                pt.x *= s;
                pt.z *= s;
            }
            var ent = self.fielderEntities[self.selectedFielder];
            if (ent) {
                ent.setPosition(pt.x, 0.05, pt.z);
            }
        } else {
            var hovered = findNearestFielder(pt.x, pt.z, 3.5);
            if (hovered !== self.hoveredFielder) {
                if (self.hoveredFielder && self.hoveredFielder !== self.selectedFielder) {
                    self._highlightFielder(self.hoveredFielder, false);
                }
                self.hoveredFielder = hovered;
                if (hovered) {
                    self._highlightFielder(hovered, true);
                    canvas.style.cursor = 'grab';
                } else {
                    canvas.style.cursor = 'default';
                }
            }
        }
    }, true);

    window.addEventListener('mouseup', function (e) {
        if (self.isDragging && self.selectedFielder) {
            e.stopImmediatePropagation();
            var ent = self.fielderEntities[self.selectedFielder];
            if (ent) {
                var pos = ent.getPosition();
                ent.setPosition(pos.x, 0.0, pos.z);
                self._send({
                    action: "update_fielder",
                    name: self.selectedFielder,
                    x: pos.x,
                    z: pos.z
                });
            }
            self._highlightFielder(self.selectedFielder, false);
            self.selectedFielder = null;
            self.isDragging = false;
            canvas.style.cursor = 'default';
        }
    }, true);
};

CricketGame.prototype._highlightFielder = function (name, active) {
    var ring = this.reactionRings[name];
    if (ring) {
        ring.enabled = active;
    }
};

// ─────────────────────────────────────────────────────────────────────────────
// WEBSOCKET GAME ENGINE CLIENT
// ─────────────────────────────────────────────────────────────────────────────
CricketGame.prototype._connect = function () {
    var self = this;
    try {
        this.ws = new WebSocket(this.serverUrl);
        this.ws.onopen = function () {
            self.isConnected = true;
            console.log("[CricketGame] Connected to Game Physics Server");
            self.app.fire('cricket:connected', true);
            self._send({ action: "get_state" });
        };
        this.ws.onmessage = function (e) {
            self._handleServerMessage(e.data);
        };
        this.ws.onclose = function () {
            self.isConnected = false;
            self.app.fire('cricket:connected', false);
            setTimeout(function () { self._connect(); }, 2000);
        };
    } catch (e) {
        setTimeout(function () { self._connect(); }, 2000);
    }
};

CricketGame.prototype._send = function (obj) {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
        this.ws.send(JSON.stringify(obj));
    }
};

CricketGame.prototype._handleServerMessage = function (raw) {
    try {
        var msg = JSON.parse(raw);
        var act = msg.action;

        if (act === "state_sync") {
            this._syncFielders(msg.state.fielders);
            if (msg.state.pitch_condition) {
                this.updatePitchCondition(msg.state.pitch_condition);
            }
            this.app.fire('cricket:stateUpdated', msg.state);
        } else if (act === "fielder_moved") {
            this.targetPositions[msg.name] = new pc.Vec3(msg.x, 0.0, msg.z);
        } else if (act === "delivery_result") {
            this._startDeliverySimulation(msg.data, 1.0);
        } else if (act === "bowling_config_updated") {
            this.app.fire('cricket:bowlingConfigUpdated', msg.config);
        } else if (act === "pitch_condition_updated") {
            this.updatePitchCondition(msg.condition);
        } else if (act === "match_analytics_report") {
            this.app.fire('cricket:analyticsReport', msg.analytics);
        }
    } catch (err) {
        console.error("Failed to parse message:", err);
    }
};

CricketGame.prototype._syncFielders = function (fielders) {
    for (var name in fielders) {
        var p = fielders[name];
        var vec = new pc.Vec3(p.x, 0.0, p.z);
        this.targetPositions[name] = vec;

        if (!this.fielderEntities[name]) {
            this._spawnFielder(name, vec);
        }
    }

    for (var existing in this.fielderEntities) {
        var isActive = !!fielders[existing];
        this.fielderEntities[existing].enabled = isActive;
    }
};

CricketGame.prototype._spawnFielder = function (name, pos) {
    var isKeeper = (name === "WicketKeeper");
    var isSlip = (name.indexOf("Slip") !== -1 || name === "Gully");

    var kitColor = isKeeper ? new pc.Color(0.95, 0.75, 0.1) :
                   isSlip ? new pc.Color(0.15, 0.45, 0.85) :
                   new pc.Color(0.2, 0.55, 0.95);

    var fielder = new pc.Entity(name);
    this._buildHumanoidMesh(fielder, "fielder", kitColor);
    fielder.setPosition(pos.x, 0.0, pos.z);
    this.app.root.addChild(fielder);
    this.fielderEntities[name] = fielder;

    var ring = new pc.Entity(name + "_Ring");
    ring.addComponent('model', { type: 'cylinder' });
    ring.setLocalScale(6.0, 0.02, 6.0);
    ring.setLocalPosition(0, 0.01, 0);
    var ringMat = new pc.StandardMaterial();
    ringMat.diffuse = new pc.Color(0.2, 0.8, 1.0);
    ringMat.emissive = new pc.Color(0.1, 0.5, 0.9);
    ringMat.opacity = 0.35;
    ringMat.blendType = pc.BLEND_ADDITIVE;
    ringMat.update();
    ring.model.material = ringMat;
    ring.enabled = false;
    fielder.addChild(ring);
    this.reactionRings[name] = ring;
};

// ─────────────────────────────────────────────────────────────────────────────
// DELIVERY SIMULATION PLAYBACK & AUDIO TRIGGERS
// ─────────────────────────────────────────────────────────────────────────────
CricketGame.prototype._startDeliverySimulation = function (data, speedMult) {
    this.lastResultData = data;
    this.activeResult = data;
    this.simSpeedMultiplier = speedMult || 1.0;
    this.isReplay = (speedMult !== 1.0);

    this.activeDeliveryTraj = data.delivery.trajectory || [];
    this.activeShotTraj = data.shot.trajectory || [];
    this.activeFielderRuns = data.pursuit.fielder_runs || {};

    this._resetFielderPoses();

    // Show pitch landing impact crater
    if (data.delivery.pitch_point) {
        var pp = data.delivery.pitch_point;
        this.pitchCrater.setPosition(pp.x, 0.028, pp.z);
        this.pitchCrater.enabled = true;
    }

    // Render Hawk-Eye Trajectory Tracer
    var fullTraj = this.activeDeliveryTraj.concat(this.activeShotTraj);
    this._renderHawkEyeTracer(fullTraj, new pc.Color(0.2, 0.85, 1.0));

    this.simPhase = 'delivery';
    this.simTime = 0.0;
    this.isSimulating = true;
    this.ball.enabled = true;
    this.flashEntity.enabled = false;

    this.batterEntity.setEulerAngles(0, -90, 0);

    this.app.fire('cricket:simStarted', data);
};

CricketGame.prototype.replayLastBall = function () {
    if (this.lastResultData && !this.isSimulating) {
        this._startDeliverySimulation(this.lastResultData, 0.45); // 0.45x Slow Motion Replay
    }
};

CricketGame.prototype.update = function (dt) {
    if (!this.isSimulating) {
        for (var name in this.fielderEntities) {
            if (this.isDragging && this.selectedFielder === name) continue;
            var target = this.targetPositions[name];
            var ent = this.fielderEntities[name];
            if (target && ent) {
                var cur = ent.getPosition();
                cur.lerp(cur, target, dt * 8.0);
                ent.setPosition(cur.x, 0.0, cur.z);
                ent.lookAt(new pc.Vec3(0, 0, 0));
                ent.setEulerAngles(0, ent.getEulerAngles().y + 180, 0);
            }
        }
    }

    if (this.isSimulating) {
        this.simTime += dt * this.simSpeedMultiplier;

        if (this.simPhase === 'delivery') {
            var dTraj = this.activeDeliveryTraj;
            if (dTraj.length > 0) {
                var sample = this._sampleTraj(dTraj, this.simTime);
                this.ball.setPosition(sample.x, sample.y, sample.z);

                // Audio trigger: Pitch Bounce
                if (sample.z <= 7.2 && sample.z >= 6.4 && !this._bouncedAudio) {
                    this._bouncedAudio = true;
                    this.app.fire('cricket:audio:bounce');
                }

                if (sample.z > 15.0) {
                    this.bowlerEntity.setPosition(sample.x, 0.0, sample.z + 0.8);
                }

                if (sample.z <= 0.2 || this.simTime >= dTraj[dTraj.length - 1].t) {
                    this.simPhase = 'shot';
                    this.simTime = 0.0;
                    this._bouncedAudio = false;
                    this._playBatStrike();
                }
            }
        } else if (this.simPhase === 'shot') {
            var sTraj = this.activeShotTraj;
            if (sTraj.length > 0) {
                var sSample = this._sampleTraj(sTraj, this.simTime);
                this.ball.setPosition(sSample.x, sSample.y, sSample.z);

                // Fielder pursuit animation with procedural athletic sprint kinematics
                var isCatch = this.activeResult && this.activeResult.pursuit &&
                              this.activeResult.pursuit.outcome === "WICKET_CAUGHT";
                var catchingFielder = isCatch ? this.activeResult.pursuit.fielder_name : null;
                var totalShotTime = (sTraj.length > 0) ? sTraj[sTraj.length - 1].t : 1.0;

                for (var fName in this.activeFielderRuns) {
                    var waypoints = this.activeFielderRuns[fName];
                    var fEnt = this.fielderEntities[fName];
                    if (fEnt && waypoints.length > 0) {
                        var fSample = this._sampleFielderRun(waypoints, this.simTime);
                        fEnt.setPosition(fSample.x, 0.0, fSample.z);
                        fEnt.lookAt(new pc.Vec3(sSample.x, 0.0, sSample.z));
                        fEnt.setEulerAngles(0, fEnt.getEulerAngles().y + 180, 0);

                        var legL = fEnt.findByName("LegL");
                        var legR = fEnt.findByName("LegR");
                        var armL = fEnt.findByName("ArmL");
                        var armR = fEnt.findByName("ArmR");
                        var torso = fEnt.findByName("Torso");

                        // If this is the catching fielder at the moment of catch, dive / catch pose
                        if (fName === catchingFielder && this.simTime >= totalShotTime - 0.35) {
                            if (torso) torso.setLocalEulerAngles(35, 0, 0);
                            if (armL) armL.setLocalEulerAngles(-55, -20, 0);
                            if (armR) armR.setLocalEulerAngles(-55, 20, 0);
                            if (legL) legL.setLocalEulerAngles(-20, 0, 0);
                            if (legR) legR.setLocalEulerAngles(35, 0, 0);
                        } else {
                            // Active running sprint oscillation
                            var swing = Math.sin(this.simTime * 18.0) * 32.0;
                            if (legL) legL.setLocalEulerAngles(swing, 0, 0);
                            if (legR) legR.setLocalEulerAngles(-swing, 0, 0);
                            if (armL) armL.setLocalEulerAngles(-swing * 1.15, 0, 0);
                            if (armR) armR.setLocalEulerAngles(swing * 1.15, 0, 0);
                            if (torso) torso.setLocalEulerAngles(8, 0, 0); // athletic forward sprint lean
                        }
                    }
                }

                if (this.simTime >= sTraj[sTraj.length - 1].t + 0.6) {
                    this.isSimulating = false;
                    this.simPhase = 'idle';
                    this._resetFielderPoses();
                    this._playOutcomeCelebrationAudio();
                    this.app.fire('cricket:simCompleted', this.activeResult);
                }
            } else {
                this.isSimulating = false;
                this.simPhase = 'idle';
                this._resetFielderPoses();
                this._playOutcomeCelebrationAudio();
                this.app.fire('cricket:simCompleted', this.activeResult);
            }
        }
    }
};

CricketGame.prototype._playBatStrike = function () {
    var self = this;
    var shot = this.activeResult.shot;
    var exitSpeed = shot ? shot.exit_velocity_kmh : 110;

    if (shot && shot.shot_type === "bowled") {
        this.app.fire('cricket:audio:bowled');
        // Tilt stumps
        if (this.batterWicket) this.batterWicket.setEulerAngles(25, 0, 10);
    } else {
        this.app.fire('cricket:audio:bat', exitSpeed);
        this.batterEntity.setEulerAngles(0, -35, 0); // swing follow-through
        this.flashEntity.setPosition(this.ball.getPosition());
        this.flashEntity.enabled = true;
        setTimeout(function () {
            self.flashEntity.enabled = false;
        }, 120);
    }
};

CricketGame.prototype._playOutcomeCelebrationAudio = function () {
    if (!this.activeResult || !this.activeResult.pursuit) return;
    var outcome = this.activeResult.pursuit.outcome;

    if (outcome === "WICKET_BOWLED" || outcome === "WICKET_CAUGHT") {
        this.app.fire('cricket:audio:cheer');
    } else if (outcome === "FOUR" || outcome === "SIX") {
        this.app.fire('cricket:audio:cheer');
    } else if (this.activeResult.shot.shot_type === "edge") {
        this.app.fire('cricket:audio:gasp');
    }
};

CricketGame.prototype._resetFielderPoses = function () {
    for (var fName in this.fielderEntities) {
        var ent = this.fielderEntities[fName];
        if (!ent) continue;
        var legL = ent.findByName("LegL");
        var legR = ent.findByName("LegR");
        var armL = ent.findByName("ArmL");
        var armR = ent.findByName("ArmR");
        var torso = ent.findByName("Torso");
        if (legL) legL.setLocalEulerAngles(0, 0, 0);
        if (legR) legR.setLocalEulerAngles(0, 0, 0);
        if (armL) armL.setLocalEulerAngles(0, 0, 0);
        if (armR) armR.setLocalEulerAngles(0, 0, 0);
        if (torso) torso.setLocalEulerAngles(0, 0, 0);
    }
};

CricketGame.prototype._sampleTraj = function (traj, t) {
    if (t <= traj[0].t) return traj[0];
    if (t >= traj[traj.length - 1].t) return traj[traj.length - 1];

    for (var i = 0; i < traj.length - 1; i++) {
        if (t >= traj[i].t && t <= traj[i + 1].t) {
            var frac = (t - traj[i].t) / (traj[i + 1].t - traj[i].t);
            return {
                x: traj[i].x + (traj[i + 1].x - traj[i].x) * frac,
                y: traj[i].y + (traj[i + 1].y - traj[i].y) * frac,
                z: traj[i].z + (traj[i + 1].z - traj[i].z) * frac
            };
        }
    }
    return traj[traj.length - 1];
};

CricketGame.prototype._sampleFielderRun = function (waypoints, t) {
    if (t <= waypoints[0].t) return waypoints[0];
    if (t >= waypoints[waypoints.length - 1].t) return waypoints[waypoints.length - 1];

    for (var i = 0; i < waypoints.length - 1; i++) {
        if (t >= waypoints[i].t && t <= waypoints[i + 1].t) {
            var frac = (t - waypoints[i].t) / (waypoints[i + 1].t - waypoints[i].t);
            return {
                x: waypoints[i].x + (waypoints[i + 1].x - waypoints[i].x) * frac,
                z: waypoints[i].z + (waypoints[i + 1].z - waypoints[i].z) * frac
            };
        }
    }
    return waypoints[waypoints.length - 1];
};

// ─────────────────────────────────────────────────────────────────────────────
// PUBLIC ACTIONS EXPOSED TO HUD
// ─────────────────────────────────────────────────────────────────────────────
CricketGame.prototype.bowlBall = function () {
    if (this.isSimulating) return;
    this._send({ action: "bowl_delivery" });
};

CricketGame.prototype.setPreset = function (presetName) {
    this._send({ action: "set_preset", preset: presetName });
};

CricketGame.prototype.setBowlingConfig = function (cfg) {
    this._send({ action: "set_bowling_config", config: cfg });
};

CricketGame.prototype.setHandedness = function (hand) {
    this._send({ action: "set_handedness", handedness: hand });
};

CricketGame.prototype.setPitchCondition = function (cond) {
    this._send({ action: "set_pitch_condition", condition: cond });
};

CricketGame.prototype.startAcademyLevel = function (levelId) {
    this._send({ action: "start_academy_level", level_id: levelId });
};

CricketGame.prototype.setGameMode = function (mode) {
    this._send({ action: "set_game_mode", mode: mode });
};

CricketGame.prototype.requestMatchAnalytics = function () {
    this._send({ action: "get_match_analytics" });
};

CricketGame.prototype.resetMatch = function () {
    if (this.pitchCrater) this.pitchCrater.enabled = false;
    if (this.batterWicket) this.batterWicket.setEulerAngles(0, 0, 0);
    this._resetFielderPoses();
    this._send({ action: "reset_match" });
};
