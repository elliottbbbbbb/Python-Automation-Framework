"""
License activation dialog GUI.
"""

import tkinter as tk
from tkinter import ttk, messagebox
import threading
from typing import Callable, Optional
import webbrowser


class LicenseDialog:
    """GUI dialog for license key activation."""

    def __init__(
        self,
        on_activate: Callable[[str], bool],
        purchase_url: str = "https://yoursite.com/buy"
    ):
        """
        Initialize the license dialog.

        Args:
            on_activate: Callback function that takes license key and returns True if successful
            purchase_url: URL where users can purchase licenses
        """
        self.on_activate = on_activate
        self.purchase_url = purchase_url
        self.result: Optional[bool] = None

        # Create window
        self.root = tk.Tk()
        self.root.title("License Activation - OSRS Bot")
        self.root.geometry("550x350")
        self.root.resizable(False, False)

        # Center window on screen
        self._center_window()

        # Set window icon (optional)
        try:
            # self.root.iconbitmap("icon.ico")  # Uncomment if you have an icon
            pass
        except Exception:
            pass

        self._build_ui()

        # Handle window close
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    def _center_window(self):
        """Center the window on the screen."""
        self.root.update_idletasks()
        width = self.root.winfo_width()
        height = self.root.winfo_height()
        x = (self.root.winfo_screenwidth() // 2) - (width // 2)
        y = (self.root.winfo_screenheight() // 2) - (height // 2)
        self.root.geometry(f'{width}x{height}+{x}+{y}')

    def _build_ui(self):
        """Build the dialog UI."""
        # Main frame with padding
        main_frame = ttk.Frame(self.root, padding="30")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Title
        title = ttk.Label(
            main_frame,
            text="OSRS Bot - License Activation",
            font=("Segoe UI", 16, "bold")
        )
        title.pack(pady=(0, 10))

        # Description
        desc = ttk.Label(
            main_frame,
            text="Please enter your license key to activate the bot.\nThis will tie the license to your current machine.",
            font=("Segoe UI", 10),
            justify=tk.CENTER
        )
        desc.pack(pady=(0, 25))

        # License key input frame
        key_frame = ttk.Frame(main_frame)
        key_frame.pack(fill=tk.X, pady=15)

        key_label = ttk.Label(
            key_frame,
            text="License Key:",
            font=("Segoe UI", 10, "bold")
        )
        key_label.pack(anchor=tk.W, pady=(0, 5))

        # Entry with larger font and padding
        self.key_entry = ttk.Entry(
            key_frame,
            width=40,
            font=("Courier New", 12)
        )
        self.key_entry.pack(fill=tk.X, ipady=5)
        self.key_entry.focus()

        # Format hint
        hint = ttk.Label(
            key_frame,
            text="Format: XXXX-XXXX-XXXX-XXXX",
            font=("Segoe UI", 8),
            foreground="gray"
        )
        hint.pack(anchor=tk.W, pady=(3, 0))

        # Buttons frame
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(pady=25)

        # Activate button (primary)
        self.activate_btn = ttk.Button(
            button_frame,
            text="Activate License",
            command=self._on_activate_clicked,
            width=20
        )
        self.activate_btn.pack(side=tk.LEFT, padx=5)

        # Purchase button
        purchase_btn = ttk.Button(
            button_frame,
            text="Buy License",
            command=self._open_purchase_url,
            width=15
        )
        purchase_btn.pack(side=tk.LEFT, padx=5)

        # Exit button
        exit_btn = ttk.Button(
            button_frame,
            text="Exit",
            command=self._on_close,
            width=10
        )
        exit_btn.pack(side=tk.LEFT, padx=5)

        # Status label
        self.status_label = ttk.Label(
            main_frame,
            text="",
            foreground="blue",
            font=("Segoe UI", 9)
        )
        self.status_label.pack(pady=10)

        # Progress bar (hidden initially)
        self.progress = ttk.Progressbar(
            main_frame,
            mode='indeterminate',
            length=300
        )

        # Bind Enter key to activate
        self.key_entry.bind('<Return>', lambda e: self._on_activate_clicked())

    def _on_activate_clicked(self):
        """Handle activate button click."""
        license_key = self.key_entry.get().strip()

        if not license_key:
            messagebox.showerror("Error", "Please enter a license key")
            return

        # Basic format validation
        if len(license_key) < 4:
            messagebox.showerror("Error", "License key appears to be invalid")
            return

        # Disable button and show loading
        self.activate_btn.config(state=tk.DISABLED)
        self.key_entry.config(state=tk.DISABLED)
        self.status_label.config(text="Activating license...", foreground="blue")
        self.progress.pack(pady=5)
        self.progress.start(10)

        # Run activation in background thread
        thread = threading.Thread(
            target=self._activate_license,
            args=(license_key,),
            daemon=True
        )
        thread.start()

    def _activate_license(self, license_key: str):
        """
        Activate license in background thread.

        Args:
            license_key: The license key to activate
        """
        try:
            success = self.on_activate(license_key)

            if success:
                self.result = True
                self.root.after(0, self._on_activation_success)
            else:
                self.root.after(0, self._on_activation_failed, "Activation failed")

        except Exception as e:
            self.root.after(0, self._on_activation_failed, str(e))

    def _on_activation_success(self):
        """Handle successful activation."""
        self.progress.stop()
        self.progress.pack_forget()
        self.status_label.config(text="License activated successfully!", foreground="green")

        messagebox.showinfo(
            "Success",
            "License activated successfully!\n\nThe bot will now start."
        )
        self.root.destroy()

    def _on_activation_failed(self, error: str):
        """
        Handle activation failure.

        Args:
            error: Error message to display
        """
        self.progress.stop()
        self.progress.pack_forget()
        self.status_label.config(text="Activation failed", foreground="red")

        # Re-enable controls
        self.activate_btn.config(state=tk.NORMAL)
        self.key_entry.config(state=tk.NORMAL)

        # Show error dialog
        messagebox.showerror(
            "Activation Failed",
            f"Failed to activate license:\n\n{error}\n\nPlease check your license key and try again."
        )

    def _open_purchase_url(self):
        """Open purchase URL in default browser."""
        try:
            webbrowser.open(self.purchase_url)
        except Exception as e:
            messagebox.showerror(
                "Error",
                f"Failed to open browser:\n{e}\n\nPlease visit:\n{self.purchase_url}"
            )

    def _on_close(self):
        """Handle window close event."""
        if self.result is None:
            result = messagebox.askyesno(
                "Exit",
                "Are you sure you want to exit?\n\nThe bot requires a valid license to run."
            )
            if result:
                self.result = False
                self.root.destroy()
        else:
            self.root.destroy()

    def show(self) -> bool:
        """
        Show the dialog and wait for result.

        Returns:
            True if activation successful, False otherwise
        """
        self.root.mainloop()
        return self.result if self.result is not None else False


if __name__ == "__main__":
    # Test the dialog
    def test_activate(key: str) -> bool:
        import time
        time.sleep(2)  # Simulate network delay
        return key == "TEST-1234-5678-ABCD"

    dialog = LicenseDialog(
        on_activate=test_activate,
        purchase_url="https://example.com/buy"
    )
    result = dialog.show()
    print(f"Dialog result: {result}")
