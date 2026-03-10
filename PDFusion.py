"""
PDF Merger Tool (Enhanced)
- Browse a folder to load PDF files
- Arrange files in preferred order (drag or use ▲ ▼)
- Choose output page size and orientation
- Choose compression quality (High / Medium / Low)
- Merge into a single output PDF
"""

import os
import io
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from pypdf import PdfWriter, PdfReader
from pypdf.generic import NameObject

# ── Page size definitions (width × height in points, portrait) ────────────────
PAGE_SIZES = {
    "Original (keep as-is)": None,
    "A4  (210 × 297 mm)":    (595.28,  841.89),
    "A3  (297 × 420 mm)":    (841.89, 1190.55),
    "A5  (148 × 210 mm)":    (419.53,  595.28),
    "Letter  (8.5 × 11 in)": (612.00,  792.00),
    "Legal  (8.5 × 14 in)":  (612.00, 1008.00),
    "Tabloid  (11 × 17 in)": (792.00, 1224.00),
}

# ── Compression settings ──────────────────────────────────────────────────────
QUALITY_SETTINGS = {
    "High Quality  (original)": {"compress": False, "image_quality": 95},
    "Medium Quality":            {"compress": True,  "image_quality": 60},
    "Low Quality  (smallest)":   {"compress": True,  "image_quality": 25},
}


class PDFMergerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("PDF Merger")
        self.root.geometry("760x690")
        self.root.resizable(True, True)
        self.root.configure(bg="#f0f2f5")

        self.pdf_files = []
        self.drag_start_index = None

        self._build_ui()

    # ================================================================== UI ==
    def _build_ui(self):
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("TButton",       font=("Segoe UI", 10), padding=6)
        style.configure("TLabel",        font=("Segoe UI", 10), background="#f0f2f5")
        style.configure("Header.TLabel", font=("Segoe UI", 13, "bold"), background="#f0f2f5")
        style.configure("Sub.TLabel",    font=("Segoe UI", 9),  background="#f0f2f5", foreground="#555")
        style.configure("Bold.TLabel",   font=("Segoe UI", 10, "bold"), background="#f0f2f5")
        style.configure("BoldW.TLabel",  font=("Segoe UI", 10, "bold"), background="#ffffff")
        style.configure("CardLbl.TLabel",font=("Segoe UI", 10), background="#ffffff")
        style.configure("TCombobox",     font=("Segoe UI", 10))
        style.configure("TRadiobutton",  font=("Segoe UI", 10), background="#ffffff")

        # ── Title ──────────────────────────────────────────────────────────
        ttk.Label(self.root, text="📄 PDF Merger", style="Header.TLabel").pack(pady=(16, 2))
        ttk.Label(self.root,
                  text="Select a folder, arrange PDFs, configure output, then merge.",
                  style="Sub.TLabel").pack()

        # ── Folder picker ──────────────────────────────────────────────────
        folder_frame = tk.Frame(self.root, bg="#f0f2f5")
        folder_frame.pack(fill="x", padx=20, pady=(12, 0))

        self.folder_var = tk.StringVar(value="No folder selected")
        ttk.Label(folder_frame, textvariable=self.folder_var, style="Sub.TLabel",
                  wraplength=500, anchor="w").pack(side="left", fill="x", expand=True)
        ttk.Button(folder_frame, text="📂  Browse Folder",
                   command=self.browse_folder).pack(side="right")

        # ── File list ──────────────────────────────────────────────────────
        list_frame = tk.Frame(self.root, bg="#f0f2f5")
        list_frame.pack(fill="both", expand=True, padx=20, pady=(10, 0))

        ttk.Label(list_frame, text="PDF Files  (drag rows or use ▲ ▼ to reorder)",
                  style="Sub.TLabel").pack(anchor="w", pady=(0, 4))

        lb_frame = tk.Frame(list_frame, bg="#f0f2f5")
        lb_frame.pack(fill="both", expand=True)

        scrollbar = ttk.Scrollbar(lb_frame, orient="vertical")
        self.listbox = tk.Listbox(
            lb_frame,
            selectmode="single",
            font=("Segoe UI", 10),
            bg="#ffffff", fg="#222",
            selectbackground="#4a90d9", selectforeground="#fff",
            activestyle="none", relief="flat",
            bd=1, highlightthickness=1, highlightcolor="#ccc",
            yscrollcommand=scrollbar.set,
        )
        scrollbar.config(command=self.listbox.yview)
        scrollbar.pack(side="right", fill="y")
        self.listbox.pack(side="left", fill="both", expand=True)

        self.listbox.bind("<ButtonPress-1>",   self._drag_start)
        self.listbox.bind("<B1-Motion>",       self._drag_motion)
        self.listbox.bind("<ButtonRelease-1>", self._drag_end)

        # ── Move / Remove buttons ──────────────────────────────────────────
        btn_row = tk.Frame(self.root, bg="#f0f2f5")
        btn_row.pack(fill="x", padx=20, pady=6)

        ttk.Button(btn_row, text="▲  Move Up",   command=self.move_up).pack(side="left", padx=(0, 6))
        ttk.Button(btn_row, text="▼  Move Down", command=self.move_down).pack(side="left", padx=(0, 6))
        ttk.Button(btn_row, text="✕  Remove",    command=self.remove_selected).pack(side="left", padx=(0, 6))
        ttk.Button(btn_row, text="🗑  Clear All", command=self.clear_all).pack(side="left")

        # ── Output Settings Card ───────────────────────────────────────────
        card = tk.Frame(self.root, bg="#ffffff", bd=1, relief="groove")
        card.pack(fill="x", padx=20, pady=(4, 6))

        ttk.Label(card, text="Output Settings", style="BoldW.TLabel").grid(
            row=0, column=0, columnspan=4, sticky="w", padx=12, pady=(10, 6))

        # -- Page Size row
        ttk.Label(card, text="Page Size:", style="CardLbl.TLabel").grid(
            row=1, column=0, sticky="w", padx=(12, 6), pady=4)
        self.page_size_var = tk.StringVar(value="Original (keep as-is)")
        size_combo = ttk.Combobox(
            card, textvariable=self.page_size_var,
            values=list(PAGE_SIZES.keys()), state="readonly", width=28)
        size_combo.grid(row=1, column=1, sticky="w", padx=(0, 20), pady=4)

        # -- Orientation row
        ttk.Label(card, text="Orientation:", style="CardLbl.TLabel").grid(
            row=1, column=2, sticky="w", padx=(0, 6), pady=4)
        self.orientation_var = tk.StringVar(value="Portrait")
        orient_frame = tk.Frame(card, bg="#ffffff")
        orient_frame.grid(row=1, column=3, sticky="w", pady=4, padx=(0, 12))
        for val in ("Portrait", "Landscape"):
            ttk.Radiobutton(orient_frame, text=val,
                            variable=self.orientation_var, value=val).pack(
                side="left", padx=(0, 10))

        # -- Quality row
        ttk.Label(card, text="Quality:", style="CardLbl.TLabel").grid(
            row=2, column=0, sticky="w", padx=(12, 6), pady=(4, 10))
        self.quality_var = tk.StringVar(value="High Quality  (original)")
        quality_frame = tk.Frame(card, bg="#ffffff")
        quality_frame.grid(row=2, column=1, columnspan=3,
                           sticky="w", pady=(4, 10))
        for val in QUALITY_SETTINGS:
            ttk.Radiobutton(quality_frame, text=val,
                            variable=self.quality_var, value=val).pack(
                side="left", padx=(0, 14))

        card.columnconfigure(1, weight=1)

        # ── Status label ───────────────────────────────────────────────────
        self.status_var = tk.StringVar(value="No files loaded.")
        ttk.Label(self.root, textvariable=self.status_var,
                  style="Sub.TLabel").pack(anchor="w", padx=22)

        # ── Progress bar ───────────────────────────────────────────────────
        self.progress = ttk.Progressbar(self.root, mode="determinate", length=200)
        self.progress.pack(fill="x", padx=20, pady=(2, 4))

        # ── Merge button ───────────────────────────────────────────────────
        merge_frame = tk.Frame(self.root, bg="#f0f2f5")
        merge_frame.pack(fill="x", padx=20, pady=(2, 14))

        tk.Button(
            merge_frame,
            text="🔗  Merge PDFs",
            font=("Segoe UI", 11, "bold"),
            bg="#4a90d9", fg="white",
            activebackground="#357abd", activeforeground="white",
            relief="flat", padx=20, pady=8,
            cursor="hand2", command=self.merge_pdfs,
        ).pack(side="right")

    # =========================================================== Folder load
    def browse_folder(self):
        folder = filedialog.askdirectory(title="Select folder containing PDFs")
        if not folder:
            return
        found = sorted(
            [os.path.join(folder, f) for f in os.listdir(folder)
             if f.lower().endswith(".pdf")]
        )
        if not found:
            messagebox.showwarning("No PDFs", "No PDF files found in the selected folder.")
            return
        self.pdf_files = found
        self.folder_var.set(f"📁  {folder}")
        self._refresh_list()

    def _refresh_list(self):
        self.listbox.delete(0, tk.END)
        for i, path in enumerate(self.pdf_files, start=1):
            self.listbox.insert(tk.END, f"  {i:>2}.  {os.path.basename(path)}")
        count = len(self.pdf_files)
        self.status_var.set(f"{count} PDF{'s' if count != 1 else ''} loaded.")

    # =========================================================== Reordering
    def move_up(self):
        sel = self.listbox.curselection()
        if not sel or sel[0] == 0:
            return
        i = sel[0]
        self.pdf_files[i - 1], self.pdf_files[i] = self.pdf_files[i], self.pdf_files[i - 1]
        self._refresh_list()
        self.listbox.selection_set(i - 1)
        self.listbox.see(i - 1)

    def move_down(self):
        sel = self.listbox.curselection()
        if not sel or sel[0] >= len(self.pdf_files) - 1:
            return
        i = sel[0]
        self.pdf_files[i + 1], self.pdf_files[i] = self.pdf_files[i], self.pdf_files[i + 1]
        self._refresh_list()
        self.listbox.selection_set(i + 1)
        self.listbox.see(i + 1)

    def remove_selected(self):
        sel = self.listbox.curselection()
        if not sel:
            return
        i = sel[0]
        self.pdf_files.pop(i)
        self._refresh_list()
        if self.pdf_files:
            self.listbox.selection_set(min(i, len(self.pdf_files) - 1))

    def clear_all(self):
        if self.pdf_files and messagebox.askyesno("Clear All",
                                                   "Remove all files from the list?"):
            self.pdf_files.clear()
            self._refresh_list()
            self.status_var.set("List cleared.")

    # =========================================================== Drag & drop
    def _drag_start(self, event):
        self.drag_start_index = self.listbox.nearest(event.y)

    def _drag_motion(self, event):
        target = self.listbox.nearest(event.y)
        if target != self.drag_start_index and 0 <= target < len(self.pdf_files):
            self.pdf_files.insert(target, self.pdf_files.pop(self.drag_start_index))
            self.drag_start_index = target
            self._refresh_list()
            self.listbox.selection_set(target)

    def _drag_end(self, _event):
        self.drag_start_index = None

    # =========================================================== Page resize
    def _apply_page_size(self, page, target_w, target_h, landscape):
        """Scale and centre page content to fit the target dimensions."""
        w = float(target_w)
        h = float(target_h)
        if landscape:
            w, h = h, w

        orig_w = float(page.mediabox.width)
        orig_h = float(page.mediabox.height)
        if orig_w == 0 or orig_h == 0:
            return page

        scale = min(w / orig_w, h / orig_h)   # uniform scale, keep aspect ratio
        tx    = (w - orig_w * scale) / 2
        ty    = (h - orig_h * scale) / 2

        page.add_transformation([scale, 0, 0, scale, tx, ty])
        page.mediabox.lower_left  = (0, 0)
        page.mediabox.upper_right = (w, h)
        return page

    # =========================================================== Compression
    def _compress_writer(self, writer, quality_key):
        settings = QUALITY_SETTINGS[quality_key]
        if not settings["compress"]:
            return writer                          # High quality — nothing to do

        # Compress PDF content streams (text/vector)
        for page in writer.pages:
            page.compress_content_streams()

        # Re-encode embedded images at lower quality (requires Pillow)
        try:
            from PIL import Image
            for page in writer.pages:
                self._compress_page_images(page, settings["image_quality"])
        except ImportError:
            pass   # Pillow not installed — skip image re-encoding

        return writer

    def _compress_page_images(self, page, quality):
        """Re-encode raster images in a page as JPEG at the given quality."""
        if "/Resources" not in page:
            return
        resources = page["/Resources"]
        if "/XObject" not in resources:
            return

        from PIL import Image
        xobjects = resources["/XObject"].get_object()
        for name in list(xobjects.keys()):
            try:
                obj = xobjects[name].get_object()
                if obj.get("/Subtype") != "/Image":
                    continue

                data   = obj._data
                width  = int(obj["/Width"])
                height = int(obj["/Height"])
                cs     = obj.get("/ColorSpace", "/DeviceRGB")
                mode   = "L" if str(cs) == "/DeviceGray" else "RGB"

                img = Image.frombytes(mode, (width, height), data)
                buf = io.BytesIO()
                img.save(buf, format="JPEG", quality=quality, optimize=True)
                buf.seek(0)
                new_data = buf.read()

                obj._data = new_data
                obj.update({
                    NameObject("/Filter"):           NameObject("/DCTDecode"),
                    NameObject("/Length"):           len(new_data),
                    NameObject("/BitsPerComponent"): obj.get("/BitsPerComponent", 8),
                })
            except Exception:
                continue   # Skip any image that cannot be processed

    # ============================================================= Merge PDF
    def merge_pdfs(self):
        if len(self.pdf_files) < 2:
            messagebox.showwarning("Not enough files",
                                   "Please load at least 2 PDF files to merge.")
            return

        out_path = filedialog.asksaveasfilename(
            title="Save merged PDF as…",
            defaultextension=".pdf",
            filetypes=[("PDF files", "*.pdf")],
            initialfile="merged_output.pdf",
        )
        if not out_path:
            return

        size_key    = self.page_size_var.get()
        target_size = PAGE_SIZES[size_key]
        landscape   = self.orientation_var.get() == "Landscape"
        quality_key = self.quality_var.get()

        self.status_var.set("Merging… please wait.")
        self.progress["value"] = 0
        self.root.update_idletasks()

        try:
            writer = PdfWriter()
            total  = len(self.pdf_files)

            for idx, path in enumerate(self.pdf_files):
                reader = PdfReader(path)
                for page in reader.pages:
                    if target_size is not None:
                        page = self._apply_page_size(
                            page, target_size[0], target_size[1], landscape)
                    writer.add_page(page)

                self.progress["value"] = int((idx + 1) / total * 80)
                self.root.update_idletasks()

            self.status_var.set("Applying compression… please wait.")
            self.root.update_idletasks()
            writer = self._compress_writer(writer, quality_key)

            self.progress["value"] = 95
            self.root.update_idletasks()

            with open(out_path, "wb") as f:
                writer.write(f)

            self.progress["value"] = 100
            kb   = os.path.getsize(out_path) / 1024
            size_str = f"{kb / 1024:.2f} MB" if kb >= 1024 else f"{kb:.1f} KB"

            self.status_var.set(
                f"✅  Merged {total} files → {os.path.basename(out_path)}  ({size_str})")
            messagebox.showinfo(
                "Success",
                f"Merged {total} PDFs successfully!\n\n"
                f"Page size:    {size_key}\n"
                f"Orientation:  {self.orientation_var.get()}\n"
                f"Quality:      {quality_key}\n"
                f"Output size:  {size_str}\n\n"
                f"Saved to:\n{out_path}",
            )

        except Exception as exc:
            self.status_var.set("❌  Merge failed.")
            self.progress["value"] = 0
            messagebox.showerror("Error", f"Failed to merge PDFs:\n{exc}")


# ──────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    root = tk.Tk()
    app = PDFMergerApp(root)
    root.mainloop()
