"""
Screen Ruler — click and drag anywhere to measure a screen region.

Controls:
  Left-click drag  — draw a measurement rectangle
  ESC              — quit
  R                — reset / clear current selection

Output:
  Prints x, y, width, height to stdout on mouse release.
  Also copies the result to clipboard (if pyperclip is available).
"""

import tkinter as tk
import sys


def copy_to_clipboard(root: tk.Tk, text: str) -> bool:
    try:
        root.clipboard_clear()
        root.clipboard_append(text)
        root.update()
        return True
    except Exception:
        return False


def run_ruler() -> None:
    root = tk.Tk()
    root.title("Screen Ruler")

    # Fullscreen transparent overlay
    root.attributes("-fullscreen", True)
    root.attributes("-alpha", 0.25)
    root.attributes("-topmost", True)
    root.configure(bg="black")
    root.overrideredirect(True)

    screen_w = root.winfo_screenwidth()
    screen_h = root.winfo_screenheight()

    canvas = tk.Canvas(root, bg="black", cursor="crosshair", highlightthickness=0)
    canvas.pack(fill=tk.BOTH, expand=True)

    # State
    state = {"x0": 0, "y0": 0, "rect": None, "label": None, "done": False}

    RECT_COLOR = "#00FF88"
    TEXT_BG = "#111111"
    TEXT_FG = "#00FF88"
    FONT = ("Consolas", 13, "bold")

    def clear_canvas() -> None:
        if state["rect"]:
            canvas.delete(state["rect"])
            state["rect"] = None
        if state["label"]:
            canvas.delete(state["label"])
            state["label"] = None

    def on_press(event: tk.Event) -> None:
        state["done"] = False
        clear_canvas()
        state["x0"] = event.x
        state["y0"] = event.y

    def on_drag(event: tk.Event) -> None:
        x0, y0 = state["x0"], state["y0"]
        x1, y1 = event.x, event.y
        w = abs(x1 - x0)
        h = abs(y1 - y0)

        clear_canvas()

        state["rect"] = canvas.create_rectangle(
            x0, y0, x1, y1,
            outline=RECT_COLOR, width=2, dash=(6, 3),
        )

        label_text = f" {w} x {h} px "
        lx = min(x0, x1)
        ly = min(y0, y1) - 22
        if ly < 4:
            ly = max(y0, y1) + 4

        state["label"] = canvas.create_text(
            lx, ly,
            text=label_text,
            anchor="nw",
            fill=TEXT_FG,
            font=FONT,
        )

    def on_release(event: tk.Event) -> None:
        x0, y0 = state["x0"], state["y0"]
        x1, y1 = event.x, event.y

        rx = min(x0, x1)
        ry = min(y0, y1)
        w = abs(x1 - x0)
        h = abs(y1 - y0)

        if w == 0 or h == 0:
            return

        result = f"x={rx}, y={ry}, width={w}, height={h}"
        print(result)

        copied = copy_to_clipboard(root, result)

        # Update label to show final result + clipboard status
        if state["label"]:
            canvas.delete(state["label"])

        suffix = "  [copied]" if copied else ""
        label_text = f" {w} x {h} px  |  x={rx}, y={ry}{suffix} "
        lx = min(x0, x1)
        ly = min(y0, y1) - 22
        if ly < 4:
            ly = max(y0, y1) + 4

        state["label"] = canvas.create_text(
            lx, ly,
            text=label_text,
            anchor="nw",
            fill=TEXT_FG,
            font=FONT,
        )
        state["done"] = True

    def on_key(event: tk.Event) -> None:
        if event.keysym == "Escape":
            root.destroy()
            sys.exit(0)
        elif event.keysym.lower() == "r":
            clear_canvas()

    canvas.bind("<ButtonPress-1>", on_press)
    canvas.bind("<B1-Motion>", on_drag)
    canvas.bind("<ButtonRelease-1>", on_release)
    root.bind("<Key>", on_key)
    root.focus_force()

    # Instruction label (bottom-centre, always visible)
    canvas.create_text(
        screen_w // 2,
        screen_h - 24,
        text="Click and drag to measure  |  ESC to quit  |  R to reset",
        fill="#AAAAAA",
        font=("Consolas", 11),
    )

    root.mainloop()


if __name__ == "__main__":
    run_ruler()
