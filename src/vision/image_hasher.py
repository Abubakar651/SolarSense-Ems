"""
SolarSense EMS — High-Performance Perceptual Image Hasher
Provides vectorized difference hashing (dHash) and average hashing (aHash)
using NumPy for robust near-duplicate detection.
"""

import numpy as np
from PIL import Image
from pathlib import Path


def compute_dhash(img: Image.Image, hash_size: int = 8) -> int:
    """
    Computes a 64-bit difference hash (dHash).
    Resizes image to (hash_size + 1, hash_size), converts to grayscale,
    and computes horizontal pixel gradients.
    """
    # Convert to grayscale and resize with anti-aliasing
    gray = img.convert("L").resize((hash_size + 1, hash_size), Image.Resampling.BILINEAR)
    pixels = np.asarray(gray, dtype=np.int32)
    # Compare adjacent pixels in each row
    diff = pixels[:, 1:] > pixels[:, :-1]
    # Pack boolean 2D array into a 64-bit integer
    bit_array = diff.flatten()
    hash_int = 0
    for bit in bit_array:
        hash_int = (hash_int << 1) | int(bit)
    return hash_int


def compute_ahash(img: Image.Image, hash_size: int = 8) -> int:
    """
    Computes a 64-bit average hash (aHash).
    Compares pixel values against the mean brightness.
    """
    gray = img.convert("L").resize((hash_size, hash_size), Image.Resampling.BILINEAR)
    pixels = np.asarray(gray, dtype=np.float32)
    avg = pixels.mean()
    diff = pixels > avg
    bit_array = diff.flatten()
    hash_int = 0
    for bit in bit_array:
        hash_int = (hash_int << 1) | int(bit)
    return hash_int


def hamming_distance(h1: int, h2: int) -> int:
    """Computes bitwise Hamming distance between two integer hashes."""
    return bin(h1 ^ h2).count("1")


def is_near_duplicate(h1: int, h2: int, threshold: int = 2) -> bool:
    """Returns True if Hamming distance <= threshold."""
    return hamming_distance(h1, h2) <= threshold
