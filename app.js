/*
 * SNAKE & APPLE - browser game frontend
 * Keyboard control + optional webcam finger control.
 */
(function () {
  "use strict";

  // ---------- config (same values as the Python game) ----------
  var GRID = 20;
  var W = 600;
  var H = 400;
  var COLS = W / GRID;   // 30
  var ROWS = H / GRID;   // 20
  var START_LENGTH = 3;
  var FINGER_POLL_MS = 50;

  var SPEEDS = { slow: 150, medium: 110, fast: 75 };
  var HS_KEY = "snake_high_score";

  // ---------- DOM ----------
  var $ = function (id) { return document.getElementById(id); };
  var els = {
    start: $("start-screen"),
    howto: $("howto-screen"),
    game: $("game-screen"),
    btnKeyboard: $("btn-keyboard"),
    btnFinger: $("btn-finger"),
    ctlLabel: $("ctl-label"),
    btnStart: $("btn-start"),
    btnHowto: $("btn-howto"),
    btnBack: $("btn-back"),
    btnAgain: $("btn-again"),
    btnMenu: $("btn-menu"),
    score: $("score-label"),
    high: $("high-label"),
    level: $("level-label"),
    board: $("board"),
    status: $("status"),
    pauseOverlay: $("pause-overlay"),
    gameover: $("gameover-modal"),
    finalScore: $("final-score"),
    newHigh: $("new-high"),
    cameraBox: $("camera-box"),
    camState: $("cam-state"),
    video: $("video"),
    camOverlay: $("cam-overlay")
  };

  var ctx = els.board.getContext("2d");

  // ---------- state ----------
  var engine = new window.SnakeEngine({ cols: COLS, rows: ROWS, startLength: START_LENGTH });
  var controlMode = "keyboard";
  var running = false;
  var paused = false;
  var level = "Easy";
  var timerId = null;
  var currentSpeed = SPEEDS.slow;
  var fingerTimerId = null;
  var messageTimer = null;
  var bannerTimer = null;
  var detector = null;
  var camera = null;
  var highScore = 0;
  var camStatus = "";

  function loadHighScore() {
    try { highScore = parseInt(localStorage.getItem(HS_KEY) || "0", 10) || 0; }
    catch (e) { highScore = 0; }
  }
  function saveHighScore() {
    try { localStorage.setItem(HS_KEY, String(highScore)); } catch (e) {}
  }

  // ---------- screens ----------
  function showScreen(name) {
    els.start.classList.remove("active");
    els.howto.classList.remove("active");
    els.game.classList.remove("active");
    if (name === "start") els.start.classList.add("active");
    else if (name === "howto") els.howto.classList.add("active");
    else els.game.classList.add("active");
  }

  // ---------- control mode ----------
  function setControlMode(mode) {
    controlMode = mode;
    if (mode === "finger") {
      els.btnFinger.classList.add("selected");
      els.btnKeyboard.classList.remove("selected");
      els.ctlLabel.textContent = "Control: ✋ FINGER";
    } else {
      els.btnKeyboard.classList.add("selected");
      els.btnFinger.classList.remove("selected");
      els.ctlLabel.textContent = "Control: ⌨️ KEYBOARD";
    }
  }

  // ---------- drawing ----------
  function render() {
    ctx.clearRect(0, 0, W, H);
    drawApple();
    drawSnake();
  }

  function drawApple() {
    if (!engine.apple) return;
    var px = engine.apple.x * GRID;
    var py = engine.apple.y * GRID;
    ctx.beginPath();
    ctx.ellipse(px + GRID / 2, py + GRID / 2 + 1, GRID / 2 - 3, GRID / 2 - 3, 0, 0, Math.PI * 2);
    ctx.fillStyle = "#e53935";
    ctx.fill();
    ctx.lineWidth = 2;
    ctx.strokeStyle = "#b71c1c";
    ctx.stroke();
    // leaf
    ctx.beginPath();
    ctx.ellipse(px + GRID / 2 - 1, py - 2, 5, 3, -0.4, 0, Math.PI * 2);
    ctx.fillStyle = "#66bb6a";
    ctx.fill();
  }

  function drawSnake() {
    for (var i = 0; i < engine.snake.length; i++) {
      var s = engine.snake[i];
      var px = s.x * GRID;
      var py = s.y * GRID;
      if (i === 0) {
        // head: bright circle with an eye
        ctx.beginPath();
        ctx.arc(px + GRID / 2, py + GRID / 2, GRID / 2 - 1, 0, Math.PI * 2);
        ctx.fillStyle = "#4caf50";
        ctx.fill();
        ctx.lineWidth = 2;
        ctx.strokeStyle = "#1b5e20";
        ctx.stroke();
        ctx.beginPath();
        ctx.arc(px + 8, py + 8, 2.4, 0, Math.PI * 2);
        ctx.fillStyle = "#1b5e20";
        ctx.fill();
      } else {
        ctx.fillStyle = "#66bb6a";
        ctx.fillRect(px + 1, py + 1, GRID - 2, GRID - 2);
        ctx.lineWidth = 1;
        ctx.strokeStyle = "#2e7d32";
        ctx.strokeRect(px + 1, py + 1, GRID - 2, GRID - 2);
      }
    }
  }

  function drawMessage(text) {
    clearMessage();
    ctx.font = "bold 22px Arial";
    ctx.textAlign = "center";
    ctx.fillStyle = "#ffffff";
    ctx.fillText(text, W / 2, H / 2);
    messageTimer = setTimeout(clearMessage, 1000);
  }
  function clearMessage() {
    if (messageTimer) { clearTimeout(messageTimer); messageTimer = null; }
    render();
  }

  function drawLevelBanner(text) {
    clearTimeout(bannerTimer);
    ctx.font = "bold 30px Arial";
    ctx.textAlign = "center";
    ctx.fillStyle = "#ffd166";
    ctx.fillText(text, W / 2, H / 2);
    bannerTimer = setTimeout(function () {
      bannerTimer = null;
      render();
    }, 1200);
  }

  // ---------- level ----------
  function updateLevel() {
    var newLevel, speed;
    if (engine.score < 5) { newLevel = "Easy"; speed = SPEEDS.slow; }
    else if (engine.score < 10) { newLevel = "Medium"; speed = SPEEDS.medium; }
    else { newLevel = "Fast"; speed = SPEEDS.fast; }

    if (newLevel !== level && engine.score > 0 && level !== "Easy") {
      drawLevelBanner("🚀 LEVEL UP!");
    }
    level = newLevel;
    els.level.textContent = "Level: " + level;
    resetLoopSpeed(speed);
  }

  function updateScores() {
    els.score.textContent = "Score: " + engine.score;
    els.high.textContent = "🏆 High Score: " + highScore;
  }

  // ---------- game loop ----------
  function startGame() {
    showScreen("game");
    stopFingerControl();
    engine.reset();
    running = true;
    paused = false;
    level = "Easy";
    els.gameover.classList.add("hidden");
    els.pauseOverlay.classList.add("hidden");
    updateScores();
    els.level.textContent = "Level: Easy";
    render();
    drawLevelBanner("GO! 🐍");
    startLoop(SPEEDS.slow);

    if (controlMode === "finger") {
      startFingerControl();
    } else {
      setStatus("Use Arrow Keys to Move  |  P = Pause  |  R = Restart  |  Esc = Menu");
    }
  }

  function startLoop(speed) {
    currentSpeed = speed;
    clearLoop();
    timerId = setInterval(tick, speed);
  }
  function resetLoopSpeed(speed) {
    if (running && !paused) startLoop(speed);
  }
  function clearLoop() {
    if (timerId) { clearInterval(timerId); timerId = null; }
  }

  function tick() {
    if (!running || paused) return;
    var result = engine.step();
    if (result.gameOver) {
      handleGameOver();
      return;
    }
    render();
    if (result.ate) {
      drawMessage("Yummy! 😋 +1 🍎");
      beep(1200, 100);
      updateScores();
      updateLevel();
    }
  }

  // ---------- pause ----------
  function togglePause() {
    if (!running) return;
    paused = !paused;
    els.pauseOverlay.classList.toggle("hidden", !paused);
    if (!paused) startLoop(currentSpeed);
  }

  // ---------- game over ----------
  function handleGameOver() {
    running = false;
    clearLoop();
    beep(400, 300);

    var isNew = engine.score > highScore;
    if (isNew) {
      highScore = engine.score;
      saveHighScore();
      updateScores();
      beep2();
    }
    els.finalScore.textContent = "Your Score: " + engine.score;
    els.newHigh.classList.toggle("hidden", !isNew);
    els.gameover.classList.remove("hidden");
  }

  // ---------- finger control ----------
  function startFingerControl() {
    detector = new window.FingerDirectionDetector();
    els.cameraBox.classList.remove("hidden");
    setCamStatus("starting camera…");
    setStatus("✋ Starting webcam hand tracking…");

    startFingerCamera({
      video: els.video,
      overlay: els.camOverlay,
      detector: detector,
      onStatus: function (s) {
        camStatus = s;
        refreshStatus();
      }
    }).then(function (cam) {
      camera = cam;
      setCamStatus("on");
      fingerTimerId = setInterval(pollFinger, FINGER_POLL_MS);
      refreshStatus();
    }).catch(function (err) {
      console.error("Finger camera error:", err);
      var msg = "⚠️ Webcam unavailable - using KEYBOARD controls  |  P = Pause  |  R = Restart";
      if (err && err.code === "NO_MEDIA") {
        msg = "⚠️ Camera is blocked - this page must be opened over HTTPS (not file:// or plain http)  |  using KEYBOARD controls";
      } else if (err && err.code === "MODEL") {
        msg = "⚠️ AI hand-tracker couldn't load (check internet, or a firewall/blocker is stopping the CDN)  |  using KEYBOARD controls";
      } else if (err && (err.name === "NotAllowedError" || err.name === "SecurityError" || err.name === "PermissionDeniedError")) {
        msg = "⚠️ Camera permission DENIED - click the camera icon in the address bar and allow it, then choose FINGER again  |  using KEYBOARD controls";
      } else if (err && (err.name === "NotFoundError" || err.name === "DevicesNotFoundError" || err.name === "OverconstrainedError")) {
        msg = "⚠️ No webcam found - connect/plug in a camera and choose FINGER again  |  using KEYBOARD controls";
      } else if (err && (err.name === "NotReadableError" || err.name === "TrackStartError")) {
        msg = "⚠️ Webcam is busy in another app - close it, refresh, and choose FINGER again  |  using KEYBOARD controls";
      }
      setCamStatus("error: " + (err && (err.code || err.name) ? (err.code || err.name) : "unknown"));
      setStatus(msg, true);
      els.cameraBox.classList.add("hidden");
    });
  }

  function pollFinger() {
    if (!running || !detector) return;
    var dir = detector.getDirection();
    if (dir) engine.changeDirection(dir);
    refreshStatus();
  }

  function refreshStatus() {
    if (controlMode !== "finger" || !detector) return;
    var hand = detector.handSeen;
    var dir = detector.getLastDirection();
    var d = dir ? dir.toUpperCase() : "—";
    var handText = hand ? "HAND: DETECTED ✅  |  " : "HAND: looking…  |  ";
    setStatus(handText + "Finger: " + d + "  |  P = Pause  |  R = Restart  |  Esc = Menu");
  }

  function stopFingerControl() {
    if (fingerTimerId) { clearInterval(fingerTimerId); fingerTimerId = null; }
    if (camera) { try { camera.stop(); } catch (e) {} camera = null; }
    detector = null;
    els.cameraBox.classList.add("hidden");
  }

  function setStatus(text, bad) {
    els.status.textContent = text || "";
    els.status.classList.toggle("bad", !!bad);
  }
  function setCamStatus(text) {
    els.camState.textContent = text || "";
  }

  // ---------- tiny beeps ----------
  var audioCtx = null;
  function beep(freq, ms) {
    try {
      if (!audioCtx) audioCtx = new (window.AudioContext || window.webkitAudioContext)();
      var osc = audioCtx.createOscillator();
      var gain = audioCtx.createGain();
      osc.frequency.value = freq;
      osc.connect(gain);
      gain.connect(audioCtx.destination);
      gain.gain.setValueAtTime(0.12, audioCtx.currentTime);
      osc.start();
      osc.stop(audioCtx.currentTime + ms / 1000);
    } catch (e) {}
  }
  function beep2() {
    beep(900, 150);
    setTimeout(function () { beep(1400, 200); }, 160);
  }

  // ---------- keyboard ----------
  document.addEventListener("keydown", function (e) {
    var k = e.key;

    if (["ArrowUp", "ArrowDown", "ArrowLeft", "ArrowRight", " "].indexOf(k) !== -1) {
      e.preventDefault();
    }

    // start screen: space starts game, F/K choose control
    if (els.start.classList.contains("active")) {
      if (k === " ") {
        e.preventDefault();
        startGame();
        return;
      }
      if (k === "f" || k === "F") { setControlMode("finger"); return; }
      if (k === "k" || k === "K") { setControlMode("keyboard"); return; }
    }

    if (k === "ArrowUp") { engine.changeDirection("up"); return; }
    if (k === "ArrowDown") { engine.changeDirection("down"); return; }
    if (k === "ArrowLeft") { engine.changeDirection("left"); return; }
    if (k === "ArrowRight") { engine.changeDirection("right"); return; }

    if (k === "p" || k === "P") { togglePause(); return; }
    if (k === "r" || k === "R") { startGame(); return; }
    if (k === "Escape") { goToMenu(); return; }
  });

  function goToMenu() {
    running = false;
    clearLoop();
    stopFingerControl();
    showScreen("start");
  }

  // ---------- buttons ----------
  els.btnKeyboard.addEventListener("click", function () { setControlMode("keyboard"); });
  els.btnFinger.addEventListener("click", function () { setControlMode("finger"); });
  els.btnStart.addEventListener("click", startGame);
  els.btnHowto.addEventListener("click", function () { showScreen("howto"); });
  els.btnBack.addEventListener("click", function () { showScreen("start"); });
  els.btnAgain.addEventListener("click", startGame);
  els.btnMenu.addEventListener("click", goToMenu);

  loadHighScore();
  updateScores();
})();