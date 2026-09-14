/*
 * FINGER CONTROL - BROWSER CAMERA WRAPPER
 * ------------------------------------------------------------------
 * Uses MediaPipe Tasks Vision (HandLandmarker) in the browser to find
 * the index fingertip on every camera frame, then feeds the position
 * into the pure FingerDirectionDetector which produces snake
 * directions. Also draws a small, optional camera preview.
 */
(function () {
  "use strict";

  var INDEX_TIP = 8;
  var CAM_SPACE_W = 640;   // fixed coordinate space for consistent thresholds
  var CAM_SPACE_H = 480;

  var CONNECTIONS = [
    [0, 1], [1, 2], [2, 3], [3, 4],
    [0, 5], [5, 6], [6, 7], [7, 8],
    [5, 9], [9, 10], [10, 11], [11, 12],
    [9, 13], [13, 14], [14, 15], [15, 16],
    [13, 17], [17, 18], [18, 19], [19, 20],
    [0, 17]
  ];

  var ARROWS = { up: [0, -1], down: [0, 1], left: [-1, 0], right: [1, 0] };

  var WASM_PATH = "https://cdn.jsdelivr.net/npm/@mediapipe/tasks-vision@0.10.0/wasm";
  var MODEL_URL = "https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/1/hand_landmarker.task";

  /*
   * Start the webcam + hand tracking.
   * opts: { video, overlay, detector, onStatus }
   * Resolves with { stop: function } once running.
   */
  async function startFingerCamera(opts) {
    var video = opts.video;
    var overlay = opts.overlay;
    var detector = opts.detector;
    var onStatus = opts.onStatus || function () {};

    if (typeof MediaPipe === "undefined" || !MediaPipe.FilesetResolver) {
      throw new Error("MediaPipe failed to load from the CDN. Check your internet and refresh.");
    }

    var fileset = await MediaPipe.FilesetResolver.forVisionTasks(WASM_PATH);

    var landmarker = null;
    try {
      landmarker = await MediaPipe.HandLandmarker.createFromOptions(fileset, {
        baseOptions: {
          modelAssetPath: MODEL_URL,
          delegate: "GPU"
        },
        runningMode: "VIDEO",
        numHands: 1,
        minHandDetectionConfidence: 0.5,
        minTrackingConfidence: 0.5
      });
    } catch (err) {
      // some browsers/devices do not support the GPU delegate
      landmarker = await MediaPipe.HandLandmarker.createFromOptions(fileset, {
        baseOptions: { modelAssetPath: MODEL_URL, delegate: "CPU" },
        runningMode: "VIDEO",
        numHands: 1,
        minHandDetectionConfidence: 0.5,
        minTrackingConfidence: 0.5
      });
    }

    var stream = await navigator.mediaDevices.getUserMedia({
      video: { width: { ideal: 640 }, height: { ideal: 480 }, facingMode: "user" },
      audio: false
    });
    video.srcObject = stream;
    await video.play();

    var ctx = overlay.getContext("2d");
    var rafId = null;
    var lastHand = false;
    var lastTs = -1;

    function sizeOverlay() {
      overlay.width = video.clientWidth || 320;
      overlay.height = video.clientHeight || 240;
    }

    function loop(now) {
      if (lastTs === -1 || now > lastTs) lastTs = now; // keep timestamps increasing
      var result;
      try {
        result = landmarker.detectForVideo(video, lastTs);
      } catch (err) {
        result = null;
      }

      var landmarks = null;
      if (result && result.landmarks && result.landmarks.length) {
        landmarks = result.landmarks[0];
      }

      if (landmarks) {
        var tip = landmarks[INDEX_TIP];
        detector.update(tip.x * CAM_SPACE_W, tip.y * CAM_SPACE_H);
        detector.handSeen = true;
        drawPreview(landmarks);
        if (!lastHand) { lastHand = true; onStatus("detected"); }
      } else {
        detector.handSeen = false;
        detector.markHandLost();
        if (lastHand) { lastHand = false; onStatus("lost"); }
        drawPreview(null);
      }

      rafId = requestAnimationFrame(loop);
    }

    function drawPreview(landmarks) {
      sizeOverlay();
      var w = overlay.width;
      var h = overlay.height;
      ctx.clearRect(0, 0, w, h);

      var hand = detector.handSeen;
      if (landmarks) {
        var pts = landmarks.map(function (lm) {
          return { x: lm.x * w, y: lm.y * h };
        });
        ctx.strokeStyle = "rgba(255,200,80,0.95)";
        ctx.lineWidth = 2;
        for (var i = 0; i < CONNECTIONS.length; i++) {
          var a = pts[CONNECTIONS[i][0]];
          var b = pts[CONNECTIONS[i][1]];
          ctx.beginPath();
          ctx.moveTo(a.x, a.y);
          ctx.lineTo(b.x, b.y);
          ctx.stroke();
        }
        for (var j = 0; j < pts.length; j++) {
          ctx.beginPath();
          if (j === INDEX_TIP) {
            ctx.fillStyle = "#00e676";
            ctx.arc(pts[j].x, pts[j].y, 7, 0, Math.PI * 2);
            ctx.fill();
            ctx.lineWidth = 2;
            ctx.strokeStyle = "#8dffc9";
            ctx.stroke();
          } else {
            ctx.fillStyle = "#ffffff";
            ctx.arc(pts[j].x, pts[j].y, 2, 0, Math.PI * 2);
            ctx.fill();
          }
        }
        var dir = detector.getLastDirection();
        var arrow = ARROWS[dir];
        if (arrow) {
          var t = pts[INDEX_TIP];
          ctx.strokeStyle = "#00c8ff";
          ctx.lineWidth = 4;
          ctx.beginPath();
          ctx.moveTo(t.x, t.y);
          ctx.lineTo(t.x + arrow[0] * 38, t.y + arrow[1] * 38);
          ctx.stroke();
          ctx.fillStyle = "#00c8ff";
          ctx.beginPath();
          ctx.arc(t.x + arrow[0] * 38, t.y + arrow[1] * 38, 4, 0, Math.PI * 2);
          ctx.fill();
        }
      }

      ctx.font = "bold 13px Arial";
      ctx.textAlign = "left";
      ctx.fillStyle = hand ? "#00e676" : "#ff5252";
      ctx.fillText(hand ? "HAND: DETECTED" : "HAND: NOT FOUND", 8, 22);
      var dirText = detector.getLastDirection();
      ctx.fillStyle = "#ffd166";
      ctx.fillText("DIRECTION: " + (dirText ? dirText.toUpperCase() : "NONE"), 8, 42);
    }

    function stop() {
      if (rafId != null) cancelAnimationFrame(rafId);
      rafId = null;
      var tracks = stream.getTracks();
      for (var i = 0; i < tracks.length; i++) tracks[i].stop();
      video.srcObject = null;
      try { landmarker.close(); } catch (e) {}
    }

    sizeOverlay();
    rafId = requestAnimationFrame(loop);
    onStatus("starting");
    return { stop: stop };
  }

  if (typeof module !== "undefined" && module.exports) {
    module.exports = { startFingerCamera: startFingerCamera };
  } else {
    window.startFingerCamera = startFingerCamera;
  }
})();