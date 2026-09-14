# Snake & Apple Game 🐍🍎

A fun, colourful Snake game made with Python and Tkinter.
Made for a **Class 4 school project** — it is easy to play and easy to understand!

## NEW: Play with your finger! ✋

Choose **FINGER** control and move your **index finger in front of the webcam**
to steer the snake:

- Move your finger **up** → the snake goes **UP**
- Move your finger **down** → the snake goes **DOWN**
- Move your finger **left** → the snake goes **LEFT**
- Move your finger **right** → the snake goes **RIGHT**

The snake follows the **direction you move your finger**, not where the finger is.
Jitter is filtered out, and the keyboard always works as a fallback.

---

## About the Project

This is a classic **Snake game**. You control a green snake on a big board.
There is a red apple 🍎 on the board. Move the snake with the **arrow keys**
(or with your **finger**) to eat the apple. Every time you eat an apple:

- Your **score goes up by 1**.
- The snake **gets longer**.
- A **new apple** appears somewhere else.

The game ends if the snake hits a **wall** or **its own body**.
Try to get the **highest score** you can!

---

## Features

- 🐍 Smooth snake movement
- 🍎 Apple collection
- ⭐ Score counter
- 🏆 High score (saved to `highscore.txt`)
- 🚀 Three levels: Easy, Medium, Fast
- ⏸️ Pause (press **P**)
- 🔄 Restart (press **R**)
- 💥 Game Over screen with PLAY AGAIN
- ⌨️ Keyboard controls (always work)
- ✋ **Finger control with webcam** (OpenCV + MediaPipe)
- 📷 Optional camera preview window with hand skeleton + direction arrow
- 🎨 Colourful child-friendly screens
- 🔉 Simple sound effects (safe if no sound)
- ✨ Fun messages like “Yummy! 😋” and “LEVEL UP!”

---

## How to Run

Make sure you have **Python 3** installed on your computer.

Open a terminal (Command Prompt) in the `Snake_Apple_Game` folder and type:

```bash
python snake_apple.py
```

### FINGER control needs two extra libraries (install once):

```bash
pip install opencv-python mediapipe
```

The first time you play in FINGER mode, the game downloads a small free hand
model file (`hand_landmarker.task`) from Google. This only happens once.

> If the webcam is missing, busy or fails, the game **does not crash** — it
> automatically keeps playing with the keyboard and shows a message.

---

## How to Play

Choosing control on the start screen:

- **⌨️ KEYBOARD** — use the arrow keys (or press **K**)
- **✋ FINGER** — move your index finger in front of the webcam (or press **F**)
- Press **SPACE** or the **START GAME** button to begin.

In game:

- ⬆️ **Up arrow** — move up
- ⬇️ **Down arrow** — move down
- ⬅️ **Left arrow** — move left
- ➡️ **Right arrow** — move right
- **P** — Pause / Resume
- **R** — Restart
- **Esc** — Exit

**Rules:**
1. Eat the apple to score 1 point.
2. Do not hit the wall.
3. Do not hit your own body.

---

## Troubleshooting

- **Finger control does not respond** → make sure a “Finger Control Camera”
  preview window is open, your hand is clearly visible, and you move your
  index finger by more than ~30 pixels. If the arrow keys stopped working,
  click on the game window first.
- **“Webcam unavailable” message** → the camera is in use by another program,
  or you have no webcam. Close other apps and press **R** to restart, or just
  play with the keyboard.
- **Hand model missing / download fails** → check your internet once, or run
  `python finger_controller.py` which re-downloads the model.
- To tune sensitivity, edit the values at the top of `finger_controller.py`:
  `FINGER_MOVE_THRESHOLD`, `DIRECTION_COOLDOWN`, `SMOOTHING_FACTOR`.
- Set `SHOW_CAMERA = False` to turn off the preview window.

---

## Python Concepts Used

This project teaches these beginner Python ideas:

- **Variables** — to store the score, speed, and snake position
- **Functions** — like `move_snake()` and `eat_apple()`
- **Lists** — the snake is a list of blocks
- **If statements** — to check collisions and directions
- **Random numbers** — to place the apple
- **Keyboard events** — to read arrow key presses
- **Tkinter Canvas** — to draw the snake, apple, and messages
- **Loops / Timers** — `after()` keeps the game moving
- **Collision detection** — checking the wall and snake body

---

## What Students Learn

Building this game teaches:

- Programming logic and problem solving
- Working with coordinates on a screen
- Reading keyboard input
- Using conditions (if / else)
- Random positions
- Keeping score
- Game design ideas

---

## How I Made My Game

Here is a simple 8-step explanation you can say during your school presentation:

1. I created the game window using Python Tkinter.
2. I created a snake using small blocks (a list of squares).
3. I used the keyboard arrow keys to move the snake.
4. I created an apple at a random position on the board.
5. When the snake touches the apple, the score increases by 1.
6. The snake grows longer after eating the apple.
7. I added collision detection for the wall and the snake body.
8. When the snake crashes, the game ends and shows a Game Over screen.

---

## Project Files

```
Snake_Apple_Game/
│
├── snake_apple.py        # The main game program
├── finger_controller.py  # Webcam finger tracking (OpenCV + MediaPipe)
├── hand_landmarker.task  # Google hand model (downloaded automatically once)
├── highscore.txt        # Saves your best score (created automatically)
└── README.md            # This file
```

Enjoy the game! 🐍🍎
