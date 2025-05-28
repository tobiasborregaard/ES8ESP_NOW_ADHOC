from shapely.geometry import LineString
import numpy as np
import time
import math
import random

scale_m_per_px = 15.01 / 867  
area_per_px_m2 = scale_m_per_px ** 2       # m² per pixel
spacing_margin_px = int(1 / scale_m_per_px)

def trilaterate_relative(a, b, c):
    """
    Given distances:
    a = self to neighbor (placed at (a, 0))
    b = self to router
    c = neighbor to router

    Returns: (x, y) coordinates of router relative to self at (0, 0)
    """
    x = (a**2 + b**2 - c**2) / (2 * a)
    y_squared = b**2 - x**2
    if y_squared < 0:
        y = 0  # or raise an error if geometry is impossible
    else:
        y = math.sqrt(y_squared)

    return (x, y)



def angle_between(v1, v2):
    dot = np.dot(v1, v2)
    norms = np.linalg.norm(v1) * np.linalg.norm(v2)
    return math.degrees(math.acos(dot / norms))


def rssi_with_walls(distance_m, n=1.8, d0=1.0,
                    walls_crossed=0, wall_penalty_db=2.3,
                    fading_std_db=2.85, include_fading=True):
    """
    Estimates RSSI at given distance using log-distance path loss model
    with wall attenuation and optional shadow fading.

    Returns:
        RSSI in dBm (typically a negative value)
    """
    if distance_m < d0:
        distance_m = d0

    rssi_1m = -47.29  # Measured or assumed RSSI at 1 meter

    # Log-distance path loss
    distance_loss = 10 * n * math.log10(distance_m / d0)

    # Wall attenuation
    wall_loss = walls_crossed * wall_penalty_db

    # Shadow fading (Gaussian)
    fading = random.gauss(0, fading_std_db) if include_fading else 0

    # Total RSSI
    rssi = rssi_1m - distance_loss - wall_loss - fading
    return rssi

def bresenham_line(x0, y0, x1, y1):
    """Returns list of (x, y) from A to B using Bresenham's algorithm."""
    points = []
    dx = abs(x1 - x0)
    dy = abs(y1 - y0)
    x, y = x0, y0
    sx = -1 if x0 > x1 else 1
    sy = -1 if y0 > y1 else 1
    if dx > dy:
        err = dx / 2.0
        while x != x1:
            points.append((x, y))
            err -= dy
            if err < 0:
                y += sy
                err += dx
            x += sx
    else:
        err = dy / 2.0
        while y != y1:
            points.append((x, y))
            err -= dx
            if err < 0:
                x += sx
                err += dy
            y += sy
    points.append((x1, y1))
    return points, math.sqrt(np.pow(dx,2) + np.pow(dy,2))*scale_m_per_px