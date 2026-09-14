"""
SNAKE & APPLE - Python Game
===========================
A fun and colourful Snake game made for Class 4 students.

Move the snake with the arrow keys and eat apples to grow and score!
This game uses only Python's standard library (Tkinter).
No internet, no downloads, no API keys needed.
"""

import tkinter as tk
import random
import os

# ============================================================
# OPTIONAL FINGER CONTROL (webcam + MediaPipe)
# ------------------------------------------------------------
# If opencv + mediapipe are installed we can also drive the snake
# by moving your index finger in front of the webcam. If they are
# missing, the keyboard still works perfectly fine.
# ============================================================
try:
    from finger_controller import FingerController
    FINGER_CONTROL_AVAILABLE = True
except Exception:
    FingerController = None
    FINGER_CONTROL_AVAILABLE = False

FINGER_POLL_MS = 50      # how often the game checks the finger direction
DEBUG_MODE = False       # print extra debug info to the console

# ============================================================
# GAME SETTINGS
# ============================================================
GRID_SIZE = 20          # Each block is 20 pixels wide and tall
BOARD_WIDTH = 600        # Game board width in pixels
BOARD_HEIGHT = 400       # Game board height in pixels

# Number of cells across and down (600 / 20 = 30, 400 / 20 = 20)
COLS = BOARD_WIDTH // GRID_SIZE
ROWS = BOARD_HEIGHT // GRID_SIZE

# Speed in milliseconds between each snake move. Smaller = faster.
BASE_SPEED = 150

# Snake starts with 3 segments
START_LENGTH = 3

# File that remembers the high score
HIGHSCORE_FILE = "highscore.txt"


# ============================================================
# MAIN GAME CLASS
# ============================================================
class SnakeGame:
    """The main Snake game. Handles all the game logic,
    drawing, keyboard controls and collisions."""

    def __init__(self):
        """Set up the main window and all the screens."""
        # ---- Create the main window ----
        self.root = tk.Tk()
        self.root.title("🐍 Snake & Apple 🍎")
        self.root.resizable(False, False)

        # ---- Game state variables ----
        self.snake = []          # List of (x, y) blocks that make the snake
        self.direction = "right" # Current moving direction
        self.next_direction = "right"  # Direction we will use on the next move
        self.apple = None        # Apple position (x, y)
        self.score = 0           # Current score
        self.high_score = 0      # Best score this session
        self.running = False     # Is the game currently moving?
        self.paused = False      # Is the game paused?
        self.game_speed = BASE_SPEED  # Current speed between moves

        # ---- Finger control state ----
        self.control_mode = "keyboard"       # "keyboard" or "finger"
        self.finger_controller = None        # FingerController instance (if available)
        self._finger_polling = False         # Is the finger poll timer on?
        self._poll_after_id = None           # Tk 'after' ID for the finger poll
        self._last_status_text = None        # Cached controls label text
        if FINGER_CONTROL_AVAILABLE:
            self.finger_controller = FingerController(debug=DEBUG_MODE)

        # ---- Load the saved high score (if any) ----
        self.load_high_score()

        # ---- Build the screens ----
        self.build_start_screen()
        self.build_game_screen()
        self.build_instructions_screen()

        # Make sure closing the window stops the webcam cleanly
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

        # ---- Show the start screen first ----
        self.show_start_screen()

    # ============================================================
    # HIGH SCORE (FILE SAVING)
    # ============================================================
    def load_high_score(self):
        """Read the high score from highscore.txt.
        Handles missing or broken files safely."""
        try:
            if os.path.exists(HIGHSCORE_FILE):
                with open(HIGHSCORE_FILE, "r") as file:
                    value = file.read().strip()
                    # Only use it if it is a whole number
                    if value.isdigit():
                        self.high_score = int(value)
                    else:
                        self.high_score = 0
            else:
                self.high_score = 0
        except Exception:
            # If anything goes wrong, just start from zero
            self.high_score = 0

    def save_high_score(self):
        """Save the high score to highscore.txt."""
        try:
            with open(HIGHSCORE_FILE, "w") as file:
                file.write(str(self.high_score))
        except Exception:
            # If we cannot save, we do not want the game to crash
            pass

    # ============================================================
    # SCREENS / UI BUILDING
    # ============================================================
    def build_start_screen(self):
        """Build the start menu screen."""
        self.start_frame = tk.Frame(self.root, bg="#1b2a4a")
        self.start_frame.pack(fill="both", expand=True)

        tk.Label(self.start_frame, text="🐍🍎", font=("Arial", 56),
                 bg="#1b2a4a", fg="#ffd166").pack(pady=(50, 0))
        tk.Label(self.start_frame, text="SNAKE & APPLE", font=("Arial", 34, "bold"),
                 bg="#1b2a4a", fg="#ffd166").pack(pady=10)
        tk.Label(self.start_frame, text="Can you eat all the apples?",
                 font=("Arial", 15), bg="#1b2a4a", fg="#8ecae6").pack(pady=5)

        tk.Button(self.start_frame, text="▶ START GAME", font=("Arial", 16, "bold"),
                  bg="#4caf50", fg="white", activebackground="#388e3c",
                  padx=25, pady=8, command=self.start_game_from_button)\
            .pack(pady=12)

        # ---- Choose how to control the snake ----
        tk.Label(self.start_frame, text="🎮 Choose Control:",
                 font=("Arial", 14, "bold"), bg="#1b2a4a", fg="#8ecae6")\
            .pack(pady=(12, 2))

        ctrl_row = tk.Frame(self.start_frame, bg="#1b2a4a")
        ctrl_row.pack(pady=4)
        self.keyboard_btn = tk.Button(ctrl_row, text="⌨️ KEYBOARD",
                                      font=("Arial", 13, "bold"), bg="#2196f3",
                                      fg="white", activebackground="#1976d2",
                                      padx=18, pady=5,
                                      command=lambda: self.set_control_mode("keyboard"))
        self.finger_btn = tk.Button(ctrl_row, text="✋ FINGER",
                                    font=("Arial", 13, "bold"), bg="#ff9800",
                                    fg="white", activebackground="#ef6c00",
                                    padx=24, pady=5,
                                    command=lambda: self.set_control_mode("finger"))
        self.keyboard_btn.pack(side="left", padx=8)
        self.finger_btn.pack(side="left", padx=8)

        if not FINGER_CONTROL_AVAILABLE:
            self.finger_btn.config(state="disabled", text="✋ FINGER (not installed)")

        self.control_label = tk.Label(self.start_frame,
                                      text="Control: ⌨️ KEYBOARD",
                                      font=("Arial", 13, "bold"),
                                      bg="#1b2a4a", fg="#ffffff")
        self.control_label.pack(pady=6)

        tk.Label(self.start_frame, text="Tip: Move your index finger up / down / "
                                        "left / right to steer.",
                 font=("Arial", 10), bg="#1b2a4a", fg="#8ecae6").pack(pady=(2, 4))
        tk.Label(self.start_frame, text="Press SPACE to start",
                 font=("Arial", 12, "bold"), bg="#1b2a4a", fg="#ffd166").pack()

        tk.Button(self.start_frame, text="❓ HOW TO PLAY", font=("Arial", 14),
                  bg="#2196f3", fg="white", activebackground="#1976d2",
                  padx=20, pady=6, command=self.show_instructions)\
            .pack(pady=6)
        tk.Button(self.start_frame, text="❌ EXIT", font=("Arial", 14),
                  bg="#e53935", fg="white", activebackground="#c62828",
                  padx=20, pady=6, command=self._on_close)\
            .pack(pady=6)

        # ---- Keyboard shortcuts on this screen ----
        self.root.unbind("<space>")
        self.root.unbind("<Key-k>")
        self.root.unbind("<Key-f>")
        self.root.bind("<space>", self._start_game_key)
        self.root.bind("<Key-k>", lambda e: self.set_control_mode("keyboard"))
        self.root.bind("<Key-f>", lambda e: self.set_control_mode("finger"))

        # Start with keyboard selected
        self.set_control_mode("keyboard")

    def build_instructions_screen(self):
        """Build the How To Play screen."""
        self.instructions_frame = tk.Frame(self.root, bg="#1b2a4a")
        self.instructions_frame.pack(fill="both", expand=True)

        tk.Label(self.instructions_frame, text="HOW TO PLAY",
                 font=("Arial", 30, "bold"), bg="#1b2a4a", fg="#ffd166")\
            .pack(pady=(30, 15))

        lines = [
            "🐍 Move the snake using the Arrow Keys.",
            "✋ Or choose FINGER control and move your index finger in front of the webcam.",
            "      Move it up / down / left / right to steer the snake.",
            "🍎 Eat the apples to increase your score.",
            "📈 Your snake grows when it eats an apple.",
            "💥 Do not hit the walls.",
            "💥 Do not hit your own body.",
            "⌨️ Keyboard always works, even in FINGER mode.",
            "⏸️ Press P to pause.",
            "🔄 Press R to restart.",
        ]
        for line in lines:
            tk.Label(self.instructions_frame, text=line, font=("Arial", 13),
                     bg="#1b2a4a", fg="#ffffff", anchor="w").pack(pady=2)

        tk.Label(self.instructions_frame, text="Try to get the highest score!",
                 font=("Arial", 15, "bold"), bg="#1b2a4a", fg="#8ecae6")\
            .pack(pady=(15, 10))

        tk.Button(self.instructions_frame, text="← BACK", font=("Arial", 14, "bold"),
                  bg="#ff9800", fg="white", activebackground="#ef6c00",
                  padx=25, pady=6, command=self.show_start_screen)\
            .pack(pady=10)

    def build_game_screen(self):
        """Build the main game screen with score, board and controls."""
        self.game_frame = tk.Frame(self.root, bg="#1b2a4a")
        self.game_frame.pack(fill="both", expand=True)

        # ---- Top bar with title and score ----
        tk.Label(self.game_frame, text="🐍 SNAKE & APPLE 🍎",
                 font=("Arial", 26, "bold"), bg="#1b2a4a", fg="#ffd166")\
            .pack(pady=(10, 0))

        self.score_label = tk.Label(self.game_frame, text="Score: 0",
                                    font=("Arial", 18, "bold"),
                                    bg="#1b2a4a", fg="#ffffff")
        self.score_label.pack()

        self.high_label = tk.Label(self.game_frame, text=f"🏆 High Score: {self.high_score}",
                                   font=("Arial", 16, "bold"),
                                   bg="#1b2a4a", fg="#ffd166")
        self.high_label.pack()

        self.level_label = tk.Label(self.game_frame, text="Level: Easy",
                                    font=("Arial", 14, "bold"),
                                    bg="#1b2a4a", fg="#8ecae6")
        self.level_label.pack()

        # ---- The game board (canvas) ----
        self.canvas = tk.Canvas(self.game_frame, width=BOARD_WIDTH,
                                height=BOARD_HEIGHT, bg="#2d6a4f",
                                highlightthickness=3,
                                highlightbackground="#ffd166")
        self.canvas.pack(pady=8)

        # ---- Controls message below the board ----
        self.controls_label = tk.Label(self.game_frame,
                                       text="Use Arrow Keys to Move   |   P = Pause   |   "
                                            "R = Restart   |   Esc = Exit",
                                       font=("Arial", 11), bg="#1b2a4a", fg="#8ecae6")
        self.controls_label.pack(pady=(2, 8))

        # ---- Bind keyboard keys ----
        self.root.bind("<KeyPress>", self.key_pressed)

        # Make sure the window can receive keyboard events
        self.root.focus_set()

    # ============================================================
    # SCREEN SWITCHING
    # ============================================================
    def show_start_screen(self):
        """Stop the game and show the start menu."""
        self.stop_game()
        self.instructions_frame.pack_forget()
        self.game_frame.pack_forget()
        self.start_frame.pack(fill="both", expand=True)

    def show_instructions(self):
        """Show the How To Play screen."""
        self.stop_game()
        self.start_frame.pack_forget()
        self.game_frame.pack_forget()
        self.instructions_frame.pack(fill="both", expand=True)

    def start_game_from_button(self):
        """Called when the START button is pressed."""
        self.start_frame.pack_forget()
        self.instructions_frame.pack_forget()
        self.game_frame.pack(fill="both", expand=True)
        self.reset_game()
        self.running = True
        self._setup_control()
        self.move_snake()

    # ============================================================
    # GAME LIFE CYCLE
    # ============================================================
    def stop_game(self):
        """Stop the game loop completely."""
        # Stop the webcam finger controller and the finger poll timer
        self._stop_finger_controller()
        self.running = False
        self.paused = False
        # Cancel any waiting 'after' callbacks
        try:
            self.root.after_cancel(self.after_id)
        except Exception:
            pass

    def reset_game(self):
        """Reset the snake, score, apple and redraw the board."""
        # Cancel old timer
        try:
            self.root.after_cancel(self.after_id)
        except Exception:
            pass

        # Reset the snake to start in the middle, moving right
        center_x = COLS // 2
        center_y = ROWS // 2
        self.snake = []
        for i in range(START_LENGTH):
            self.snake.append((center_x - i, center_y))

        self.direction = "right"
        self.next_direction = "right"
        self.score = 0
        self.paused = False
        self.running = False  # The caller will set running = True
        self.game_speed = BASE_SPEED

        # Update the level and score labels
        self.update_score_display()
        self.update_level()

        # Clear the canvas and draw everything fresh
        self.canvas.delete("all")
        self.create_apple()
        self.draw_snake()
        self.draw_apple()
        self.draw_level_banner("GO! 🐍")

    # ============================================================
    # APPLE
    # ============================================================
    def create_apple(self):
        """Put a new apple at a random empty cell."""
        while True:
            x = random.randint(0, COLS - 1)
            y = random.randint(0, ROWS - 1)
            # Only accept a position that is not on the snake
            if (x, y) not in self.snake:
                self.apple = (x, y)
                break

    def draw_apple(self):
        """Draw the apple as a red circle with a green leaf."""
        x, y = self.apple
        px = x * GRID_SIZE
        py = y * GRID_SIZE
        size = GRID_SIZE

        # Red apple body
        self.canvas.create_oval(px + 2, py + 3, px + size - 2, py + size - 2,
                                fill="#e53935", outline="#b71c1c", width=2)
        # Green leaf on top
        self.canvas.create_oval(px + size // 2 - 6, py - 4, px + size // 2 + 4, py + 6,
                                fill="#66bb6a", outline="#2e7d32", width=1)

    # ============================================================
    # SNAKE
    # ============================================================
    def draw_snake(self):
        """Draw the whole snake. The head looks different from the body."""
        for index, (x, y) in enumerate(self.snake):
            px = x * GRID_SIZE
            py = y * GRID_SIZE
            size = GRID_SIZE
            if index == 0:
                # The head is a bright colour with a white eye
                self.canvas.create_oval(px + 1, py + 1, px + size - 1, py + size - 1,
                                        fill="#4caf50", outline="#1b5e20", width=2)
                # A little white eye on the head
                self.canvas.create_oval(px + 6, py + 6, px + 10, py + 10,
                                        fill="white", outline="#1b5e20")
                self.canvas.create_oval(px + 7, py + 7, px + 9, py + 9,
                                        fill="#1b5e20")
            else:
                # The body is a lighter green with a dark outline
                self.canvas.create_rectangle(px + 1, py + 1, px + size - 1, py + size - 1,
                                             fill="#66bb6a", outline="#2e7d32",
                                             width=1)

    # ============================================================
    # MOVEMENT AND GAME LOOP
    # ============================================================
    def change_direction(self, new_dir):
        """Change the direction the snake wants to go, if allowed."""
        # Make sure the snake cannot reverse into itself
        opposite = {
            "up": "down",
            "down": "up",
            "left": "right",
            "right": "left",
        }
        if new_dir != opposite[self.direction]:
            self.next_direction = new_dir

    def move_snake(self):
        """Move the snake by one step. Called by the timer."""
        if not self.running or self.paused:
            # If paused or stopped, schedule another look and stop here
            if self.running:
                self.after_id = self.root.after(self.game_speed, self.move_snake)
            return

        # Use the new direction now
        self.direction = self.next_direction

        # Work out the new head position
        head_x, head_y = self.snake[0]
        if self.direction == "up":
            head_y -= 1
        elif self.direction == "down":
            head_y += 1
        elif self.direction == "left":
            head_x -= 1
        elif self.direction == "right":
            head_x += 1

        new_head = (head_x, head_y)

        # Check for wall or self collision BEFORE moving
        if self.check_collision(new_head):
            self.game_over()
            return

        # Add the new head at the front
        self.snake.insert(0, new_head)

        # If we ate the apple, grow (do not remove the tail)
        if new_head == self.apple:
            self.eat_apple()
        else:
            # Otherwise remove the tail so the snake stays the same length
            self.snake.pop()

        # Redraw everything
        self.canvas.delete("all")
        self.draw_snake()
        self.draw_apple()

        # Schedule the next move. Speed up naturally with the level.
        self.after_id = self.root.after(self.game_speed, self.move_snake)

    # ============================================================
    # COLLISION DETECTION
    # ============================================================
    def check_collision(self, new_head):
        """Return True if the new head hits a wall or the snake's body."""
        x, y = new_head
        # Wall collision: out of bounds
        if x < 0 or x >= COLS or y < 0 or y >= ROWS:
            return True
        # Self collision: new head lands on any body part
        if new_head in self.snake:
            return True
        return False

    # ============================================================
    # EATING APPLES / SCORING
    # ============================================================
    def eat_apple(self):
        """Handle eating an apple: score up, show message, new apple."""
        self.score += 1
        self.update_score_display()

        # Show a positive message on the board
        self.draw_message("Yummy! 😋 +1 🍎")

        # Update level (this can speed up the game)
        self.update_level()

        # Put a brand new apple on the board
        self.create_apple()

        # Optional: a cheerful "ding" sound (does nothing if sound fails)
        self.play_beep()

    def update_score_display(self):
        """Refresh the score and high score labels."""
        self.score_label.config(text=f"Score: {self.score}")
        self.high_label.config(text=f"🏆 High Score: {self.high_score}")

    def draw_message(self, text):
        """Briefly draw a message in the middle of the board."""
        self.canvas.create_text(BOARD_WIDTH // 2, BOARD_HEIGHT // 2,
                                text=text, font=("Arial", 22, "bold"),
                                fill="#ffffff", tag="message")
        # Remove it after 1 second
        self.root.after(1000, lambda: self.canvas.delete("message"))

    def draw_level_banner(self, text):
        """Draw a big banner in the middle of the board."""
        self.canvas.create_text(BOARD_WIDTH // 2, BOARD_HEIGHT // 2,
                                text=text, font=("Arial", 30, "bold"),
                                fill="#ffd166", tag="banner")
        self.root.after(1200, lambda: self.canvas.delete("banner"))

    # ============================================================
    # LEVELS / DIFFICULTY
    # ============================================================
    def update_level(self):
        """Set the level name and speed based on the score."""
        if self.score < 5:
            level = "Easy"
            self.game_speed = 150
        elif self.score < 10:
            level = "Medium"
            self.game_speed = 110
        else:
            level = "Fast"
            self.game_speed = 75

        # Only show LEVEL UP banner when we increase difficulty
        old_level = self.level_label.cget("text").replace("Level: ", "")
        if old_level != level and self.score > 0 and old_level != "Easy":
            self.draw_level_banner("🚀 LEVEL UP!")

        self.level_label.config(text=f"Level: {level}")

    # ============================================================
    # SOUND (uses only standard library, safe if it fails)
    # ============================================================
    def play_beep(self):
        """Play a short beep using the Windows 'beep' if possible.
        If sound is not available, the game keeps running normally."""
        try:
            # Prints a bell character; on many terminals/programs it beeps.
            # We wrap everything so a failure never stops the game.
            import ctypes
            ctypes.windll.kernel32.Beep(1200, 100)  # a short high beep
        except Exception:
            pass

    def play_game_over_beep(self):
        """Play a longer low beep for game over."""
        try:
            import ctypes
            ctypes.windll.kernel32.Beep(400, 300)
        except Exception:
            pass

    def play_high_score_beep(self):
        """A happy two-note beep for a new high score."""
        try:
            import ctypes
            ctypes.windll.kernel32.Beep(900, 150)
            ctypes.windll.kernel32.Beep(1400, 200)
        except Exception:
            pass

    # ============================================================
    # PAUSE
    # ============================================================
    def pause_game(self):
        """Pause or resume the game."""
        if not self.running:
            return
        if self.paused:
            self.paused = False
            self.canvas.delete("pause_text")
            # Immediately resume
            try:
                self.root.after_cancel(self.after_id)
            except Exception:
                pass
            self.after_id = self.root.after(self.game_speed, self.move_snake)
        else:
            self.paused = True
            self.canvas.create_text(BOARD_WIDTH // 2, BOARD_HEIGHT // 2,
                                    text="⏸️ GAME PAUSED", font=("Arial", 28, "bold"),
                                    fill="#ffd166", tag="pause_text")

    # ============================================================
    # GAME OVER
    # ============================================================
    def game_over(self):
        """Stop the game and show the Game Over overlay."""
        self.running = False
        self.play_game_over_beep()

        # Check if this is a new high score
        is_new_high = False
        if self.score > self.high_score:
            self.high_score = self.score
            self.save_high_score()
            self.update_score_display()
            is_new_high = True
            self.play_high_score_beep()

        # Draw the game over overlay on the canvas
        self.canvas.delete("all")
        self.draw_snake()
        self.draw_apple()
        self.canvas.create_rectangle(0, 0, BOARD_WIDTH, BOARD_HEIGHT,
                                     fill="black", stipple="gray50")
        self.canvas.create_text(BOARD_WIDTH // 2, BOARD_HEIGHT // 2 - 50,
                                text="GAME OVER!", font=("Arial", 34, "bold"),
                                fill="#e53935")
        self.canvas.create_text(BOARD_WIDTH // 2, BOARD_HEIGHT // 2,
                                text=f"Your Score: {self.score}",
                                font=("Arial", 20, "bold"), fill="#ffffff")

        if is_new_high:
            self.canvas.create_text(BOARD_WIDTH // 2, BOARD_HEIGHT // 2 + 30,
                                    text="🏆 NEW HIGH SCORE! 🏆",
                                    font=("Arial", 18, "bold"), fill="#ffd166")

        # Show the PLAY AGAIN and EXIT buttons
        play_again_btn = tk.Button(self.game_frame, text="🔄 PLAY AGAIN",
                                   font=("Arial", 14, "bold"), bg="#4caf50",
                                   fg="white", activebackground="#388e3c",
                                   padx=15, pady=6, command=self.play_again)
        exit_btn = tk.Button(self.game_frame, text="❌ EXIT", font=("Arial", 14, "bold"),
                             bg="#e53935", fg="white", activebackground="#c62828",
                             padx=15, pady=6, command=self.root.destroy)

        # Position the buttons below the canvas, next to each other
        btn_row = tk.Frame(self.game_frame, bg="#1b2a4a")
        btn_row.pack(pady=8)
        play_again_btn.pack(in_=btn_row, side="left", padx=10)
        exit_btn.pack(in_=btn_row, side="left", padx=10)
        # Remember them so we can remove them later
        self.game_over_buttons = (btn_row, play_again_btn, exit_btn)

    def play_again(self):
        """Restart the game from the current screen."""
        # Remove any game over buttons
        try:
            for widget in self.game_over_buttons:
                widget.destroy()
        except Exception:
            pass
        self.reset_game()
        self.running = True
        self.move_snake()

    # ============================================================
    # KEYBOARD CONTROLS
    # ============================================================
    def key_pressed(self, event):
        """Handle all keyboard keys the player can press."""
        key = event.keysym

        # Arrow keys control the snake (only when the game is running)
        if key == "Up":
            self.change_direction("up")
        elif key == "Down":
            self.change_direction("down")
        elif key == "Left":
            self.change_direction("left")
        elif key == "Right":
            self.change_direction("right")
        elif key.lower() == "p":
            self.pause_game()
        elif key.lower() == "r":
            # Restart during gameplay
            if self.running:
                self.play_again()
            else:
                self.start_game_from_button()
        elif key == "Escape":
            self._on_close()

    # ============================================================
    # CONTROL MODE SELECTION (start screen)
    # ============================================================
    def set_control_mode(self, mode):
        """Select KEYBOARD or FINGER control from the start screen."""
        if mode == "finger" and not FINGER_CONTROL_AVAILABLE:
            return
        self.control_mode = mode
        if mode == "finger":
            self.keyboard_btn.config(bg="#1c5982")      # dim
            self.finger_btn.config(bg="#f57c00")        # bright = selected
            self.control_label.config(text="Control: ✋ FINGER")
        else:
            self.keyboard_btn.config(bg="#1565c0")      # bright = selected
            self.finger_btn.config(bg="#b26a00")        # dim
            self.control_label.config(text="Control: ⌨️ KEYBOARD")

    def _start_game_key(self, event):
        """SPACE key starts the game from the start screen."""
        try:
            if self.start_frame.winfo_viewable():
                self.start_game_from_button()
        except Exception:
            pass

    # ============================================================
    # FINGER CONTROL (webcam) - start, poll, stop
    # ============================================================
    def _setup_control(self):
        """Called each time a game session starts. Starts the webcam
        controller if FINGER mode was chosen."""
        self._last_status_text = None
        if self.control_mode == "finger":
            if self.start_finger_controller():
                self._start_finger_polling()
            else:
                # Webcam failed -> keep playing with the keyboard
                self.controls_label.config(
                    text="⚠️ Webcam unavailable - using KEYBOARD controls  |  "
                         "P = Pause   R = Restart   Esc = Exit")

    def start_finger_controller(self):
        """Start the webcam hand tracker. Returns True if it works."""
        if self.finger_controller is None:
            return False
        if self.finger_controller.is_running():
            return True
        ok = self.finger_controller.start()
        if not ok:
            error = self.finger_controller.get_error() or "unknown error"
            print("[SnakeGame] Finger control not available:", error)
        return ok

    def _start_finger_polling(self):
        """Begin checking the finger direction every few milliseconds."""
        if self._finger_polling:
            return
        self._finger_polling = True
        self._poll_finger_controller()

    def _stop_finger_polling(self):
        """Stop checking the finger direction."""
        self._finger_polling = False
        if self._poll_after_id is not None:
            try:
                self.root.after_cancel(self._poll_after_id)
            except Exception:
                pass
            self._poll_after_id = None

    def _stop_finger_controller(self):
        """Stop the webcam tracker and the poll timer."""
        self._stop_finger_polling()
        if self.finger_controller is not None:
            try:
                self.finger_controller.stop()
            except Exception:
                pass
        self._last_status_text = None

    def _poll_finger_controller(self):
        """Tick the finger controller: apply any new direction and show status."""
        if not self._finger_polling:
            return
        controller = self.finger_controller
        if controller is not None and controller.is_available():
            direction = controller.get_direction()
            if direction:
                self.change_direction(direction)
            self._update_hand_status()
        self._poll_after_id = self.root.after(FINGER_POLL_MS, self._poll_finger_controller)

    def _update_hand_status(self):
        """Keep the controls label up to date with the hand status."""
        controller = self.finger_controller
        if controller is None:
            return
        hand = "HAND: DETECTED ✅" if controller.is_hand_detected() else "HAND: looking..."
        direction = controller.get_last_direction()
        finger_dir = direction.upper() if direction else "—"
        text = (f"{hand}  |  Finger: {finger_dir}  |  P = Pause   R = Restart   "
                f"Esc = Exit")
        if text != self._last_status_text:
            self._last_status_text = text
            self.controls_label.config(text=text)
            if DEBUG_MODE:
                info = controller.get_debug_info()
                print("Hand: {} | Finger: {} | dx: {:.1f} | dy: {:.1f}".format(
                    info["hand"], finger_dir, info["dx"], info["dy"]))

    def _on_close(self):
        """Clean shutdown when the window is closed."""
        self._stop_finger_controller()
        try:
            self.root.destroy()
        except Exception:
            pass

    # ============================================================
    # RUN
    # ============================================================
    def run(self):
        """Start the Tkinter event loop."""
        try:
            self.root.mainloop()
        finally:
            # In case the window was closed some other way, make sure
            # the webcam is released before the program exits.
            self._stop_finger_controller()


# ============================================================
# START THE GAME
# ============================================================
if __name__ == "__main__":
    game = SnakeGame()
    game.run()
