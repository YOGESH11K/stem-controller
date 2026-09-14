/*
 * SNAKE GAME LOGIC (pure, works in browser and Node)
 * ------------------------------------------------------------------
 * The classic Snake rules, kept identical to the original Python game:
 *   - eat the apple to score 1 and grow
 *   - die when hitting a wall or your own body
 *   - you can never instantly reverse directions
 */
(function () {
  "use strict";

  var OPPOSITE = { up: "down", down: "up", left: "right", right: "left" };

  function SnakeEngine(opts) {
    this.cols = opts.cols;
    this.rows = opts.rows;
    this.startLength = opts.startLength || 3;
    this.reset();
  }

  SnakeEngine.prototype.reset = function () {
    var cx = Math.floor(this.cols / 2);
    var cy = Math.floor(this.rows / 2);
    this.snake = [];
    for (var i = 0; i < this.startLength; i++) {
      this.snake.push({ x: cx - i, y: cy });
    }
    this.direction = "right";
    this.nextDirection = "right";
    this.score = 0;
    this.placeApple();
  };

  SnakeEngine.prototype.placeApple = function () {
    var taken = {};
    for (var i = 0; i < this.snake.length; i++) {
      taken[this.snake[i].x + "," + this.snake[i].y] = true;
    }
    var free = [];
    for (var x = 0; x < this.cols; x++) {
      for (var y = 0; y < this.rows; y++) {
        if (!taken[x + "," + y]) free.push({ x: x, y: y });
      }
    }
    this.apple = free.length ? free[Math.floor(Math.random() * free.length)] : null;
  };

  SnakeEngine.prototype.changeDirection = function (dir) {
    if (dir !== OPPOSITE[this.direction]) this.nextDirection = dir;
  };

  /*
   * Move one step. Returns { gameOver, ate }.
   */
  SnakeEngine.prototype.step = function () {
    this.direction = this.nextDirection;
    var head = this.snake[0];
    var nx = head.x;
    var ny = head.y;
    if (this.direction === "up") ny -= 1;
    else if (this.direction === "down") ny += 1;
    else if (this.direction === "left") nx -= 1;
    else if (this.direction === "right") nx += 1;

    if (nx < 0 || nx >= this.cols || ny < 0 || ny >= this.rows) {
      return { gameOver: true, ate: false };
    }
    for (var i = 0; i < this.snake.length; i++) {
      if (this.snake[i].x === nx && this.snake[i].y === ny) {
        return { gameOver: true, ate: false };
      }
    }

    this.snake.unshift({ x: nx, y: ny });
    var ate = false;
    if (this.apple && nx === this.apple.x && ny === this.apple.y) {
      this.score += 1;
      ate = true;
      this.placeApple();
    } else {
      this.snake.pop();
    }
    return { gameOver: false, ate: ate };
  };

  if (typeof module !== "undefined" && module.exports) {
    module.exports = { SnakeEngine: SnakeEngine };
  } else {
    window.SnakeEngine = SnakeEngine;
  }
})();