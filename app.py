"""
PDFusion - Cloud PDF Merger
Flask backend: stateless, in-memory processing.
No files are stored on the server.
"""

import io
import os
import json
from flask import Flask, request, jsonify, send_file, render_template
from pypdf import PdfWriter, PdfReader
from pypdf.generic import NameObject
from functools import wraps
from datetime import datetime, timedelta
import hashlib

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 50 * 1024 * 1024  # 50 MB max upload

# ── Page sizes (points) ───────────────────────────────────────────────────────
PAGE_SIZES = {
    "original": None,
    "a4":       (595.28,  841.89),
    "a3":       (841.89, 1190.55),
    "a5":       (419.53,  595.28),
    "letter":   (612.00,  792.00),
    "legal":    (612.00, 1008.00),
    "tabloid":  (792.00, 1224.00),
}

QUALITY_SETTINGS = {
    "high":   {"compress": False, "image_quality": 95},
    "medium": {"compress": True,  "image_quality": 60},
    "low":    {"compress": True,  "image_quality": 25},
}

# ── Simple in-memory rate limiter (resets on server restart) ──────────────────
# Tracks merge count per IP per day for freemium limiting
_rate_store = {}   # { ip: { "date": "YYYY-MM-DD", "count": int } }
FREE_DAILY_LIMIT = 3


def get_ip():
    return request.headers.get("X-Forwarded-For", request.remote_addr).split(",")[0].strip()


def check_rate_limit(ip):
    today = datetime.utcnow().strftime("%Y-%m-%d")
    record = _rate_store.get(ip)
    if not record or record["date"] != today:
        _rate_store[ip] = {"date": today, "count": 0}
    return _rate_store[ip]["count"]


def increment_rate(ip):
    today = datetime.utcnow().strftime("%Y-%m-%d")
    if ip not in _rate_store or _rate_store[ip]["date"] != today:
        _rate_store[ip] = {"date": today, "count": 0}
    _rate_store[ip]["count"] += 1


# ── Page resize helper ────────────────────────────────────────────────────────
def apply_page_size(page, target_w, target_h, landscape):
    w, h = float(target_w), float(target_h)
    if landscape:
        w, h = h, w
    orig_w = float(page.mediabox.width)
    orig_h = float(page.mediabox.height)
    if orig_w == 0 or orig_h == 0:
        return page
    scale = min(w / orig_w, h / orig_h)
    tx = (w - orig_w * scale) / 2
    ty = (h - orig_h * scale) / 2
    page.add_transformation([scale, 0, 0, scale, tx, ty])
    page.mediabox.lower_left  = (0, 0)
    page.mediabox.upper_right = (w, h)
    return page


# ── Image compression helper ─────────────────────────────────────────────────
def compress_page_images(page, quality):
    try:
        from PIL import Image
    except ImportError:
        return
    if "/Resources" not in page:
        return
    resources = page["/Resources"]
    if "/XObject" not in resources:
        return
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
            img    = Image.frombytes(mode, (width, height), data)
            buf    = io.BytesIO()
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
            continue


# ── Routes ────────────────────────────────────────────────────────────────────
@app.route("/")
def index():
    return render_template("index.html")


@app.route("/about")
def about():
    return render_template("about.html")


@app.route("/api/merge", methods=["POST"])
def merge():
    ip = get_ip()

    # Freemium gate
    uses_today = check_rate_limit(ip)
    premium    = request.form.get("premium_key", "").strip()
    is_premium = (premium == os.environ.get("PREMIUM_KEY", ""))

    if not is_premium and uses_today >= FREE_DAILY_LIMIT:
        return jsonify({
            "error": "free_limit",
            "message": f"Free plan allows {FREE_DAILY_LIMIT} merges per day. "
                       "Support PDFusion to unlock unlimited merges.",
            "uses_today": uses_today,
            "limit": FREE_DAILY_LIMIT,
        }), 429

    files = request.files.getlist("files")
    if len(files) < 2:
        return jsonify({"error": "Need at least 2 PDF files."}), 400

    size_key    = request.form.get("page_size", "original")
    landscape   = request.form.get("orientation", "portrait") == "landscape"
    quality_key = request.form.get("quality", "high")
    order_raw   = request.form.get("order", "")

    target_size = PAGE_SIZES.get(size_key)
    q_settings  = QUALITY_SETTINGS.get(quality_key, QUALITY_SETTINGS["high"])

    # Re-order files if client sent an order array
    if order_raw:
        try:
            order = json.loads(order_raw)
            files = [files[i] for i in order if i < len(files)]
        except Exception:
            pass

    try:
        writer = PdfWriter()

        for f in files:
            data   = f.read()
            reader = PdfReader(io.BytesIO(data))
            for page in reader.pages:
                if target_size:
                    page = apply_page_size(page, target_size[0], target_size[1], landscape)
                writer.add_page(page)

        # Compression
        if q_settings["compress"]:
            for page in writer.pages:
                page.compress_content_streams()
            for page in writer.pages:
                compress_page_images(page, q_settings["image_quality"])

        out = io.BytesIO()
        writer.write(out)
        out.seek(0)

        increment_rate(ip)

        remaining = max(0, FREE_DAILY_LIMIT - check_rate_limit(ip))

        response = send_file(
            out,
            mimetype="application/pdf",
            as_attachment=True,
            download_name="pdfusion_merged.pdf",
        )
        response.headers["X-Uses-Today"]   = str(check_rate_limit(ip))
        response.headers["X-Remaining"]    = str(remaining)
        response.headers["X-Daily-Limit"]  = str(FREE_DAILY_LIMIT)
        return response

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/status", methods=["GET"])
def status():
    ip        = get_ip()
    uses      = check_rate_limit(ip)
    remaining = max(0, FREE_DAILY_LIMIT - uses)
    return jsonify({
        "uses_today": uses,
        "remaining":  remaining,
        "limit":      FREE_DAILY_LIMIT,
    })


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
