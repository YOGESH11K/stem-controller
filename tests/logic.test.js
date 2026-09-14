"use strict";
const assert = require("node:assert");
const path = require("node:path");

const { SnakeEngine } = require(path.join(__dirname, "..", "game-logic.js"));
const { FingerDirectionDetector } = require(path.join(__dirname, "..", "finger-control.js"));

let passed = 0;
function expect(label, fn) {
  try {
    fn();
    console.log("OK  " + label);
    passed++;
  } catch (err) {
    console.log("FAIL " + label + "  ->  " + err.message);
    process.exitCode = 1;
  }
}

// ============================================================
// SNAKE ENGINE
// ============================================================
expect("snake resets to middle, length 3, moving right", () => {
  const e = new SnakeEngine({ cols: 30, rows: 20, startLength: 3 });
  assert.strictEqual(e.snake.length, 3);
  assert.strictEqual(e.direction, "right");
  assert.strictEqual(e.score, 0);
});

expect("step moves the snake 1 cell right", () => {
  const e = new SnakeEngine({ cols: 30, rows: 20, startLength: 3 });
  const head = e.snake[0];
  const r = e.step();
  assert.deepStrictEqual(r, { gameOver: false, ate: false });
  assert.strictEqual(e.snake[0].x, head.x + 1);
});

expect("changeDirection works", () => {
  const e = new SnakeEngine({ cols: 30, rows: 20, startLength: 3 });
  e.changeDirection("up");
  e.step();
  assert.strictEqual(e.direction, "up");
});

expect("instant reversal RIGHT -> LEFT is blocked", () => {
  const e = new SnakeEngine({ cols: 30, rows: 20, startLength: 3 });
  e.changeDirection("left");
  e.step();
  assert.strictEqual(e.direction, "right");
});

expect("apple eaten -> score 1 and snake grows", () => {
  const e = new SnakeEngine({ cols: 30, rows: 20, startLength: 3 });
  const head = e.snake[0];
  e.apple = { x: head.x + 1, y: head.y };
  const r = e.step();
  assert.ok(r.ate);
  assert.strictEqual(e.score, 1);
  assert.strictEqual(e.snake.length, 4);
});

expect("wall collision -> game over", () => {
  const e = new SnakeEngine({ cols: 30, rows: 20, startLength: 3 });
  e.snake = [{ x: 29, y: 5 }, { x: 28, y: 5 }, { x: 27, y: 5 }];
  e.direction = "right";
  e.nextDirection = "right";
  const r = e.step();
  assert.ok(r.gameOver);
});

expect("self collision -> game over", () => {
  const e = new SnakeEngine({ cols: 10, rows: 10, startLength: 3 });
  e.snake = [
    { x: 2, y: 1 }, { x: 1, y: 1 }, { x: 1, y: 2 }, { x: 2, y: 2 }, { x: 3, y: 2 },
  ];
  e.direction = "left";
  e.nextDirection = "left";
  const r = e.step();
  assert.ok(r.gameOver);
  assert.strictEqual(e.snake[0].x, 2);
});

// ============================================================
// FINGER DIRECTION DETECTOR
// ============================================================
const D = () => new FingerDirectionDetector({ threshold: 30, cooldown: 0, smoothing: 0.5 });

function setFinger(d, x, y, n) {
  for (let i = 0; i < (n || 4); i++) d.update(x, y);
}

expect("no motion -> no direction", () => {
  const d = D();
  d.update(100, 100);
  assert.strictEqual(d.getLastDirection(), null);
});

expect("move right -> right", () => {
  const d = D();
  d.update(100, 100);
  setFinger(d, 140, 100);
  assert.strictEqual(d.getLastDirection(), "right");
});

expect("keep moving right stays right", () => {
  const d = D();
  d.update(100, 100);
  setFinger(d, 140, 100);
  setFinger(d, 180, 100);
  assert.strictEqual(d.getLastDirection(), "right");
});

expect("move down -> down", () => {
  const d = D();
  d.update(100, 100);
  setFinger(d, 140, 100);
  setFinger(d, 180, 100);
  setFinger(d, 180, 140);
  assert.strictEqual(d.getLastDirection(), "down");
});

expect("UP right after DOWN is blocked (classic rule)", () => {
  const d = D();
  d.update(100, 100);
  setFinger(d, 140, 100);
  setFinger(d, 180, 100);
  setFinger(d, 180, 140);
  setFinger(d, 180, 100);
  assert.strictEqual(d.getLastDirection(), "down");
});

expect("one-shot: getDirection returns once then null", () => {
  const d = D();
  d.update(100, 100);
  setFinger(d, 140, 100);
  assert.strictEqual(d.getDirection(), "right");
  assert.strictEqual(d.getDirection(), null);
});

expect("hand lost keeps direction and resets motion meter", () => {
  const d = D();
  d.update(100, 100);
  setFinger(d, 140, 100);
  d.markHandLost();
  setFinger(d, 500, 300);
  assert.strictEqual(d.getLastDirection(), "right");
  setFinger(d, 500, 340);
  assert.strictEqual(d.getLastDirection(), "down");
});

expect("jitter under the threshold is ignored", () => {
  const d = D();
  d.update(500, 300);
  setFinger(d, 500, 340);
  setFinger(d, 510, 350);
  assert.strictEqual(d.getLastDirection(), "down");
});

console.log("");
console.log(passed + " tests passed.");
if (process.exitCode) process.exit(process.exitCode);