# Copyright (c) 2026 Lumen Solutions
# SPDX-License-Identifier: AGPL-3.0-only
# "LumenPOS" is a trademark of Lumen Solutions. See TRADEMARKS.md.
"""Pictures on the thermal (ESC/POS) receipt.

The restaurant's own logo prints at the top when its receipt settings have
one, and the Lumen Restaurants mark prints small at the foot of every receipt
(he chose it, 2026-09-27: "خلي حقنا موجود ولو هو حاط شعار يطلع شعاره"). Both go
out as GS v 0 raster images, which Epson-compatible printers take. Pillow comes
with Frappe. A picture that cannot be read or converted is left out, never the
receipt.
"""
import io
import os
from functools import lru_cache

import frappe

GS = b"\x1d"
# The kit's receipt cut: 96 dots is 12 mm at 203 dpi, black on transparent.
MARK_FILE = "public/images/png/receipt-96px-203dpi.png"
# The restaurant's logo fits 48 mm by 20 mm, inside both a 58 mm and an 80 mm roll.
LOGO_MAX = (384, 160)


def raster(image):
    """GS v 0 bytes for a 1-bit PIL image: a dark dot where the image is black."""
    width, height = image.size
    row_bytes = (width + 7) // 8
    pixels = image.load()
    data = bytearray()
    for y in range(height):
        for xb in range(row_bytes):
            byte = 0
            for bit in range(8):
                x = xb * 8 + bit
                if x < width and not pixels[x, y]:
                    byte |= 0x80 >> bit
            data.append(byte)
    head = bytes([row_bytes % 256, row_bytes // 256, height % 256, height // 256])
    return GS + b"v0\x00" + head + bytes(data)


def _gray_on_white(source):
    """A grayscale copy with any transparency laid on white paper."""
    from PIL import Image

    image = Image.open(source).convert("RGBA")
    paper = Image.new("RGBA", image.size, (255, 255, 255, 255))
    paper.alpha_composite(image)
    return paper.convert("L")


@lru_cache(maxsize=1)
def mark_bytes():
    """The Lumen Restaurants mark, sharp black and white (it already is)."""
    try:
        gray = _gray_on_white(frappe.get_app_path("lumen_restaurants", *MARK_FILE.split("/")))
        return raster(gray.point(lambda value: 0 if value < 128 else 255, "1"))
    except Exception:
        frappe.log_error(title="Lumen Restaurants: receipt mark")
        return b""


def logo_bytes(url):
    """The restaurant's logo, shrunk to fit and dithered to black and white."""
    content = _read(url)
    if not content:
        return b""
    try:
        gray = _gray_on_white(io.BytesIO(content))
        gray.thumbnail(LOGO_MAX)
        return raster(gray.convert("1"))
    except Exception:
        frappe.log_error(title="Lumen Restaurants: receipt logo")
        return b""


def _read(url):
    """A logo kept on this site (/files, /private/files) or in an app
    (/assets). A logo on another website is not fetched: the till's server
    would wait on it while the receipt prints."""
    url = str(url or "").split("?")[0].strip()
    if not url.startswith(("/files/", "/private/files/", "/assets/")):
        return None
    try:
        if url.startswith("/assets/"):
            root = os.path.join(frappe.local.sites_path, "assets")
        else:
            name = frappe.db.get_value("File", {"file_url": url}, "name")
            if name:
                return frappe.get_doc("File", name).get_content()
            root = frappe.get_site_path("public", "files") if url.startswith("/files/") else frappe.get_site_path("private", "files")
        base = os.path.dirname(root) if url.startswith("/assets/") else frappe.get_site_path("public" if url.startswith("/files/") else "")
        # Normalised, not resolved: assets are links into the apps, and a path
        # that climbs out of its folder ("..") is refused.
        path = os.path.normpath(os.path.join(base, url.lstrip("/")))
        if not path.startswith(os.path.normpath(root) + os.sep):
            return None
        if os.path.isfile(path):
            # Confined above: a normalised path inside the site's files or an
            # app's public folder, never one that climbs out of it.
            with open(path, "rb") as f:  # nosemgrep
                return f.read()
    except Exception:
        frappe.log_error(title="Lumen Restaurants: receipt logo")
    return None
