"""
PDF watermarking service — generates personalized watermarked copies for leak tracing.
Uses PyMuPDF (fitz) and Pillow. Output is in-memory bytes, no disk writes.
"""

import io
from typing import Optional

# Zero-width Unicode for invisible fingerprint
ZW_SPACE = "\u200B"      # 0
ZW_NON_JOINER = "\u200C"  # 1
ZW_JOINER = "\u200D"    # separator
BOM = "\uFEFF"          # wrap


def _encode_user_id_binary(user_id: int) -> str:
    """Encode user_id as invisible zero-width Unicode: 200B=0, 200C=1, 200D=separator, FEFF=wrap."""
    bits = bin(user_id)[2:]  # "10110" for 22
    encoded = "".join(ZW_NON_JOINER if b == "1" else ZW_SPACE for b in bits)
    return f"{BOM}{encoded}{BOM}"


def decode_user_id_from_text(text: str) -> Optional[int]:
    """Extract user_id from text containing zero-width fingerprint. Returns None if not found."""
    if not text or BOM not in text:
        return None
    try:
        start = text.index(BOM) + len(BOM)
        end = text.index(BOM, start) if BOM in text[start:] else len(text)
        chunk = text[start:end]
        # Filter to only our chars, split by ZW_JOINER if used
        bits = []
        for c in chunk:
            if c == ZW_SPACE:
                bits.append("0")
            elif c == ZW_NON_JOINER:
                bits.append("1")
            elif c == ZW_JOINER:
                pass  # separator, skip
        if not bits:
            return None
        return int("".join(bits), 2)
    except (ValueError, IndexError):
        return None


def generate_watermarked_pdf(
    original_pdf_path: str,
    user_id: int,
    username: Optional[str] = None,
) -> bytes:
    """
    Generate a personalized watermarked PDF. Returns bytes (in-memory, no disk).
    - Visible: semi-transparent diagonal watermark on each page
    - Invisible: zero-width Unicode fingerprint encoding user_id
    """
    import fitz  # PyMuPDF
    from PIL import Image

    username = username or "unknown"
    watermark_text = f"@{username} | ID:{user_id} | ONE"

    doc = fitz.open(original_pdf_path)
    output_buffer = io.BytesIO()
    new_doc = fitz.open()

    invisible_fingerprint = _encode_user_id_binary(user_id)

    for page_num in range(len(doc)):
        page = doc[page_num]
        # Render at 300 DPI
        mat = fitz.Matrix(300 / 72, 300 / 72)
        pix = page.get_pixmap(matrix=mat, alpha=False)
        img_data = pix.tobytes("png")
        pil_img = Image.open(io.BytesIO(img_data)).convert("RGBA")

        # Draw visible watermark: diagonal, repeated, 45 degrees, white 35% opacity
        from PIL import ImageDraw, ImageFont

        w, h = pil_img.size
        try:
            font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 48)
        except OSError:
            try:
                font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 48)
            except OSError:
                font = ImageFont.load_default()

        fill = (255, 255, 255, int(255 * 0.35))
        step = 220
        watermark_layer = Image.new("RGBA", (w * 2, h * 2), (0, 0, 0, 0))
        wdraw = ImageDraw.Draw(watermark_layer)
        for y in range(0, h * 2, step):
            for x in range(0, w * 2, step):
                wdraw.text((x, y), watermark_text, fill=fill, font=font)
        rotated = watermark_layer.rotate(45, expand=True)
        # Crop to page size, centered
        cx = max(0, (rotated.width - w) // 2)
        cy = max(0, (rotated.height - h) // 2)
        rotated = rotated.crop((cx, cy, cx + w, cy + h))
        if rotated.size != (w, h):
            rotated = rotated.resize((w, h), Image.Resampling.LANCZOS)
        pil_img = Image.alpha_composite(pil_img, rotated)

        # Convert to RGB and get bytes
        pil_rgb = pil_img.convert("RGB")
        img_bytes = io.BytesIO()
        pil_rgb.save(img_bytes, format="PNG")
        img_bytes.seek(0)
        img_data_final = img_bytes.getvalue()

        # Create new page from image
        new_page = new_doc.new_page(width=w, height=h)
        new_page.insert_image(new_page.rect, stream=img_data_final)

        # Add invisible text layer (1pt white at top-left) for leak tracing
        new_page.insert_text(
            fitz.Point(0, 10),
            invisible_fingerprint,
            fontsize=1,
            color=(1, 1, 1),
        )

    doc.close()
    new_doc.save(output_buffer, garbage=4, deflate=True)
    new_doc.close()
    return output_buffer.getvalue()


def render_pdf_pages_as_images(pdf_bytes: bytes) -> list[tuple[str, bytes]]:
    """Render PDF bytes to PNG page images for v3 manual delivery."""
    import fitz  # PyMuPDF

    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    images: list[tuple[str, bytes]] = []
    try:
        for page_index in range(len(doc)):
            page = doc[page_index]
            pix = page.get_pixmap(matrix=fitz.Matrix(2, 2), alpha=False)
            images.append((f"page-{page_index + 1}.png", pix.tobytes("png")))
    finally:
        doc.close()
    return images
