# PDFusion — Python PDF Merger with GUI

A lightweight desktop application for merging multiple PDF files with full control over page size, orientation, and output quality — all through a clean, user-friendly graphical interface. No command-line knowledge required.

---

## 🖼️ Features

- **📂 Folder-based file picker** — select a folder and all PDFs inside are loaded automatically
- **🔀 Drag-and-drop reordering** — drag files into your preferred merge order directly in the list
- **▲ ▼ Move buttons** — fine-tune order with Move Up / Move Down controls
- **📐 Page size selection** — choose from A3, A4, A5, Letter, Legal, Tabloid, or keep original sizes
- **🔄 Orientation control** — set output to Portrait or Landscape
- **🗜️ Compression / quality options** — three quality presets to control output file size:
  - **High Quality** — no changes, preserves original quality
  - **Medium Quality** — compresses streams and re-encodes images at 60% JPEG quality
  - **Low Quality** — maximum compression, images re-encoded at 25% JPEG quality
- **📊 Live progress bar** — visual feedback during merge and compression
- **📋 Output summary** — success dialog shows page size, orientation, quality, and final file size

---

## 🛠️ Requirements

### Python Version
Python **3.8 or higher** is required.

### Dependencies

| Package | Purpose | Required |
|---|---|---|
| `pypdf` | Core PDF reading, writing, and merging | ✅ Yes |
| `Pillow` | Image re-encoding for Medium / Low quality compression | ⚠️ Optional |
| `tkinter` | GUI framework (ships with Python standard library) | ✅ Yes (built-in) |

> **Note:** `tkinter` is included with most Python installations. On some Linux distributions you may need to install it separately:
> ```bash
> sudo apt-get install python3-tk
> ```

---

## 📦 Installation

**1. Clone the repository**
```bash
git clone https://github.com/abiodun360/pdfusion.git
cd pdfusion
```

**2. Install required dependencies**
```bash
pip install pypdf
```

**3. (Optional) Install Pillow for image compression support**
```bash
pip install Pillow
```

> Without Pillow, Medium and Low quality modes still compress text and vector streams — only image re-encoding is skipped.

---

## ▶️ Usage

Run the application with:

```bash
python pdf_merger.py
```

### Step-by-step

1. Click **📂 Browse Folder** and select the folder containing your PDF files
2. All PDFs in the folder are loaded into the list automatically
3. **Reorder** the files by dragging rows or using the ▲ / ▼ buttons
4. Use **✕ Remove** to exclude any files you don't want merged
5. In the **Output Settings** panel:
   - Choose a **Page Size** (or keep originals)
   - Set **Orientation** — Portrait or Landscape
   - Select a **Quality** preset
6. Click **🔗 Merge PDFs**, choose where to save, and you're done

---

## 📁 Project Structure

```
pdfusion/
│
├── pdf_merger.py     # Main application — run this file
└── README.md         # Project documentation
```

---

## 🔧 Page Size Reference

| Option | Dimensions |
|---|---|
| Original (keep as-is) | Preserves each page's existing size |
| A5 | 148 × 210 mm |
| A4 | 210 × 297 mm |
| A3 | 297 × 420 mm |
| Letter | 8.5 × 11 in |
| Legal | 8.5 × 14 in |
| Tabloid | 11 × 17 in |

When a page size is selected, content is uniformly scaled and centred to fit — the aspect ratio is always preserved.

---

## 🗜️ Compression Details

| Quality Preset | Content Streams | Image Re-encoding | Best For |
|---|---|---|---|
| High Quality | Unchanged | Unchanged | Archival, print-ready |
| Medium Quality | Compressed | JPEG 60% | General sharing / email |
| Low Quality | Compressed | JPEG 25% | Web upload, minimal size |

> Image compression requires **Pillow** to be installed. Content stream compression works without it.

---

## 🤝 Contributing

Contributions, bug reports, and feature suggestions are welcome! Feel free to open an issue or submit a pull request.

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/your-feature`)
3. Commit your changes (`git commit -m 'Add your feature'`)
4. Push to the branch (`git push origin feature/your-feature`)
5. Open a Pull Request

---

## 📄 License

This project is licensed under the MIT License — free to use, modify, and distribute.

---

## 💡 Acknowledgements

Built with:
- [pypdf](https://github.com/py-pdf/pypdf) — PDF processing
- [Pillow](https://python-pillow.org/) — image compression
- [tkinter](https://docs.python.org/3/library/tkinter.html) — GUI framework
