/*
 * FINGER CONTROL - BROWSER CAMERA WRAPPER  (ES MODULE)
 * ------------------------------------------------------------------
 * Imports MediaPipe Tasks Vision HandLandmarker directly from the
 * self-hosted ESM bundle.  Finds the index fingertip on every camera
 * frame, feeds the position into the pure FingerDirectionDetector,
 * and draws a small camera preview.
 */
import { FilesetResolver, HandLandmarker } from "./vendor/vision_bundle.js";

(function () {
  "use strict";

  var INDEX_TIP = 8;
  var CAM_SPACE_W = 640;
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

  var WASM_PATH = "vendor/wasm";
  var MODEL_URL = "models/hand_landmarker.task";

  function mediaError(message, code) {
    var err = new Error(message);
    err.code = code;
    return err;
  }

  function stopStreamTracks(stream, video) {
    var tracks = stream.getTracks();
    for (var i = 0; i < tracks.length; i++) tracks[i].stop();
    video.srcObject = null;
  }

  /*
   * opts: { video, overlay, detector, onStatus }
   * Resolves with { stop: function } once running.
   * Rejects with an Error whose .code is:
   *   "NO_MEDIA" - browser blocks camera (needs HTTPS)
   *   "MODEL"    - hand model / WASM could not load
   *   or a DOMException name (NotAllowedError, NotFoundError, …)
   */
  async function startFingerCamera(opts) {
    var video = opts.video;
    var overlay = opts.overlay;
    var detector = opts.detector;
    var onStatus = opts.onStatus || function () {};

    // a selfie (front) camera is a mirror image, so steer using what the
    // user SEES on screen: flip L/R by default, U/D is available too.
    var flips = { x: !!opts.flipX, y: !!opts.flipY };

    function applyVideoMirror() {
      var t = "";
      if (flips.x) t += " scaleX(-1)";
      if (flips.y) t += " scaleY(-1)";
      video.style.transform = t.trim();
    }
    function mapX(x01) { return flips.x ? CAM_SPACE_W - x01 * CAM_SPACE_W : x01 * CAM_SPACE_W; }
    function mapY(y01) { return flips.y ? CAM_SPACE_H - y01 * CAM_SPACE_H : y01 * CAM_SPACE_H; }
    applyVideoMirror();

    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
      throw mediaError("Camera requires a secure (HTTPS) connection.", "NO_MEDIA");
    }

    var stream = await navigator.mediaDevices.getUserMedia({
      video: { width: { ideal: 640 }, height: { ideal: 480 }, facingMode: "user" },
      audio: false
    });
    video.srcObject = stream;
    await video.play();

    var fileset = null, landmarker = null;
    try {
      fileset = await FilesetResolver.forVisionTasks(WASM_PATH);
    } catch (err) {
      stopStreamTracks(stream, video);
      throw mediaError("Could not load MediaPipe WASM: " + err.message, "MODEL");
    }

    try {
      landmarker = await HandLandmarker.createFromOptions(fileset, {
        baseOptions: { modelAssetPath: MODEL_URL, delegate: "GPU" },
        runningMode: "VIDEO",
        numHands: 1,
        minHandDetectionConfidence: 0.5,
        minTrackingConfidence: 0.5
      });
    } catch (err) {
      try {
        landmarker = await HandLandmarker.createFromOptions(fileset, {
          baseOptions: { modelAssetPath: MODEL_URL, delegate: "CPU" },
          runningMode: "VIDEO",
          numHands: 1,
          minHandDetectionConfidence: 0.5,
          minTrackingConfidence: 0.5
        });
      } catch (err2) {
        stopStreamTracks(stream, video);
        throw mediaError("Hand-tracking model failed to load: " + err2.message, "MODEL");
      }
    }

    var ctx = overlay.getContext("2d");
    var rafId = null;
    var lastHand = false;
    var lastTs = -1;

    function sizeOverlay() {
      overlay.width = video.clientWidth || 320;
      overlay.height = video.clientHeight || 240;
    }

    function loop(now) {
      if (lastTs === -1 || now > lastTs) lastTs = now;
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
        detector.update(mapX(tip.x), mapY(tip.y));
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
          return { x: mapX(lm.x) / CAM_SPACE_W * w, y: mapY(lm.y) / CAM_SPACE_H * h };
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
    return {
      stop: stop,
      setFlips: function (x, y) {
        flips.x = !!x;
        flips.y = !!y;
        applyVideoMirror();
      }
    };
  }

  window.startFingerCamera = startFingerCamera;
})();
