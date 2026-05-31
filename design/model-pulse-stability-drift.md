# Design: Model Pulse Population Stability Index (PSI) Drift Thresholds

## Overview
Model Pulse audits prediction accuracy, Population Stability Index (PSI), and feature covariance shifts Month-over-Month (MoM). This document describes the refactoring of drift thresholds inside the Model Pulse module to enforce modular, robust, and standards-compliant alerts.

## Architectural Changes

### Refactoring to PSI-based Alarm Checks
Previously, Month-over-Month warning and critical drift alerts inside `src/data_science_ml/model_pulse/main.py` were calculated directly on raw accuracy shifts (`drift_score`) rather than Population Stability Index (`psi_score`) covariance shifts:
- Alarm triggered if `drift_score >= 0.05`

The module has been refactored to use standard data science thresholds defined on the calculated PSI metric:
1. **Configurable Thresholds**:
   - `PSI_WARNING_THRESHOLD = 0.10`: Triggers warning status on minor distributions shift (e.g. `PSI >= 0.10`).
   - `PSI_CRITICAL_THRESHOLD = 0.25`: Triggers critical status on major distribution shifts requiring auto-retraining workflows.
2. **Refactored Alerts Conditional**:
   - The warning and critical states check `psi_score` against the exposed constants:
     ```python
     drift_detected = psi_score >= PSI_WARNING_THRESHOLD
     drift_status = 'stable'
     if psi_score >= PSI_CRITICAL_THRESHOLD:
         drift_status = 'critical'
     elif psi_score >= PSI_WARNING_THRESHOLD:
         drift_status = 'warning'
     ```

## Alignment with Developer Guidelines
This update conforms directly with the specifications in `/develop-data-science-ml-suite.md`:
> LIVE prediction validation and feature stability thresholds are implemented in `src/data_science_ml/model_pulse/main.py`.
> The default distribution shift alarm is triggered if calculated feature PSI value > 0.25.
> To make the alert system more sensitive (e.g. warning at PSI > 0.10), modify the threshold constants inside `model_pulse/main.py`.
