# 🐍 Snake & Apple — Playable Web Game with Finger Control

A classic **Snake game** built with HTML5 Canvas + pure JavaScript, inspired
by the original Python/Tkinter version in `python-game/`.

## NEW: steer the snake with your finger ✋

Choose **FINGER** control on the start screen, allow your webcam, then
move your **index finger up / down / left / right** to steer the snake.
The camera preview shows your hand skeleton, fingertip, and direction.

> The keyboard **always** works as a fallback — even in finger mode.

### How it works (client-side only, no server needed)

- Uses **MediaPipe Tasks Vision** (`HandLandmarker`) loaded from a CDN to
  find your index finger tip in the webcam every frame.
- A pure `FingerDirectionDetector` (same math as the Python version)
  measures the **motion vector** of the fingertip and emits a direction.
- Threshold, smoothing, cooldown, and the classic no-reversal rule all
  prevent jittery or accidental turns.

---

## How to run locally

You need **Node.js 14+** (just to run the tests — the game itself is
a pure static website).

```bash
# serve the folder on http://localhost:3000
npx http-server . -p 3000
# then open http://localhost:3000 in Chrome / Edge / Firefox
```

> Finger control **requires HTTPS** (browsers block camera on plain HTTP).
> Vercel / GitHub Pages / any HTTPS host will work. If you must test
> locally, use a self-signed cert or a service like ngrok.

Run the tests:

```bash
node tests/logic.test.js   # 15 tests: snake engine + finger direction
```

---

## Deploy to Vercel

```bash
npm i -g vercel          # install once
vercel login
vercel --prod --yes      # deploy the current folder
```

---

## Project files

```
stem-controller/
├── index.html              # game UI (start, instructions, board)
├── style.css               # dark-blue / gold theme (same palette as the Python game)
├── game-logic.js           # pure Snake engine (eat, grow, collide, reverse-block)
├── finger-control.js       # pure finger direction detector
├── mediapipe-finger.js     # camera + MediaPipe Hands wrapper
├── app.js                  # frontend wiring (screens, keyboard, finger poll, draw)
├── tests/logic.test.js     # node unit tests (snake + finger)
├── python-game/            # the original Python/Tkinter game (for reference)
│   ├── snake_apple.py
│   ├── finger_controller.py
│   └── README.md
└── README.md
```

---

## Controls

| Input        | Action                              |
|-------------|--------------------------------------|
| ↑ ↓ ← →    | move the snake                       |
| P           | pause / resume                        |
| R           | restart                               |
| Esc         | back to menu                          |
| SPACE       | start the game                        |
| F / K       | choose FINGER / KEYBOARD control     |

---

## Troubleshooting

- **Finger control does not respond** → allow camera permissions, make sure
  a preview window is open, and move your finger by at least 30 pixels.
  If the page was opened over plain HTTP (`http://...`) the browser will
  block the camera — use HTTPS instead.
- **Camera unavailable** → close other apps using the camera, refresh the
  page, and re-allow permissions. The keyboard always works as a fallback.
- To tune finger sensitivity, edit the constants at the top of
  `finger-control.js`: `threshold`, `cooldown`, `smoothing`.
- The MediaPipe hand model is loaded from Google's CDN; it needs internet
  access once when the game first loads.