/**
 * GameHUD.js
 * Comprehensive AAA Cricket Simulation HUD.
 * Features:
 * - Dual Gameplay Modes: Free Play Sandbox & Captain's Academy Career Mode.
 * - Junior Mode vs Pro Mode Neuroscience Explainer Toggle.
 * - Pitch Condition Selector (Day 1 Green, Day 3 Flat, Day 5 Dusty).
 * - Slow-Motion Hawk-Eye Replay Trigger.
 * - Pro Analytics Suite (Wagon Wheel, Pitch Map, Expected Runs Prevented xRP).
 * - Audio Mute/Unmute toggle.
 */

var GameHUD = pc.createScript('gameHUD');

GameHUD.prototype.initialize = function () {
    this.gameScript = null;
    this.currentHand = 'RHB';
    this.personaMode = 'junior'; // 'junior' or 'pro'
    this.gameMode = 'free_play'; // 'free_play' or 'academy'
    this.pitchCondition = 'day_3_flat';
    this.isMuted = false;

    this.bowlingConfig = {
        bowling_type: 'fast',
        speed_kmh: 142.0,
        line: 'outside_off',
        length: 'good_length',
        variation: 'outswing'
    };

    this._injectStyles();
    this._buildUI();

    var self = this;
    setTimeout(function () {
        var mgr = self.app.root.findByName("AnalyticsManager") || self.app.root.findByName("GameManager");
        if (mgr && mgr.script && mgr.script.cricketGame) {
            self.gameScript = mgr.script.cricketGame;
        }
    }, 100);

    // Event listeners
    this.app.on('cricket:stateUpdated', this._onStateUpdated, this);
    this.app.on('cricket:connected', this._onConnected, this);
    this.app.on('cricket:simStarted', this._onSimStarted, this);
    this.app.on('cricket:simCompleted', this._onSimCompleted, this);
    this.app.on('cricket:analyticsReport', this._onAnalyticsReport, this);
};

GameHUD.prototype._injectStyles = function () {
    if (document.getElementById('cricket-game-styles')) return;
    var css = `
        .c-root {
            position: absolute; inset: 0; pointer-events: none;
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            color: #fff; z-index: 100;
        }
        .c-interactive { pointer-events: auto; }

        /* Top Bar Scoreboard */
        .c-topbar {
            position: absolute; top: 12px; left: 16px; right: 16px;
            display: flex; justify-content: space-between; align-items: center;
        }
        .c-score-card {
            background: rgba(10, 18, 34, 0.94);
            backdrop-filter: blur(14px);
            border: 1px solid rgba(255,255,255,0.15);
            border-radius: 14px; padding: 8px 16px;
            display: flex; align-items: center; gap: 16px;
            box-shadow: 0 8px 30px rgba(0,0,0,0.5);
        }
        .c-score-title { font-size: 13px; font-weight: 800; color: #60a5fa; letter-spacing: 0.8px; text-transform: uppercase; }
        .c-stat-group { display: flex; align-items: baseline; gap: 4px; }
        .c-stat-val { font-size: 18px; font-weight: 800; color: #fff; }
        .c-stat-lbl { font-size: 10px; color: #94a3b8; text-transform: uppercase; }

        .c-btn {
            background: rgba(15, 23, 42, 0.9);
            border: 1px solid rgba(255,255,255,0.15);
            color: #cbd5e1; border-radius: 18px; padding: 6px 14px;
            font-size: 11px; font-weight: 700; cursor: pointer; transition: all .15s;
        }
        .c-btn:hover { background: rgba(30, 41, 59, 0.95); color: #fff; border-color: rgba(255,255,255,0.3); }
        .c-btn.active { background: #2563eb; color: #fff; border-color: #60a5fa; box-shadow: 0 0 10px rgba(37,99,235,0.5); }
        .c-btn.gold { background: linear-gradient(135deg, #f59e0b, #d97706); color: #fff; border-color: #fbbf24; }

        /* Top Right Control Cluster */
        .c-cam-bar {
            position: absolute; top: 68px; right: 16px;
            display: flex; gap: 6px;
        }
        .c-cam-btn {
            background: rgba(10, 18, 34, 0.85); backdrop-filter: blur(10px);
            border: 1px solid rgba(255,255,255,0.12); color: #94a3b8;
            border-radius: 12px; padding: 5px 11px; font-size: 10px; font-weight: 700;
            cursor: pointer; transition: all .15s;
        }
        .c-cam-btn.active, .c-cam-btn:hover { color: #fff; border-color: #38bdf8; background: rgba(14, 165, 233, 0.25); }

        /* Drag Tip Banner */
        .c-drag-tip {
            position: absolute; top: 72px; left: 16px;
            background: rgba(10, 18, 34, 0.85); backdrop-filter: blur(10px);
            border: 1px solid rgba(56, 189, 248, 0.3); border-radius: 10px;
            padding: 6px 14px; font-size: 11px; font-weight: 600; color: #38bdf8;
            box-shadow: 0 4px 16px rgba(0,0,0,0.3);
        }

        /* Bottom Bowling Controller Deck */
        .c-deck {
            position: absolute; bottom: 16px; left: 50%; transform: translateX(-50%);
            width: min(940px, calc(100vw - 32px));
            background: rgba(10, 18, 34, 0.94);
            backdrop-filter: blur(20px);
            border: 1px solid rgba(255,255,255,0.14);
            border-radius: 18px;
            padding: 12px 18px;
            box-shadow: 0 16px 48px rgba(0,0,0,0.65);
            display: flex; flex-direction: column; gap: 10px;
        }
        .c-deck-row {
            display: flex; align-items: center; justify-content: space-between; gap: 12px; flex-wrap: wrap;
        }
        .c-section-label { font-size: 9px; font-weight: 800; color: #64748b; letter-spacing: 0.8px; text-transform: uppercase; margin-bottom: 3px; }

        .c-pills { display: flex; gap: 6px; align-items: center; flex-wrap: wrap; }
        .c-pill {
            background: rgba(255,255,255,0.06); border: 1px solid rgba(255,255,255,0.12);
            color: #cbd5e1; border-radius: 8px; padding: 5px 11px;
            font-size: 11px; font-weight: 600; cursor: pointer; transition: all .15s;
        }
        .c-pill:hover { background: rgba(255,255,255,0.12); color: #fff; }
        .c-pill.active { background: linear-gradient(135deg, #2563eb, #38bdf8); color: #fff; border-color: #60a5fa; }

        /* Speed Slider */
        .c-speed-box { display: flex; align-items: center; gap: 10px; min-width: 200px; }
        .c-speed-slider { flex: 1; accent-color: #38bdf8; cursor: pointer; height: 6px; }
        .c-speed-val { font-size: 13px; font-weight: 800; color: #38bdf8; min-width: 60px; text-align: right; }

        /* Glowing Bowl Delivery Button */
        .c-bowl-btn {
            background: linear-gradient(135deg, #ef4444, #f97316);
            border: none; border-radius: 12px;
            color: #fff; font-size: 14px; font-weight: 900; letter-spacing: 0.8px;
            padding: 10px 22px; cursor: pointer; transition: all .2s;
            box-shadow: 0 0 20px rgba(239, 68, 68, 0.5);
            display: flex; align-items: center; gap: 8px;
        }
        .c-bowl-btn:hover { transform: scale(1.03); box-shadow: 0 0 28px rgba(249, 115, 22, 0.7); }
        .c-bowl-btn:disabled { opacity: 0.5; cursor: not-allowed; transform: none; box-shadow: none; }

        /* Big Outcome Celebration Banner */
        .c-outcome-banner {
            position: absolute; top: 38%; left: 50%; transform: translate(-50%, -50%) scale(0.8);
            background: rgba(10, 18, 34, 0.95);
            border: 2px solid #38bdf8; border-radius: 20px;
            padding: 16px 36px; text-align: center;
            box-shadow: 0 20px 60px rgba(0,0,0,0.8), 0 0 40px rgba(56, 189, 248, 0.4);
            opacity: 0; pointer-events: none; transition: all .35s cubic-bezier(0.175, 0.885, 0.32, 1.275);
            z-index: 150;
        }
        .c-outcome-banner.show { opacity: 1; transform: translate(-50%, -50%) scale(1.0); }
        .c-outcome-title { font-size: 26px; font-weight: 900; letter-spacing: 1px; color: #fff; }
        .c-outcome-sub { font-size: 13px; color: #94a3b8; margin-top: 4px; font-weight: 600; }

        /* Tactical & Neuroscience Coaching Card */
        .c-coach-card {
            position: absolute; bottom: 144px; left: 16px; width: 360px;
            background: rgba(10, 18, 34, 0.95); backdrop-filter: blur(16px);
            border: 1px solid rgba(56, 189, 248, 0.3); border-radius: 14px;
            padding: 12px 16px; box-shadow: 0 12px 40px rgba(0,0,0,0.6);
            display: none; animation: slideUp .3s ease;
        }
        @keyframes slideUp { from { opacity:0; transform:translateY(15px); } to { opacity:1; transform:translateY(0); } }
        .c-coach-header { display: flex; justify-content: space-between; align-items: center; }
        .c-coach-title { font-size: 13px; font-weight: 800; color: #38bdf8; }
        .c-coach-toggle { font-size: 10px; color: #fbbf24; cursor: pointer; text-decoration: underline; }
        .c-coach-lesson { font-size: 11px; color: #e2e8f0; line-height: 1.5; margin: 8px 0; }
        .c-coach-tip { font-size: 10px; color: #fbbf24; background: rgba(245, 158, 11, 0.12); padding: 5px 8px; border-radius: 6px; }

        /* Modal Overlays (Academy & Analytics) */
        .c-modal-overlay {
            position: absolute; inset: 0; background: rgba(0,0,0,0.7); backdrop-filter: blur(6px);
            display: none; justify-content: center; align-items: center; z-index: 200;
        }
        .c-modal-card {
            background: rgba(15, 23, 42, 0.96); border: 1px solid rgba(255,255,255,0.18);
            border-radius: 20px; padding: 24px 28px; width: min(650px, 90vw); max-height: 85vh;
            overflow-y: auto; box-shadow: 0 24px 64px rgba(0,0,0,0.8);
        }
        .c-modal-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px; }
        .c-modal-title { font-size: 18px; font-weight: 800; color: #60a5fa; }
        .c-modal-close { cursor: pointer; color: #94a3b8; font-size: 18px; font-weight: 700; }
        .c-level-card {
            background: rgba(255,255,255,0.04); border: 1px solid rgba(255,255,255,0.1);
            border-radius: 12px; padding: 12px 16px; margin-bottom: 10px;
            display: flex; justify-content: space-between; align-items: center;
        }
        .c-level-card.active { border-color: #38bdf8; background: rgba(56, 189, 248, 0.1); }
    `;
    var style = document.createElement('style');
    style.id = 'cricket-game-styles';
    style.textContent = css;
    document.head.appendChild(style);
};

GameHUD.prototype._buildUI = function () {
    var self = this;
    var root = document.createElement('div');
    root.className = 'c-root';
    document.body.appendChild(root);

    root.innerHTML = `
        <!-- Top Scoreboard Bar -->
        <div class="c-topbar c-interactive">
            <div class="c-score-card">
                <div class="c-score-title" id="hud-game-mode-lbl">🏏 Free Play</div>
                <div class="c-stat-group">
                    <span class="c-stat-val" id="hud-overs">0.0</span>
                    <span class="c-stat-lbl">Overs</span>
                </div>
                <div class="c-stat-group">
                    <span class="c-stat-val" id="hud-score">0 / 0</span>
                    <span class="c-stat-lbl">Runs / Wkts</span>
                </div>
                <div class="c-stat-group">
                    <span class="c-stat-val" id="hud-speed">--</span>
                    <span class="c-stat-lbl">km/h</span>
                </div>
                <div class="c-stat-group">
                    <span class="c-stat-val" id="hud-xrp" style="color:#22c55e;">+0.0</span>
                    <span class="c-stat-lbl">xRP</span>
                </div>
            </div>

            <div style="display:flex;gap:8px;align-items:center;">
                <button class="c-btn gold" id="btn-academy">🎓 Academy Mode</button>
                <button class="c-btn" id="btn-analytics">📊 Match Analytics</button>
                <button class="c-btn" id="btn-replay">⏪ Replay (0.45x)</button>
                <button class="c-btn" id="btn-hand">🏏 RHB</button>
                <button class="c-btn" id="btn-audio">🔊 Sound</button>
                <div class="c-pill" id="hud-status" style="font-size:10px;">🟢 Live</div>
            </div>
        </div>

        <!-- Camera Angles & Pitch Selector -->
        <div class="c-cam-bar c-interactive">
            <button class="c-cam-btn active" data-cam="broadcast">🦅 Broadcast View</button>
            <button class="c-cam-btn" data-cam="bowler">🎳 Bowler Cam</button>
            <button class="c-cam-btn" data-cam="batsman">🏏 Batter Cam</button>
        </div>

        <!-- Fielder Drag Tip -->
        <div class="c-drag-tip">
            ✋ Click & drag any fielder on the turf to set your custom field!
        </div>

        <!-- Big Celebration / Wicket Banner -->
        <div class="c-outcome-banner" id="outcome-banner">
            <div class="c-outcome-title" id="outcome-title">FOUR!</div>
            <div class="c-outcome-sub" id="outcome-sub">Pierces the off-side gap!</div>
        </div>

        <!-- Tactical & Neuroscience Coaching Card -->
        <div class="c-coach-card c-interactive" id="coach-card">
            <div class="c-coach-header">
                <div class="c-coach-title" id="coach-title">🧠 Cognitive Lesson</div>
                <div class="c-coach-toggle" id="coach-persona-toggle">Switch to Pro Mode</div>
            </div>
            <div class="c-coach-lesson" id="coach-lesson"></div>
            <div class="c-coach-tip" id="coach-tip"></div>
        </div>

        <!-- Bottom Bowling & Fielding Controller Deck -->
        <div class="c-deck c-interactive">
            <!-- Row 1: Presets & Pitch Condition -->
            <div class="c-deck-row">
                <div>
                    <div class="c-section-label">Fielding Presets</div>
                    <div class="c-pills" id="preset-pills">
                        <button class="c-pill active" data-preset="Powerplay Attack (Slips + Gully)">Slips Attack</button>
                        <button class="c-pill" data-preset="T20 Death Yorker Lock (5 on Boundary)">Death Yorker Lock</button>
                        <button class="c-pill" data-preset="Spin Trap (Close Catchers + Boundary Traps)">Spin Trap</button>
                        <button class="c-pill" data-preset="Balanced One-Day Ring">Balanced Ring</button>
                    </div>
                </div>

                <div>
                    <div class="c-section-label">Pitch Condition</div>
                    <div class="c-pills" id="pitch-pills">
                        <button class="c-pill" data-pitch="day_1_green">🌿 Day 1 Green</button>
                        <button class="c-pill active" data-pitch="day_3_flat">🏏 Day 3 Flat</button>
                        <button class="c-pill" data-pitch="day_5_dusty">🏜️ Day 5 Dusty</button>
                    </div>
                </div>

                <div>
                    <div class="c-section-label">Bowling Style</div>
                    <div class="c-pills" id="style-pills">
                        <button class="c-pill active" data-style="fast">⚡ Fast</button>
                        <button class="c-pill" data-style="medium_pace">🔵 Swing</button>
                        <button class="c-pill" data-style="off_spin">🔄 Off Spin</button>
                        <button class="c-pill" data-style="leg_spin">🌀 Leg Spin</button>
                    </div>
                </div>
            </div>

            <!-- Row 2: Speed Slider & Line & Length & Action -->
            <div class="c-deck-row">
                <div class="c-speed-box">
                    <span style="font-size:11px;font-weight:700;">Speed</span>
                    <input type="range" class="c-speed-slider" id="speed-slider" min="70" max="155" value="142" />
                    <span class="c-speed-val" id="speed-val">142 km/h</span>
                </div>

                <div>
                    <div class="c-section-label">Line</div>
                    <div class="c-pills" id="line-pills">
                        <button class="c-pill active" data-line="outside_off">Outside Off</button>
                        <button class="c-pill" data-line="off_stump">Off Stump</button>
                        <button class="c-pill" data-line="middle_stump">Middle</button>
                        <button class="c-pill" data-line="leg_stump">Leg Stump</button>
                    </div>
                </div>

                <div>
                    <div class="c-section-label">Length</div>
                    <div class="c-pills" id="length-pills">
                        <button class="c-pill" data-length="yorker">Yorker</button>
                        <button class="c-pill" data-length="full">Full</button>
                        <button class="c-pill active" data-length="good_length">Good Length</button>
                        <button class="c-pill" data-length="bouncer">Bouncer</button>
                    </div>
                </div>

                <!-- BOWL BALL ACTION -->
                <button class="c-bowl-btn" id="btn-bowl">
                    ⚡ BOWL BALL!
                </button>
            </div>
        </div>

        <!-- Captain's Academy Modal -->
        <div class="c-modal-overlay c-interactive" id="academy-modal">
            <div class="c-modal-card">
                <div class="c-modal-header">
                    <div class="c-modal-title">🎓 Captain's Academy Progression</div>
                    <div class="c-modal-close" id="academy-close">✕</div>
                </div>
                <div id="academy-level-list"></div>
            </div>
        </div>

        <!-- Match Analytics Suite Modal -->
        <div class="c-modal-overlay c-interactive" id="analytics-modal">
            <div class="c-modal-card">
                <div class="c-modal-header">
                    <div class="c-modal-title">📊 Match Analytics & Hawk-Eye Suite</div>
                    <div class="c-modal-close" id="analytics-close">✕</div>
                </div>
                <div id="analytics-content"></div>
            </div>
        </div>
    `;

    // ── Wire Controls ────────────────────────────────────────────────────────
    // 1. Handedness
    var handBtn = document.getElementById('btn-hand');
    handBtn.addEventListener('click', function () {
        self.currentHand = (self.currentHand === 'RHB') ? 'LHB' : 'RHB';
        handBtn.textContent = '🏏 ' + self.currentHand;
        if (self.gameScript) self.gameScript.setHandedness(self.currentHand);
    });

    // 2. Audio Toggle
    var audioBtn = document.getElementById('btn-audio');
    audioBtn.addEventListener('click', function () {
        self.isMuted = !self.isMuted;
        audioBtn.textContent = self.isMuted ? '🔇 Muted' : '🔊 Sound';
        self.app.fire('cricket:audio:mute', self.isMuted);
        var audioScript = self.app.root.findByName("GameManager")?.script?.cricketAudio;
        if (audioScript) audioScript.isMuted = self.isMuted;
    });

    // 3. Slow-Motion Replay
    document.getElementById('btn-replay').addEventListener('click', function () {
        if (self.gameScript) self.gameScript.replayLastBall();
    });

    // 4. Academy Modal
    document.getElementById('btn-academy').addEventListener('click', function () {
        document.getElementById('academy-modal').style.display = 'flex';
    });
    document.getElementById('academy-close').addEventListener('click', function () {
        document.getElementById('academy-modal').style.display = 'none';
    });

    // 5. Match Analytics Modal
    document.getElementById('btn-analytics').addEventListener('click', function () {
        if (self.gameScript) self.gameScript.requestMatchAnalytics();
        document.getElementById('analytics-modal').style.display = 'flex';
    });
    document.getElementById('analytics-close').addEventListener('click', function () {
        document.getElementById('analytics-modal').style.display = 'none';
    });

    // 6. Persona Toggle
    var personaBtn = document.getElementById('coach-persona-toggle');
    personaBtn.addEventListener('click', function () {
        self.personaMode = (self.personaMode === 'junior') ? 'pro' : 'junior';
        personaBtn.textContent = (self.personaMode === 'junior') ? 'Switch to Pro Mode' : 'Switch to Junior Mode';
        self._updateCoachCardContent();
    });

    // 7. Pitch Condition
    root.querySelectorAll('#pitch-pills .c-pill').forEach(function (b) {
        b.addEventListener('click', function () {
            root.querySelectorAll('#pitch-pills .c-pill').forEach(function (x) { x.classList.remove('active'); });
            b.classList.add('active');
            var cond = b.getAttribute('data-pitch');
            self.pitchCondition = cond;
            if (self.gameScript) self.gameScript.setPitchCondition(cond);
        });
    });

    // 8. Preset selection
    root.querySelectorAll('#preset-pills .c-pill').forEach(function (b) {
        b.addEventListener('click', function () {
            root.querySelectorAll('#preset-pills .c-pill').forEach(function (x) { x.classList.remove('active'); });
            b.classList.add('active');
            if (self.gameScript) self.gameScript.setPreset(b.getAttribute('data-preset'));
        });
    });

    // 9. Bowling Style
    root.querySelectorAll('#style-pills .c-pill').forEach(function (b) {
        b.addEventListener('click', function () {
            root.querySelectorAll('#style-pills .c-pill').forEach(function (x) { x.classList.remove('active'); });
            b.classList.add('active');
            var style = b.getAttribute('data-style');
            self.bowlingConfig.bowling_type = style;
            if (style === 'fast') {
                self.bowlingConfig.speed_kmh = 142;
                self.bowlingConfig.variation = 'outswing';
            } else if (style === 'medium_pace') {
                self.bowlingConfig.speed_kmh = 125;
                self.bowlingConfig.variation = 'inswing';
            } else if (style === 'off_spin') {
                self.bowlingConfig.speed_kmh = 86;
                self.bowlingConfig.variation = 'standard';
            } else if (style === 'leg_spin') {
                self.bowlingConfig.speed_kmh = 82;
                self.bowlingConfig.variation = 'standard';
            }
            document.getElementById('speed-slider').value = self.bowlingConfig.speed_kmh;
            document.getElementById('speed-val').textContent = self.bowlingConfig.speed_kmh + ' km/h';
            self._syncBowlingConfig();
        });
    });

    // 10. Speed Slider
    var slider = document.getElementById('speed-slider');
    slider.addEventListener('input', function () {
        self.bowlingConfig.speed_kmh = parseFloat(slider.value);
        document.getElementById('speed-val').textContent = slider.value + ' km/h';
        self._syncBowlingConfig();
    });

    // 11. Line
    root.querySelectorAll('#line-pills .c-pill').forEach(function (b) {
        b.addEventListener('click', function () {
            root.querySelectorAll('#line-pills .c-pill').forEach(function (x) { x.classList.remove('active'); });
            b.classList.add('active');
            self.bowlingConfig.line = b.getAttribute('data-line');
            self._syncBowlingConfig();
        });
    });

    // 12. Length
    root.querySelectorAll('#length-pills .c-pill').forEach(function (b) {
        b.addEventListener('click', function () {
            root.querySelectorAll('#length-pills .c-pill').forEach(function (x) { x.classList.remove('active'); });
            b.classList.add('active');
            self.bowlingConfig.length = b.getAttribute('data-length');
            self._syncBowlingConfig();
        });
    });

    // 13. BOWL BALL
    var bowlBtn = document.getElementById('btn-bowl');
    bowlBtn.addEventListener('click', function () {
        if (self.gameScript) self.gameScript.bowlBall();
    });

    // 14. Camera buttons
    root.querySelectorAll('.c-cam-btn').forEach(function (b) {
        b.addEventListener('click', function () {
            root.querySelectorAll('.c-cam-btn').forEach(function (x) { x.classList.remove('active'); });
            b.classList.add('active');
            self.app.fire('cricket:cameraPreset', b.getAttribute('data-cam'));
        });
    });
};

GameHUD.prototype._syncBowlingConfig = function () {
    if (this.gameScript) {
        this.gameScript.setBowlingConfig(this.bowlingConfig);
    }
};

GameHUD.prototype._onStateUpdated = function (state) {
    if (!state) return;
    if (state.scoreboard) {
        document.getElementById('hud-overs').textContent = state.scoreboard.overs || '0.0';
        document.getElementById('hud-score').textContent =
            (state.scoreboard.runs_conceded || 0) + ' / ' + (state.scoreboard.wickets_taken || 0);
        var xrpEl = document.getElementById('hud-xrp');
        var xrpVal = state.scoreboard.total_xrp || 0.0;
        xrpEl.textContent = (xrpVal >= 0 ? '+' : '') + xrpVal.toFixed(1);
        xrpEl.style.color = (xrpVal >= 0 ? '#22c55e' : '#f87171');
    }

    if (state.game_mode) {
        document.getElementById('hud-game-mode-lbl').textContent =
            (state.game_mode === 'academy') ? '🎓 Academy' : '🏏 Free Play';
    }

    // Populate Academy Level List
    if (state.academy_levels) {
        var listEl = document.getElementById('academy-level-list');
        var html = '';
        var curLvlId = state.academy_level ? state.academy_level.id : 'level_1';
        var storedCompleted = [];
        try {
            storedCompleted = JSON.parse(localStorage.getItem('cricket_completed_levels') || '[]');
        } catch (e) {}

        state.academy_levels.forEach(function (lvl) {
            var isCur = (lvl.id === curLvlId);
            var isDone = storedCompleted.indexOf(lvl.id) !== -1;
            html += `
                <div class="c-level-card ${isCur ? 'active' : ''}">
                    <div>
                        <div style="font-size:13px;font-weight:700;color:#fff;">
                            ${lvl.title} ${isDone ? '<span style="color:#fbbf24;font-size:11px;margin-left:6px;">⭐ MASTERED</span>' : ''}
                        </div>
                        <div style="font-size:11px;color:#94a3b8;margin-top:2px;">${lvl.objective}</div>
                        <div style="font-size:10px;color:#fbbf24;margin-top:4px;">💡 ${lvl.hint}</div>
                    </div>
                    <button class="c-btn ${isCur ? 'active' : ''}" onclick="window.app.fire('cricket:startLevel', '${lvl.id}')">
                        ${isCur ? 'Active' : (isDone ? 'Replay' : 'Play')}
                    </button>
                </div>
            `;
        });
        listEl.innerHTML = html;
    }
};

GameHUD.prototype._onConnected = function (connected) {
    var s = document.getElementById('hud-status');
    if (s) {
        s.textContent = connected ? '🟢 Live' : '🔴 Reconnecting…';
    }
};

GameHUD.prototype._onSimStarted = function (data) {
    var bowlBtn = document.getElementById('btn-bowl');
    if (bowlBtn) bowlBtn.disabled = true;
    document.getElementById('outcome-banner').classList.remove('show');
    document.getElementById('coach-card').style.display = 'none';
    if (data && data.delivery) {
        document.getElementById('hud-speed').textContent = data.delivery.speed_kmh;
    }
};

GameHUD.prototype._onSimCompleted = function (data) {
    var bowlBtn = document.getElementById('btn-bowl');
    if (bowlBtn) bowlBtn.disabled = false;
    if (!data) return;

    this.lastSimData = data;

    // Outcome Banner
    var banner = document.getElementById('outcome-banner');
    var title = document.getElementById('outcome-title');
    var sub = document.getElementById('outcome-sub');

    title.textContent = data.pursuit.outcome_headline;
    sub.textContent = data.shot.shot_name + " — " + data.shot.shot_description;

    // Check Academy Challenge Completion
    if (data.academy_status && data.academy_status.status === "passed") {
        try {
            var completed = JSON.parse(localStorage.getItem('cricket_completed_levels') || '[]');
            if (completed.indexOf(data.academy_status.level_id) === -1) {
                completed.push(data.academy_status.level_id);
                localStorage.setItem('cricket_completed_levels', JSON.stringify(completed));
            }
        } catch (e) {}
        title.textContent = "🏆 CHALLENGE CLEARED!";
        sub.textContent = data.academy_status.message;
    }

    banner.classList.add('show');

    setTimeout(function () {
        banner.classList.remove('show');
    }, 3200);

    // Update Coach Card Content
    this._updateCoachCardContent();
    document.getElementById('coach-card').style.display = 'block';

    // Update Scoreboard & xRP
    if (data.scoreboard) {
        document.getElementById('hud-overs').textContent = data.scoreboard.overs;
        document.getElementById('hud-score').textContent =
            data.scoreboard.runs_conceded + ' / ' + data.scoreboard.wickets_taken;
        var xrpEl = document.getElementById('hud-xrp');
        var xrpVal = data.scoreboard.total_xrp || 0.0;
        xrpEl.textContent = (xrpVal >= 0 ? '+' : '') + xrpVal.toFixed(1);
        xrpEl.style.color = (xrpVal >= 0 ? '#22c55e' : '#f87171');
    }
};

GameHUD.prototype._updateCoachCardContent = function () {
    if (!this.lastSimData) return;
    var data = this.lastSimData;
    var card = document.getElementById('coach-card');
    var titleEl = document.getElementById('coach-title');
    var lessonEl = document.getElementById('coach-lesson');
    var tipEl = document.getElementById('coach-tip');

    if (this.personaMode === 'junior') {
        titleEl.textContent = "🧠 Junior Brain Power";
        if (data.neuro && data.neuro.junior) {
            lessonEl.textContent = data.neuro.junior.headline;
            tipEl.textContent = "💡 " + data.neuro.junior.tip;
        } else if (data.coaching_tip) {
            lessonEl.textContent = data.coaching_tip.lesson;
            tipEl.textContent = "💡 " + data.coaching_tip.tactical_tip;
        }
    } else {
        titleEl.textContent = "🔬 Pro Telemetry & Neuroscience";
        if (data.neuro && data.neuro.pro) {
            lessonEl.textContent = data.neuro.pro.headline;
            tipEl.textContent = "📊 " + data.neuro.pro.tip;
        }
    }
};

GameHUD.prototype._onAnalyticsReport = function (report) {
    var contentEl = document.getElementById('analytics-content');
    if (!report || !contentEl) return;

    var sb = report.scoreboard;
    var ww = report.wagon_wheel || [];
    var pm = report.pitch_map || [];

    var html = `
        <div style="display:flex;gap:16px;margin-bottom:16px;">
            <div style="flex:1;background:rgba(255,255,255,0.05);padding:10px 14px;border-radius:10px;">
                <div style="font-size:10px;color:#94a3b8;">EXPECTED RUNS PREVENTED (xRP)</div>
                <div style="font-size:22px;font-weight:800;color:${report.total_xrp >= 0 ? '#22c55e' : '#f87171'};">
                    ${report.total_xrp >= 0 ? '+' : ''}${report.total_xrp}
                </div>
            </div>
            <div style="flex:1;background:rgba(255,255,255,0.05);padding:10px 14px;border-radius:10px;">
                <div style="font-size:10px;color:#94a3b8;">DOT BALL PERCENTAGE</div>
                <div style="font-size:22px;font-weight:800;color:#38bdf8;">
                    ${sb.balls_bowled > 0 ? Math.round((sb.dots_bowled / sb.balls_bowled) * 100) : 0} %
                </div>
            </div>
            <div style="flex:1;background:rgba(255,255,255,0.05);padding:10px 14px;border-radius:10px;">
                <div style="font-size:10px;color:#94a3b8;">ECONOMY RATE</div>
                <div style="font-size:22px;font-weight:800;color:#fbbf24;">${sb.economy}</div>
            </div>
        </div>

        <div style="font-size:12px;font-weight:700;color:#fff;margin-bottom:8px;">🎯 Wagon Wheel Shot History (${ww.length} shots)</div>
        <div style="max-height:160px;overflow-y:auto;background:rgba(0,0,0,0.3);border-radius:8px;padding:8px;">
    `;

    ww.forEach(function (shot, idx) {
        html += `
            <div style="display:flex;justify-content:space-between;font-size:11px;padding:4px 0;border-bottom:1px solid rgba(255,255,255,0.05);">
                <span>#${idx+1} ${shot.shot_name} (${shot.distance}m)</span>
                <span style="font-weight:700;color:${shot.runs >= 4 ? '#f87171' : shot.runs === 0 ? '#22c55e' : '#fbbf24'};">
                    ${shot.runs} Runs (${shot.outcome.replace('_', ' ')})
                </span>
            </div>
        `;
    });

    html += `</div>`;
    contentEl.innerHTML = html;
};
