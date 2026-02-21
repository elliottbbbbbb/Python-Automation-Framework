from __future__ import annotations

import logging
import threading
from typing import Callable, List, Optional, Tuple

import cv2 as cv
import numpy as np
from PIL import Image, ImageTk
import tkinter as tk

logger = logging.getLogger(__name__)

OverlayCallback = Callable[[np.ndarray], np.ndarray]


class LiveViewService:
    """
    Floating window that mirrors the OSRS game client in real-time.

    Runs a tkinter event loop in a background daemon thread (safe on Windows).
    Detection overlays are registered via register_overlay() and drawn on top
    of each captured frame before display.

    Overlay callbacks follow the pattern: (bgr_frame: np.ndarray) -> np.ndarray
    They read from already-cached detection state — zero extra detection cost.
    Future systems (pathfinding, combat targeting, etc.) register their own
    callbacks with no changes needed here.
    """

    def __init__(self, screen_service, fps: int = 10) -> None:
        """
        Args:
            screen_service: ScreenService instance for raw frame capture.
            fps: Target refresh rate for the viewer window.
        """
        self._screen = screen_service
        self._fps = fps

        self._overlays: List[Tuple[str, OverlayCallback]] = []
        self._overlay_lock = threading.Lock()

        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._root: Optional[tk.Tk] = None

    # ==================== Overlay Registry ====================

    def register_overlay(self, name: str, callback: OverlayCallback) -> None:
        """
        Register (or replace) a named overlay callback.

        Callbacks are applied in registration order.  Each receives the current
        BGR frame (after all previous overlays) and must return the annotated frame.
        Thread-safe — can be called from any thread while the viewer is running.

        Args:
            name: Unique identifier (used for unregistration / replacement).
            callback: ``(bgr_frame: np.ndarray) -> np.ndarray``
        """
        with self._overlay_lock:
            self._overlays = [(n, cb) for n, cb in self._overlays if n != name]
            self._overlays.append((name, callback))
        logger.debug(f"LiveViewService: registered overlay '{name}'")

    def unregister_overlay(self, name: str) -> None:
        """Remove an overlay callback by name.  Thread-safe."""
        with self._overlay_lock:
            self._overlays = [(n, cb) for n, cb in self._overlays if n != name]
        logger.debug(f"LiveViewService: unregistered overlay '{name}'")

    # ==================== Lifecycle ====================

    def start(self) -> None:
        """Start the background display thread."""
        if self._thread and self._thread.is_alive():
            logger.warning("LiveViewService is already running")
            return
        self._stop_event.clear()
        self._thread = threading.Thread(
            target=self._run_loop,
            daemon=True,
            name="LiveViewThread",
        )
        self._thread.start()
        logger.info(f"LiveViewService started at {self._fps} FPS")

    def stop(self) -> None:
        """Signal the thread to stop and close the viewer window."""
        self._stop_event.set()
        if self._root is not None:
            try:
                self._root.quit()
            except Exception:
                pass
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=3.0)
        logger.info("LiveViewService stopped")

    # ==================== Tkinter Display Loop ====================

    def _run_loop(self) -> None:
        """
        Run a standalone tkinter window in this background thread.

        On Windows, each thread can safely own its own tk.Tk() instance,
        making this the most reliable display approach for background threads.
        """
        try:
            self._root = tk.Tk()
            self._root.title("Bot Vision")
            self._root.geometry("800x600")
            # Keep window open while bot is running; ignore the X button
            self._root.protocol("WM_DELETE_WINDOW", lambda: None)

            self._label = tk.Label(self._root, bg="black")
            self._label.pack(fill=tk.BOTH, expand=True)

            self._schedule_update()
            self._root.mainloop()
        except Exception:
            logger.error("LiveViewService display loop failed", exc_info=True)
        finally:
            self._root = None

    def _schedule_update(self) -> None:
        """Capture one frame, apply overlays, display — then schedule the next tick."""
        if self._stop_event.is_set():
            self._root.destroy()
            return

        try:
            pil_img = self._screen.capture(region=None)
            if pil_img is not None:
                # Convert PIL (RGB) → numpy BGR for overlay callbacks
                img_rgb = np.array(pil_img)
                frame_bgr = cv.cvtColor(img_rgb, cv.COLOR_RGB2BGR)

                # Snapshot overlay list without holding the lock during callbacks
                with self._overlay_lock:
                    overlays_snapshot = list(self._overlays)

                for name, callback in overlays_snapshot:
                    try:
                        result = callback(frame_bgr)
                        if result is not None:
                            frame_bgr = result
                    except Exception:
                        logger.error(f"Overlay '{name}' callback raised", exc_info=True)

                # Convert BGR → RGB → PIL → PhotoImage for tkinter
                frame_rgb = cv.cvtColor(frame_bgr, cv.COLOR_BGR2RGB)
                pil_display = Image.fromarray(frame_rgb)

                # Scale to current window size
                w = max(self._root.winfo_width(), 1)
                h = max(self._root.winfo_height(), 1)
                pil_display = pil_display.resize((w, h), Image.NEAREST)

                photo = ImageTk.PhotoImage(pil_display)
                self._label.configure(image=photo)
                self._label.image = photo  # hold reference to prevent GC
        except Exception:
            logger.error("LiveViewService frame update failed", exc_info=True)

        # Schedule next update via tkinter's event loop (thread-safe within the same thread)
        self._root.after(int(1000 / self._fps), self._schedule_update)
