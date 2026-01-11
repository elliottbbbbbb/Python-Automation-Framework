"""
License Admin Panel - GUI for managing OSRS Bot licenses

This tool provides a simple interface to:
- Create new licenses
- View all licenses
- Search for specific licenses
- Revoke licenses
- View license details

Usage:
    python deployment/license_admin.py
"""

import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import requests
from datetime import datetime
import json
from typing import Optional, Dict, List


class LicenseAdminPanel:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("OSRS Bot - License Admin Panel")
        self.root.geometry("1000x700")

        # Configuration (will be set in setup)
        self.api_url = ""
        self.api_key = ""

        # Show setup dialog first
        if not self.show_setup_dialog():
            self.root.destroy()
            return

        self.setup_ui()

    def show_setup_dialog(self) -> bool:
        """Show dialog to configure API URL and key."""
        setup = tk.Toplevel()
        setup.title("Setup - API Configuration")
        setup.geometry("500x200")
        setup.transient(self.root)
        setup.grab_set()

        # Center the dialog
        setup.update_idletasks()
        x = (setup.winfo_screenwidth() // 2) - (500 // 2)
        y = (setup.winfo_screenheight() // 2) - (200 // 2)
        setup.geometry(f"500x200+{x}+{y}")

        result = {"ok": False}

        # API URL
        ttk.Label(setup, text="API URL:").grid(row=0, column=0, padx=10, pady=10, sticky="w")
        url_entry = ttk.Entry(setup, width=50)
        url_entry.insert(0, "https://osrs-automation-framework-production.up.railway.app")
        url_entry.grid(row=0, column=1, padx=10, pady=10)

        # API Key
        ttk.Label(setup, text="API Key:").grid(row=1, column=0, padx=10, pady=10, sticky="w")
        key_entry = ttk.Entry(setup, width=50, show="*")
        key_entry.grid(row=1, column=1, padx=10, pady=10)

        def on_ok():
            self.api_url = url_entry.get().strip()
            self.api_key = key_entry.get().strip()

            if not self.api_url or not self.api_key:
                messagebox.showerror("Error", "Both fields are required!")
                return

            # Test connection
            try:
                response = requests.get(f"{self.api_url}/health", timeout=5)
                if response.status_code != 200:
                    messagebox.showerror("Error", "Cannot connect to API!")
                    return
            except Exception as e:
                messagebox.showerror("Error", f"Connection failed: {e}")
                return

            result["ok"] = True
            setup.destroy()

        def on_cancel():
            setup.destroy()

        # Buttons
        btn_frame = ttk.Frame(setup)
        btn_frame.grid(row=2, column=0, columnspan=2, pady=20)

        ttk.Button(btn_frame, text="Connect", command=on_ok).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Cancel", command=on_cancel).pack(side=tk.LEFT, padx=5)

        setup.wait_window()
        return result["ok"]

    def setup_ui(self):
        """Setup the main UI."""
        # Create notebook (tabs)
        notebook = ttk.Notebook(self.root)
        notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Tab 1: Create License
        create_frame = ttk.Frame(notebook)
        notebook.add(create_frame, text="Create License")
        self.setup_create_tab(create_frame)

        # Tab 2: View Licenses
        view_frame = ttk.Frame(notebook)
        notebook.add(view_frame, text="View Licenses")
        self.setup_view_tab(view_frame)

        # Tab 3: Search License
        search_frame = ttk.Frame(notebook)
        notebook.add(search_frame, text="Search License")
        self.setup_search_tab(search_frame)

        # Status bar
        self.status_var = tk.StringVar(value="Ready")
        status_bar = ttk.Label(self.root, textvariable=self.status_var, relief=tk.SUNKEN)
        status_bar.pack(side=tk.BOTTOM, fill=tk.X)

    def setup_create_tab(self, parent):
        """Setup the Create License tab."""
        # Duration presets
        ttk.Label(parent, text="License Duration:", font=("Arial", 12, "bold")).pack(pady=10)

        preset_frame = ttk.Frame(parent)
        preset_frame.pack(pady=10)

        durations = [
            ("1 Hour (Trial)", 1),
            ("24 Hours", 24),
            ("3 Days", 72),
            ("1 Week", 168),
            ("1 Month", 720),
        ]

        self.duration_var = tk.IntVar(value=168)

        for text, hours in durations:
            ttk.Radiobutton(
                preset_frame,
                text=text,
                variable=self.duration_var,
                value=hours
            ).pack(anchor=tk.W, padx=20)

        # Custom duration
        custom_frame = ttk.Frame(parent)
        custom_frame.pack(pady=10)

        ttk.Label(custom_frame, text="Custom (hours):").pack(side=tk.LEFT, padx=5)
        self.custom_duration = ttk.Entry(custom_frame, width=10)
        self.custom_duration.pack(side=tk.LEFT, padx=5)

        def use_custom():
            try:
                hours = int(self.custom_duration.get())
                if hours > 0:
                    self.duration_var.set(hours)
            except ValueError:
                pass

        ttk.Button(custom_frame, text="Use Custom", command=use_custom).pack(side=tk.LEFT, padx=5)

        # Notes
        ttk.Label(parent, text="Notes (customer email, order ID, etc.):").pack(pady=5)
        self.notes_entry = ttk.Entry(parent, width=50)
        self.notes_entry.pack(pady=5)

        # Create button
        ttk.Button(
            parent,
            text="Create License",
            command=self.create_license,
            style="Accent.TButton"
        ).pack(pady=20)

        # Result display
        ttk.Label(parent, text="Created License:").pack(pady=5)
        self.create_result = scrolledtext.ScrolledText(parent, height=8, width=80)
        self.create_result.pack(pady=5)

    def setup_view_tab(self, parent):
        """Setup the View Licenses tab."""
        # Refresh button
        btn_frame = ttk.Frame(parent)
        btn_frame.pack(pady=10)

        ttk.Button(btn_frame, text="Refresh List", command=self.load_licenses).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Export to JSON", command=self.export_licenses).pack(side=tk.LEFT, padx=5)

        # Treeview for licenses
        columns = ("ID", "License Key", "Duration", "Expires At", "Status", "Activations")
        self.tree = ttk.Treeview(parent, columns=columns, show="headings", height=20)

        for col in columns:
            self.tree.heading(col, text=col)
            self.tree.column(col, width=150)

        # Scrollbar
        scrollbar = ttk.Scrollbar(parent, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscroll=scrollbar.set)

        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(10, 0), pady=10)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y, pady=10, padx=(0, 10))

        # Context menu
        self.tree.bind("<Double-1>", self.on_license_double_click)

        # Load licenses on startup
        self.root.after(100, self.load_licenses)

    def setup_search_tab(self, parent):
        """Setup the Search License tab."""
        search_frame = ttk.Frame(parent)
        search_frame.pack(pady=20)

        ttk.Label(search_frame, text="License Key:").pack(side=tk.LEFT, padx=5)
        self.search_entry = ttk.Entry(search_frame, width=30)
        self.search_entry.pack(side=tk.LEFT, padx=5)

        ttk.Button(search_frame, text="Search", command=self.search_license).pack(side=tk.LEFT, padx=5)

        # Result display
        ttk.Label(parent, text="License Details:").pack(pady=10)
        self.search_result = scrolledtext.ScrolledText(parent, height=15, width=80)
        self.search_result.pack(pady=10)

        # Action buttons
        action_frame = ttk.Frame(parent)
        action_frame.pack(pady=10)

        self.revoke_btn = ttk.Button(
            action_frame,
            text="Revoke This License",
            command=self.revoke_current_license,
            state=tk.DISABLED
        )
        self.revoke_btn.pack(side=tk.LEFT, padx=5)

        self.current_search_key = None

    def create_license(self):
        """Create a new license."""
        try:
            duration = self.duration_var.get()
            notes = self.notes_entry.get().strip()

            self.status_var.set(f"Creating license for {duration} hours...")
            self.root.update()

            url = f"{self.api_url}/api/v1/admin/licenses"
            params = {"duration_hours": duration}
            if notes:
                params["notes"] = notes

            headers = {"X-API-Key": self.api_key}

            response = requests.post(url, params=params, headers=headers, timeout=10)

            if response.status_code == 200:
                data = response.json()

                result = f"""
✓ License Created Successfully!

License Key: {data['license_key']}
Duration: {data['duration_hours']} hours
Created: {data['created_at']}
Status: Active
Activations: 0

📋 Copy this key and send it to your customer:
{data['license_key']}
"""
                self.create_result.delete(1.0, tk.END)
                self.create_result.insert(1.0, result)

                # Copy to clipboard
                self.root.clipboard_clear()
                self.root.clipboard_append(data['license_key'])

                self.status_var.set(f"✓ License created: {data['license_key']}")
                messagebox.showinfo("Success", f"License created!\n\nKey copied to clipboard:\n{data['license_key']}")

            else:
                error = response.json().get("detail", "Unknown error")
                messagebox.showerror("Error", f"Failed to create license:\n{error}")
                self.status_var.set("Error creating license")

        except Exception as e:
            messagebox.showerror("Error", f"Failed to create license:\n{e}")
            self.status_var.set(f"Error: {e}")

    def load_licenses(self):
        """Load and display all licenses."""
        try:
            self.status_var.set("Loading licenses...")
            self.root.update()

            url = f"{self.api_url}/api/v1/admin/licenses"
            headers = {"X-API-Key": self.api_key}

            response = requests.get(url, headers=headers, timeout=10)

            if response.status_code == 200:
                licenses = response.json()

                # Clear existing items
                for item in self.tree.get_children():
                    self.tree.delete(item)

                # Add licenses
                for lic in licenses:
                    expires = lic['expires_at']
                    if expires:
                        expires = datetime.fromisoformat(expires).strftime("%Y-%m-%d %H:%M")
                    else:
                        expires = "Not activated"

                    status = "Active" if lic['is_active'] else "Revoked"

                    self.tree.insert("", tk.END, values=(
                        lic['id'],
                        lic['license_key'],
                        f"{lic['duration_hours']}h",
                        expires,
                        status,
                        lic['activation_count']
                    ))

                self.status_var.set(f"✓ Loaded {len(licenses)} licenses")
            else:
                error = response.json().get("detail", "Unknown error")
                messagebox.showerror("Error", f"Failed to load licenses:\n{error}")
                self.status_var.set("Error loading licenses")

        except Exception as e:
            messagebox.showerror("Error", f"Failed to load licenses:\n{e}")
            self.status_var.set(f"Error: {e}")

    def search_license(self):
        """Search for a specific license."""
        try:
            key = self.search_entry.get().strip()
            if not key:
                messagebox.showwarning("Warning", "Please enter a license key")
                return

            self.status_var.set(f"Searching for {key}...")
            self.root.update()

            url = f"{self.api_url}/api/v1/admin/licenses/{key}"
            headers = {"X-API-Key": self.api_key}

            response = requests.get(url, headers=headers, timeout=10)

            if response.status_code == 200:
                data = response.json()

                expires = data['expires_at']
                if expires:
                    expires_dt = datetime.fromisoformat(expires)
                    expires_str = expires_dt.strftime("%Y-%m-%d %H:%M:%S")

                    # Calculate remaining time
                    now = datetime.utcnow()
                    if expires_dt > now:
                        delta = expires_dt - now
                        hours = delta.total_seconds() / 3600
                        remaining = f"{hours:.1f} hours remaining"
                    else:
                        remaining = "EXPIRED"
                else:
                    expires_str = "Not activated yet"
                    remaining = f"{data['duration_hours']} hours (when activated)"

                last_validated = data['last_validated_at']
                if last_validated:
                    last_validated = datetime.fromisoformat(last_validated).strftime("%Y-%m-%d %H:%M:%S")
                else:
                    last_validated = "Never"

                result = f"""
License Details:

License Key: {data['license_key']}
Status: {'✓ Active' if data['is_active'] else '❌ Revoked'}
Duration: {data['duration_hours']} hours
Created: {datetime.fromisoformat(data['created_at']).strftime("%Y-%m-%d %H:%M:%S")}
Expires: {expires_str}
Remaining: {remaining}
Activations: {data['activation_count']}
Last Validated: {last_validated}
"""

                self.search_result.delete(1.0, tk.END)
                self.search_result.insert(1.0, result)

                self.current_search_key = key
                self.revoke_btn.config(state=tk.NORMAL if data['is_active'] else tk.DISABLED)

                self.status_var.set(f"✓ Found license: {key}")
            elif response.status_code == 404:
                self.search_result.delete(1.0, tk.END)
                self.search_result.insert(1.0, "❌ License not found")
                self.revoke_btn.config(state=tk.DISABLED)
                self.status_var.set("License not found")
            else:
                error = response.json().get("detail", "Unknown error")
                messagebox.showerror("Error", f"Failed to search license:\n{error}")
                self.status_var.set("Error searching license")

        except Exception as e:
            messagebox.showerror("Error", f"Failed to search license:\n{e}")
            self.status_var.set(f"Error: {e}")

    def revoke_current_license(self):
        """Revoke the currently displayed license."""
        if not self.current_search_key:
            return

        if not messagebox.askyesno("Confirm", f"Revoke license {self.current_search_key}?\n\nThis cannot be undone!"):
            return

        try:
            url = f"{self.api_url}/api/v1/admin/licenses/{self.current_search_key}"
            headers = {"X-API-Key": self.api_key}

            response = requests.delete(url, headers=headers, timeout=10)

            if response.status_code == 200:
                messagebox.showinfo("Success", f"License {self.current_search_key} revoked successfully!")
                self.search_license()  # Refresh display
                self.status_var.set(f"✓ License revoked: {self.current_search_key}")
            else:
                error = response.json().get("detail", "Unknown error")
                messagebox.showerror("Error", f"Failed to revoke license:\n{error}")
                self.status_var.set("Error revoking license")

        except Exception as e:
            messagebox.showerror("Error", f"Failed to revoke license:\n{e}")
            self.status_var.set(f"Error: {e}")

    def on_license_double_click(self, event):
        """Handle double-click on license in tree."""
        selection = self.tree.selection()
        if not selection:
            return

        item = self.tree.item(selection[0])
        license_key = item['values'][1]  # License key is column 1

        # Switch to search tab and search for this license
        notebook = self.tree.master.master
        notebook.select(2)  # Search tab

        self.search_entry.delete(0, tk.END)
        self.search_entry.insert(0, license_key)
        self.search_license()

    def export_licenses(self):
        """Export all licenses to JSON file."""
        try:
            url = f"{self.api_url}/api/v1/admin/licenses"
            headers = {"X-API-Key": self.api_key}

            response = requests.get(url, headers=headers, timeout=10)

            if response.status_code == 200:
                licenses = response.json()

                filename = f"licenses_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
                with open(filename, 'w') as f:
                    json.dump(licenses, f, indent=2)

                messagebox.showinfo("Success", f"Exported {len(licenses)} licenses to:\n{filename}")
                self.status_var.set(f"✓ Exported to {filename}")
            else:
                error = response.json().get("detail", "Unknown error")
                messagebox.showerror("Error", f"Failed to export:\n{error}")

        except Exception as e:
            messagebox.showerror("Error", f"Failed to export:\n{e}")

    def run(self):
        """Run the application."""
        self.root.mainloop()


def main():
    app = LicenseAdminPanel()
    app.run()


if __name__ == "__main__":
    main()
