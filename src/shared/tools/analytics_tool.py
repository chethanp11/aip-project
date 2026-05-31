"""
Time-series and statistical analytics telemetry tools.
"""

import math
from typing import Dict, Any, List


def calculate_trend_diagnostics(time_series_data: List[Dict[str, Any]], date_col: str, val_col: str) -> Dict[str, Any]:
    """Computes pure-Python linear regression slopes, R-squared values, standard deviation,
    and Z-score anomalies for numerical time-series arrays.

    Args:
        time_series_data: List of dictionary records.
        date_col: Name of the date/timestamp column.
        val_col: Name of the numerical value column.

    Returns:
        A dictionary containing statistical metrics, regression outputs, and anomaly alerts.
    """
    if not time_series_data or len(time_series_data) < 2:
        return {
            'has_trend': False,
            'data_points': len(time_series_data),
            'slope': 0.0,
            'r_squared': 0.0,
            'mean': 0.0,
            'std_dev': 0.0,
            'anomalies': []
        }

    # Extract clean pairs of (x, y) where x is simple index (1..N) and y is float value
    cleaned_points = []
    for idx, r in enumerate(time_series_data):
        val = r.get(val_col)
        date_val = r.get(date_col) or f"index_{idx}"
        try:
            val_float = float(val) if val is not None else 0.0
            cleaned_points.append({'x': idx + 1, 'y': val_float, 'date': date_val})
        except (ValueError, TypeError):
            continue

    n = len(cleaned_points)
    if n < 2:
        return {
            'has_trend': False,
            'data_points': n,
            'slope': 0.0,
            'r_squared': 0.0,
            'mean': 0.0,
            'std_dev': 0.0,
            'anomalies': []
        }

    sum_x = sum(p['x'] for p in cleaned_points)
    sum_y = sum(p['y'] for p in cleaned_points)
    mean_x = sum_x / n
    mean_y = sum_y / n

    # Linear Regression Lease-Squares calculation
    num = 0.0
    den = 0.0
    for p in cleaned_points:
        num += (p['x'] - mean_x) * (p['y'] - mean_y)
        den += (p['x'] - mean_x) ** 2

    slope = num / den if den != 0.0 else 0.0
    intercept = mean_y - slope * mean_x

    # R-squared & Standard Deviation
    sst = sum((p['y'] - mean_y) ** 2 for p in cleaned_points)
    ssr = sum((p['y'] - (slope * p['x'] + intercept)) ** 2 for p in cleaned_points)
    r_squared = 1.0 - (ssr / sst) if sst != 0.0 else 0.0
    
    variance = sst / (n - 1) if n > 1 else 0.0
    std_dev = math.sqrt(variance)

    # Z-Score Anomaly detection (where absolute Z-score > 1.5)
    anomalies = []
    for idx, p in enumerate(cleaned_points):
        if std_dev > 0.0:
            z_score = (p['y'] - mean_y) / std_dev
            if abs(z_score) > 1.5:
                anomalies.append({
                    'index': idx,
                    'date': p['date'],
                    'value': p['y'],
                    'z_score': round(z_score, 3),
                    'severity': 'high' if abs(z_score) > 2.0 else 'moderate'
                })

    return {
        'has_trend': True,
        'data_points': n,
        'slope': round(slope, 4),
        'intercept': round(intercept, 4),
        'r_squared': round(r_squared, 4),
        'mean': round(mean_y, 4),
        'std_dev': round(std_dev, 4),
        'anomalies': anomalies
    }
