"""
SolarSense EMS — Deep File-by-File Image Inspector & Normalizer
Performs comprehensive image audits: color mode analysis, channel conversion,
brightness/contrast statistics, and aspect-ratio preserving standardization.
"""

import numpy as np
from PIL import Image, ImageOps
from pathlib import Path


def safe_convert_to_rgb(img: Image.Image) -> Image.Image:
    """
    Safely converts any image format (RGBA, Palette, CMYK, Grayscale)
    into a standardized 3-channel RGB image.
    Handles transparency by compositing over a neutral clean background.
    """
    if img.mode == "RGB":
        return img.copy()

    if img.mode in ("RGBA", "LA") or (img.mode == "P" and "transparency" in img.info):
        # Composite transparent images over a neutral background
        rgba = img.convert("RGBA")
        background = Image.new("RGBA", rgba.size, (240, 240, 240, 255))
        composed = Image.alpha_composite(background, rgba)
        return composed.convert("RGB")

    if img.mode == "CMYK":
        return img.convert("RGB")

    if img.mode in ("L", "P", "1"):
        return img.convert("RGB")

    return img.convert("RGB")


def letterbox_resize(
    img: Image.Image,
    target_size: tuple[int, int] = (512, 512),
    fill_color: tuple[int, int, int] = (128, 128, 128)
) -> Image.Image:
    """
    Resizes an image to target_size (width, height) while strictly preserving
    aspect ratio. Padds boundaries with a neutral fill_color using high-quality
    Lanczos resampling.
    """
    target_w, target_h = target_size
    orig_w, orig_h = img.size

    if orig_w == 0 or orig_h == 0:
        raise ValueError("Invalid image dimensions: width or height is 0")

    scale = min(target_w / orig_w, target_h / orig_h)
    new_w = max(1, int(orig_w * scale))
    new_h = max(1, int(orig_h * scale))

    resized = img.resize((new_w, new_h), Image.Resampling.LANCZOS)
    canvas = Image.new("RGB", (target_w, target_h), fill_color)

    offset_x = (target_w - new_w) // 2
    offset_y = (target_h - new_h) // 2
    canvas.paste(resized, (offset_x, offset_y))

    return canvas


def inspect_single_image(file_path: Path):
    """
    Deep inspection of a single image file.
    Returns a dictionary of technical properties or raises an error if corrupt.
    """
    try:
        # Integrity check
        with Image.open(file_path) as im:
            im.verify()

        # Reopen for actual reading
        with Image.open(file_path) as im:
            w, h = im.size
            mode = im.mode
            fmt = im.format
            file_size_kb = round(file_path.stat().st_size / 1024, 2)
            aspect_ratio = round(w / h, 3)

            # Compute luminance metrics
            gray = im.convert("L")
            arr = np.asarray(gray, dtype=np.float32)
            mean_brightness = round(float(arr.mean()), 2)
            std_contrast = round(float(arr.std()), 2)

            # Check if degenerate (blank, pure black, pure white)
            is_degenerate = (std_contrast < 2.0) or (mean_brightness < 5.0) or (mean_brightness > 250.0)

            return {
                "valid": True,
                "error": None,
                "width": w,
                "height": h,
                "aspect_ratio": aspect_ratio,
                "mode": mode,
                "format": fmt,
                "size_kb": file_size_kb,
                "brightness": mean_brightness,
                "contrast": std_contrast,
                "degenerate": is_degenerate
            }
    except Exception as e:
        return {
            "valid": False,
            "error": str(e),
            "width": 0,
            "height": 0,
            "aspect_ratio": 0.0,
            "mode": "UNKNOWN",
            "format": "UNKNOWN",
            "size_kb": 0.0,
            "brightness": 0.0,
            "contrast": 0.0,
            "degenerate": True
        }
