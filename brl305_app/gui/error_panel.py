import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import csv
import os


class ErrorPanel(ttk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent)
        self.app = app
        self._error_records = []
        self._last_count = 0

        self.configure(padding=10)

        top_frame = tk.Frame(self, bg="#1a1a2e")
        top_frame.pack(fill=tk.X, pady=(0, 10))

        tk.Button(top_frame, text="Read Error Count (W)",
                  command=self._on_read_count,
                  bg="#2a2a4e", fg="#e0e0e0", activebackground="#3a3a6e",
                  font=("Segoe UI", 10), padx=10, pady=3).pack(side=tk.LEFT, padx=5)

        self.count_var = tk.StringVar(value="Count: --")
        tk.Label(top_frame, textvariable=self.count_var,
                 bg="#1a1a2e", fg="#e0e0e0",
                 font=("Segoe UI", 12)).pack(side=tk.LEFT, padx=15)

        tk.Button(top_frame, text="Fetch All Errors",
                  command=self._on_fetch_all,
                  bg="#2a2a4e", fg="#e0e0e0", activebackground="#3a3a6e",
                  font=("Segoe UI", 10), padx=10, pady=3).pack(side=tk.LEFT, padx=5)

        btn_frame = tk.Frame(self, bg="#1a1a2e")
        btn_frame.pack(fill=tk.X, pady=(0, 10))

        tk.Button(btn_frame, text="Edit Detail",
                  command=self._on_edit_detail,
                  bg="#2a2a4e", fg="#e0e0e0", activebackground="#3a3a6e",
                  font=("Segoe UI", 10), padx=10, pady=3).pack(side=tk.LEFT, padx=5)

        tk.Button(btn_frame, text="Export to CSV",
                  command=self._on_export,
                  bg="#2a2a4e", fg="#e0e0e0", activebackground="#3a3a6e",
                  font=("Segoe UI", 10), padx=10, pady=3).pack(side=tk.LEFT, padx=5)

        tree_frame = tk.Frame(self, bg="#1a1a2e")
        tree_frame.pack(fill=tk.BOTH, expand=True)

        columns = ("#", "Detail Text", "Meter at Fault", "Fetched At")
        self.tree = ttk.Treeview(tree_frame, columns=columns, show="headings",
                                 selectmode="browse")
        for col in columns:
            self.tree.heading(col, text=col)
            self.tree.column(col, width=120)

        vsb = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        vsb.pack(side=tk.RIGHT, fill=tk.Y)

        self._style_tree()

    def _style_tree(self):
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("Treeview", background="#2a2a4e", foreground="#e0e0e0",
                        fieldbackground="#2a2a4e", rowheight=24)
        style.configure("Treeview.Heading", background="#3a3a5e", foreground="#e0e0e0")

    def _on_read_count(self):
        self.app.submit("read_error_count")

    def _on_fetch_all(self):
        if self._last_count <= 0:
            messagebox.showinfo("Fetch Errors", "Read error count first.")
            return
        for i in self.tree.get_children():
            self.tree.delete(i)
        self._error_records.clear()
        for num in range(1, self._last_count + 1):
            self.app.submit("read_error_detail", num)

    def _on_edit_detail(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showinfo("Edit Detail", "Select an error row first.")
            return
        item = self.tree.item(selected[0])
        err_num = int(item["values"][0])
        dialog = EditDetailDialog(self, err_num, self.app)
        self.wait_window(dialog.top)

    def _on_export(self):
        if not self._error_records:
            messagebox.showinfo("Export", "No error data to export.")
            return
        path = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv")],
            initialdir=os.path.expanduser("~/Desktop"),
            title="Export Error Records",
        )
        if not path:
            return
        try:
            with open(path, "w", newline="", encoding="utf-8-sig") as f:
                writer = csv.writer(f)
                writer.writerow(["#", "Detail Text", "Meter at Fault", "Fetched At"])
                for rec in self._error_records:
                    writer.writerow([rec["error_number"], rec["detail_text"],
                                     rec["meter_at_fault"], rec.get("fetched_at", "")])
            messagebox.showinfo("Export", f"Exported to:\n{path}")
        except Exception as e:
            messagebox.showerror("Export", f"Failed to export:\n{e}")

    def update_count(self, count):
        if count is None:
            self.count_var.set("Count: ERR")
            self._last_count = 0
        else:
            self.count_var.set(f"Count: {count}")
            self._last_count = count

    def add_error_detail(self, detail):
        if detail is None:
            return
        from datetime import datetime
        detail["fetched_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self._error_records.append(detail)
        self.tree.insert("", tk.END, values=(
            detail["error_number"],
            detail["detail_text"],
            detail["meter_at_fault"],
            detail["fetched_at"],
        ))


class EditDetailDialog:
    def __init__(self, parent, error_num, app):
        self.app = app
        self.top = tk.Toplevel(parent)
        self.top.title(f"Edit Error #{error_num:02d}")
        self.top.geometry("400x150")
        self.top.configure(bg="#1a1a2e")
        self.top.transient(parent)
        self.top.grab_set()

        tk.Label(self.top, text=f"Error #{error_num:02d} — Detail Text (max 16 chars):",
                 bg="#1a1a2e", fg="#e0e0e0",
                 font=("Segoe UI", 10)).pack(pady=(15, 5), padx=10, anchor=tk.W)

        self.text_var = tk.StringVar()
        entry = tk.Entry(self.top, textvariable=self.text_var,
                         bg="#2a2a4e", fg="#e0e0e0", insertbackground="#e0e0e0",
                         font=("Segoe UI", 12), width=20)
        entry.pack(pady=5, padx=10, fill=tk.X)
        entry.focus_set()

        self.char_count_var = tk.StringVar(value="0/16")
        tk.Label(self.top, textvariable=self.char_count_var,
                 bg="#1a1a2e", fg="#888",
                 font=("Segoe UI", 9)).pack(anchor=tk.W, padx=10)

        self.text_var.trace("w", lambda *a: self.char_count_var.set(
            f"{len(self.text_var.get())}/16"))

        btn_frame = tk.Frame(self.top, bg="#1a1a2e")
        btn_frame.pack(pady=15)

        tk.Button(btn_frame, text="Send (V)",
                  command=self._on_send,
                  bg="#2a2a4e", fg="#e0e0e0", activebackground="#3a3a6e",
                  padx=15, pady=3).pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="Cancel",
                  command=self.top.destroy,
                  bg="#4e2a2a", fg="#ff6666", activebackground="#6e3a3a",
                  padx=15, pady=3).pack(side=tk.LEFT, padx=5)

    def _on_send(self):
        text = self.text_var.get()
        if len(text) > 16:
            text = text[:16]
        self.app.submit("write_error_detail", error_num, text)
        self.top.destroy()
