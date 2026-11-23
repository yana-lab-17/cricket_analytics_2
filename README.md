# 🏏 3D Cricket Fielding Simulation & Neuroscience Platform
### *Grade 1 / Top 1% Club Sports Technology & Interactive Gaming Platform*

A professional-grade, interactive 3D Cricket Simulation and Sports Science platform built for young learners and elite athletes alike.

Combines an **Atmospheric Ballistics & Cognitive Neuroscience Engine (Python)** with a **Procedural Web Audio & PlayCanvas WebGL 3D Game Layer**.

---

## 🏛️ The 6 Operational Pillars Built into this Codebase

### 🎮 Pillar 1: AAA 3D Visuals, Hawk-Eye Tracers & Procedural Web Audio Engine
- **Procedural Sound Synthesizer (`CricketAudio.js`)**:
  - Synthesizes realistic willow-on-leather bat cracks (scaled to exit velocity via oscillators).
  - Turf pitch bounce thud, wooden stumps shattering on bowled, dynamic stadium crowd cheers and gasps.
  - Zero external `.mp3` dependencies; 100% real-time browser Web Audio API synthesis!
- **Hawk-Eye 3D Trajectory Tracers & Pitch Impact Crater**:
  - Displays dynamic 3D ballistic tracers and chalk landing marks where the ball bounces on the turf.
- **Cinematic Slow-Motion Replay**:
  - Dedicated **"⏪ Replay (0.45x)"** button plays back the last delivery in slow-motion with synchronized sound.

### 🔬 Pillar 2: Hawk-Eye Physics, Bat Sweet-Spot Dynamics & Pitch Wear
- **Bat-Ball Collision Zones**:
  - Middle / Sweet Spot (peak exit velocity), Outside Edge (slips deflection), Inside Edge, Toe-end dig-outs.
- **Atmospheric & Aerodynamics Modeling**:
  - Humidity, air density, wind vectors, and late reverse swing at speeds $>138\text{ km/h}$.
- **Pitch Degradation Wear States**:
  - 🌿 **Day 1 Green**: High bounce, steep seam nip, favors pacers.
  - 🏏 **Day 3 Flat**: True, consistent bounce, high-scoring highway.
  - 🏜️ **Day 5 Dusty**: Low, variable bounce, massive spin turn and grip.

### 🧠 Pillar 3: Dual-Mode Cricket Neuroscience Cognitive Engine
- **Cognitive Telemetry Calculated per Ball**:
  - **Decision Window ($\text{ms}$)**: Time available between pitch bounce and crease arrival.
  - **Saccadic Latency ($195\text{ms}$)**: Foveal gaze tracking delay.
  - **Cognitive Load Score ($0 - 100$)**: Neural strain induced by express pace.
- **Dual-Persona Pedagogical Voices**:
  - **Junior Mode (Ages 7–14)**: Uses superhero, brain-computer, and auto-pilot analogies so children understand instantly.
  - **Pro Mode (Elite Players / Coaches)**: Displays kinetic chain data, visual saccade thresholds, and tactical offset recommendations.

### 🎓 Pillar 4: Captain's Academy Progression & Challenge Scenarios
Structured career challenges accessible via the in-game modal:
- **Level 1: The Leaking Bucket**: Plug the cover gap against 142 km/h outswing bowling.
- **Level 2: The Bouncer Trap**: Set deep boundary fielders to catch aerial hooks/pulls.
- **Level 3: Spinner's Web**: Choke the batter with close catchers inside the ring on a dusty deck.
- **Level 4: T20 Death Over Defense**: Defend 5 runs or less using pinpoint reverse-swinging yorkers.
- **Level 5: Grandmaster Captaincy**: Achieve complete tactical domination against an adaptive batter.

### ⚡ Pillar 5: Zero-Lag Pure WebSocket & Cross-Platform Architecture
- **Pure Python RFC 6455 WebSocket Implementation**: Runs on any plain Python 3.8+ setup without external network dependencies or broken pip packages.
- **3D Interactive Drag-and-Drop**: Click, drag, and drop any of the 11 fielders anywhere on the ground with instantaneous visual clamping and server sync.

### 📊 Pillar 6: Pro Analytics Suite (Wagon Wheel, Pitch Map & xRP)
- **Expected Runs Prevented (xRP)**: Advanced proprietary metric calculating runs saved or conceded per delivery based on field placement.
- **Interactive Match Analytics Suite**:
  - Complete 360° Wagon Wheel history of all shots conceded.
  - Pitch Map landing cluster coordinates.
  - Economy Rate and Dot-Ball Percentage.

---

## 🚀 Quick Start

### 1. Launch Game on Linux / macOS
```bash
./start_game.sh
```
Or directly:
```bash
python3 -m backend.game_server
```

### 2. Launch Game on Windows
Double-click `start_simulator.bat` or run:
```cmd
python -m backend.game_server
```

### 3. Open in Browser
Visit **`http://localhost:8080`** (or `http://localhost:8081`).

---

## 🧪 Comprehensive Verification Test Suite

Run the full end-to-end architecture verification test:
```bash
python3 test_game.py
```
*Verifies WebSocket 101 Handshake, 3D Fielder Drag-and-Drop, Day 1 Green pitch condition physics, 148 km/h delivery simulation, bat edge deflection, cognitive neuroscience metrics, Captain's Academy progression, and Wagon Wheel/xRP match analytics.*

---

## 🧠 NeuroSport-Cricket LLM Engine (Custom Non-Generic Architecture)

A custom, production-grade domain foundation model designed from scratch for cricket ballistics, international playing conditions, and cognitive neuroscience.

### 📐 Architectural Innovations:
- **Grouped-Query Attention (GQA)**: 4:1 query-to-KV head ratio for ultra-fast $O(1)$ streaming inference.
- **Rotary Position Embeddings (RoPE)**: High-frequency base ($\theta = 500,000$) for long-context match history extrapolation ($4096+$ tokens).
- **Biomechanical Cognitive Cross-Attention**: Interleaved cross-attention layers correlating physical telemetry (release velocity, saccadic latency, decision window, pitch coordinates) with text tokens.
- **SwiGLU Multi-Scale Feed-Forward**: As used in modern frontier architectures (LLaMA-3/PaLM).
- **RMSNorm Pre-Normalization**: Root-mean-square normalization with scaled residual projections.

### 📂 Dataset Ingestion Directory Layout:
Drop your external data files into `llm/raw_datasets/` — the pipeline automatically ingests, parses, and tokenizes them:
- `llm/raw_datasets/matches/`: Place international match ball-by-ball JSON files (e.g. Cricsheet format). The stream parser transforms them into continuous chronological sequences.
- `llm/raw_datasets/rules/`: Place additional playing conditions or laws (`.txt`, `.md`, `.json`).
- `llm/raw_datasets/previous/`: Place legacy datasets (`.json`, `.jsonl`).

### ⚡ Running LLM Pipeline & Training:
- **Verify full LLM pipeline**:
  ```bash
  python3 test_llm.py
  ```
- **Launch Pre-Training & DPO Alignment**:
  ```bash
  ./train_neurosport.sh base 5 4 8 3e-4
  ```
- **Interactive Terminal Chat**:
  ```bash
  python3 -m llm.server --chat
  ```
