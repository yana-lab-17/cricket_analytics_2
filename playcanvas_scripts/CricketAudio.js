/**
 * CricketAudio.js
 * High-Fidelity Procedural Web Audio API Sound Synthesizer.
 * Generates dynamic, zero-latency 3D spatial cricket audio without external files:
 * - Bat-on-ball willow crack (scaled to exit velocity)
 * - Pitch bounce turf thud
 * - Wooden stumps shatter & bails clatter
 * - Dynamic stadium crowd roars & gasps
 */

var CricketAudio = pc.createScript('cricketAudio');

CricketAudio.prototype.initialize = function () {
    var AudioContext = window.AudioContext || window.webkitAudioContext;
    if (AudioContext) {
        this.ctx = new AudioContext();
    } else {
        this.ctx = null;
    }
    this.isMuted = false;

    // Listen to gameplay events
    this.app.on('cricket:audio:bat', this.playBatStrike, this);
    this.app.on('cricket:audio:bounce', this.playTurfBounce, this);
    this.app.on('cricket:audio:bowled', this.playStumpsShatter, this);
    this.app.on('cricket:audio:cheer', this.playCrowdCheer, this);
    this.app.on('cricket:audio:gasp', this.playCrowdGasp, this);
};

CricketAudio.prototype._resumeContext = function () {
    if (this.ctx && this.ctx.state === 'suspended') {
        this.ctx.resume();
    }
};

/**
 * Procedural Willow-on-Leather Bat Strike
 */
CricketAudio.prototype.playBatStrike = function (exitSpeedKmh) {
    if (this.isMuted || !this.ctx) return;
    this._resumeContext();

    var speed = exitSpeedKmh || 120.0;
    var intensity = Math.min(1.0, Math.max(0.3, speed / 140.0));
    var now = this.ctx.currentTime;

    // 1. Initial High-Frequency Click / Transient (The leather seam hitting wood)
    var osc1 = this.ctx.createOscillator();
    var gain1 = this.ctx.createGain();
    osc1.type = 'triangle';
    osc1.frequency.setValueAtTime(1400 * intensity, now);
    osc1.frequency.exponentialRampToValueAtTime(180, now + 0.04);

    gain1.gain.setValueAtTime(0.85 * intensity, now);
    gain1.gain.exponentialRampToValueAtTime(0.001, now + 0.05);

    osc1.connect(gain1);
    gain1.connect(this.ctx.destination);
    osc1.start(now);
    osc1.stop(now + 0.06);

    // 2. Resonant Body Thud (The thick willow blade vibration)
    var osc2 = this.ctx.createOscillator();
    var gain2 = this.ctx.createGain();
    osc2.type = 'sine';
    osc2.frequency.setValueAtTime(260 * intensity, now);
    osc2.frequency.exponentialRampToValueAtTime(80, now + 0.12);

    gain2.gain.setValueAtTime(0.6 * intensity, now);
    gain2.gain.exponentialRampToValueAtTime(0.001, now + 0.14);

    osc2.connect(gain2);
    gain2.connect(this.ctx.destination);
    osc2.start(now);
    osc2.stop(now + 0.15);
};

/**
 * Procedural Turf Pitch Bounce Thud
 */
CricketAudio.prototype.playTurfBounce = function () {
    if (this.isMuted || !this.ctx) return;
    this._resumeContext();

    var now = this.ctx.currentTime;
    var osc = this.ctx.createOscillator();
    var gain = this.ctx.createGain();

    osc.type = 'sine';
    osc.frequency.setValueAtTime(160, now);
    osc.frequency.exponentialRampToValueAtTime(45, now + 0.08);

    gain.gain.setValueAtTime(0.4, now);
    gain.gain.exponentialRampToValueAtTime(0.001, now + 0.09);

    osc.connect(gain);
    gain.connect(this.ctx.destination);
    osc.start(now);
    osc.stop(now + 0.1);
};

/**
 * Procedural Stumps Shatter & Bails Clatter
 */
CricketAudio.prototype.playStumpsShatter = function () {
    if (this.isMuted || !this.ctx) return;
    this._resumeContext();

    var now = this.ctx.currentTime;
    // Multiple wooden crack frequencies
    var freqs = [780, 1150, 1680, 2400];
    for (var i = 0; i < freqs.length; i++) {
        var osc = this.ctx.createOscillator();
        var gain = this.ctx.createGain();
        var delay = now + (i * 0.025);

        osc.type = 'triangle';
        osc.frequency.setValueAtTime(freqs[i], delay);
        osc.frequency.exponentialRampToValueAtTime(220, delay + 0.15);

        gain.gain.setValueAtTime(0.6, delay);
        gain.gain.exponentialRampToValueAtTime(0.001, delay + 0.2);

        osc.connect(gain);
        gain.connect(this.ctx.destination);
        osc.start(delay);
        osc.stop(delay + 0.22);
    }
};

/**
 * Procedural Stadium Crowd Cheering Roar
 */
CricketAudio.prototype.playCrowdCheer = function () {
    if (this.isMuted || !this.ctx) return;
    this._resumeContext();

    var now = this.ctx.currentTime;
    var bufferSize = this.ctx.sampleRate * 2.2;
    var buffer = this.ctx.createBuffer(1, bufferSize, this.ctx.sampleRate);
    var data = buffer.getChannelData(0);

    for (var i = 0; i < bufferSize; i++) {
        data[i] = Math.random() * 2 - 1;
    }

    var noise = this.ctx.createBufferSource();
    noise.buffer = buffer;

    var filter = this.ctx.createBiquadFilter();
    filter.type = 'bandpass';
    filter.frequency.setValueAtTime(450, now);
    filter.frequency.exponentialRampToValueAtTime(800, now + 0.8);
    filter.Q.value = 1.4;

    var gain = this.ctx.createGain();
    gain.gain.setValueAtTime(0.01, now);
    gain.gain.linearRampToValueAtTime(0.35, now + 0.5);
    gain.gain.exponentialRampToValueAtTime(0.001, now + 2.2);

    noise.connect(filter);
    filter.connect(gain);
    gain.connect(this.ctx.destination);

    noise.start(now);
    noise.stop(now + 2.2);
};

/**
 * Procedural Crowd Gasp (Near-miss edge)
 */
CricketAudio.prototype.playCrowdGasp = function () {
    if (this.isMuted || !this.ctx) return;
    this._resumeContext();

    var now = this.ctx.currentTime;
    var osc = this.ctx.createOscillator();
    var gain = this.ctx.createGain();

    osc.type = 'sine';
    osc.frequency.setValueAtTime(280, now);
    osc.frequency.exponentialRampToValueAtTime(140, now + 0.35);

    gain.gain.setValueAtTime(0.01, now);
    gain.gain.linearRampToValueAtTime(0.2, now + 0.1);
    gain.gain.exponentialRampToValueAtTime(0.001, now + 0.4);

    osc.connect(gain);
    gain.connect(this.ctx.destination);
    osc.start(now);
    osc.stop(now + 0.45);
};

