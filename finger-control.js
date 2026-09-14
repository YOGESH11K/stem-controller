/*
 * FINGER DIRECTION DETECTOR (pure, works in browser and Node)
 * ------------------------------------------------------------------
 * Turns the MOTION of a fingertip into up/down/left/right, mirroring
 * the Python controller exactly:
 *   - previous/current position tracking
 *   - movement delta (dx = current - reference)
 *   - dominant axis + minimum movement threshold
 *   - optional smoothing (EMA on the position)
 *   - a small cooldown / debounce between changes
 *   - classic Snake rule: no instant reversal
 * A new direction is handed out exactly once (like a key press) until
 * the next finger gesture.
 */
(function () {
  "use strict";

  var OPPOSITE = { up: "down", down: "up", left: "right", right: "left" };

  function FingerDirectionDetector(opts) {
    opts = opts || {};
    this.threshold = opts.threshold == null ? 30 : opts.threshold;  // pixels
    this.cooldown = opts.cooldown == null ? 0.15 : opts.cooldown;   // seconds
    this.smoothing = opts.smoothing == null ? 0.5 : opts.smoothing; // 0..1

    this.direction = null;        // last direction (for display)
    this.pending = false;         // a NEW direction is ready
    this.lastEmit = 0;            // ms timestamp of last accepted change
    this.anchor = null;           // reference point for measuring motion
    this.smoothed = null;         // EMA-filtered fingertip position
    this.prevPos = null;          // raw fingertip of the previous frame
    this.handSeen = false;

    // diagnostic deltas (display only)
    this.dx = 0;
    this.dy = 0;
  }

  FingerDirectionDetector.prototype.update = function (x, y) {
    if (this.prevPos) {
      this.dx = x - this.prevPos.x;
      this.dy = y - this.prevPos.y;
    }
    this.prevPos = { x: x, y: y };

    // first frame with a hand: just remember the starting spot
    if (this.smoothed == null) {
      this.smoothed = { x: x, y: y };
      this.anchor = { x: x, y: y };
      return;
    }

    // smooth the fingertip position so camera noise is ignored
    var sx = this.smoothing * x + (1 - this.smoothing) * this.smoothed.x;
    var sy = this.smoothing * y + (1 - this.smoothing) * this.smoothed.y;
    this.smoothed = { x: sx, y: sy };

    // cumulative motion since the last accepted direction change
    var dx = sx - this.anchor.x;
    var dy = sy - this.anchor.y;

    // dominant axis decides; the threshold ignores small motions
    if (Math.abs(dx) >= Math.abs(dy)) {
      if (Math.abs(dx) >= this.threshold) this.emit(dx > 0 ? "right" : "left");
    } else {
      if (Math.abs(dy) >= this.threshold) this.emit(dy > 0 ? "down" : "up");
    }
  };

  FingerDirectionDetector.prototype.emit = function (dir) {
    var now = Date.now();
    if (now - this.lastEmit < this.cooldown * 1000) return; // debounce

    if (dir === OPPOSITE[this.direction]) {
      // instant reversal is not allowed; restart the motion meter
      this.anchor = { x: this.smoothed.x, y: this.smoothed.y };
      return;
    }

    this.direction = dir;
    this.pending = true;
    this.lastEmit = now;
    this.anchor = { x: this.smoothed.x, y: this.smoothed.y };
  };

  /* Hand a new direction to the game exactly once. */
  FingerDirectionDetector.prototype.getDirection = function () {
    if (this.pending) {
      this.pending = false;
      return this.direction;
    }
    return null;
  };

  /* Most recent direction, for display only (never cleared). */
  FingerDirectionDetector.prototype.getLastDirection = function () {
    return this.direction;
  };

  /* Hand lost: keep the direction, restart the motion meter. */
  FingerDirectionDetector.prototype.markHandLost = function () {
    this.smoothed = null;
    this.anchor = null;
    this.prevPos = null;
    this.dx = 0;
    this.dy = 0;
  };

  if (typeof module !== "undefined" && module.exports) {
    module.exports = { FingerDirectionDetector: FingerDirectionDetector };
  } else {
    window.FingerDirectionDetector = FingerDirectionDetector;
  }
})();