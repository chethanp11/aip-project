# Design: What-If Scenario Sandbox Financial Boundary Validation

## Overview
The What-If Scenario sandbox projects downstream net interest margins, projected revenues, expenses, and default spreads based on interest rates, asset sizes, and default parameters. This document outlines the design for boundary validation guards added to protect against statistically and financially invalid inputs.

## Architectural Changes

### Financial Boundary Sanity Guards
Previously, standard float inputs inside `AIP/src/business_analytics/what_if_analysis/main.py` were caught via a general `ValueError` try-catch block, but negative parameters (e.g. negative interest rates or assets) were not validated. This resulted in nonsensical negative interest calculations.

To ensure robustness, financial boundary guards have been introduced:
1. **Safety Overrides**:
   - Earning rate (`l_rate`) must be $\ge 0$. If negative, it is overridden to baseline `6.5%`.
   - Resource cost rate (`d_rate`) must be $\ge 0$. If negative, it is overridden to baseline `2.5%`.
   - Total Assets (`total_assets`) must be $> 0$. If zero or negative, it is overridden to baseline `10.0` billion.
   - Defaults rate (`def_rate`) must be $\ge 0$. If negative, it is overridden to baseline `1.5%`.
2. **Implementation Block**:
   ```python
   # Financial boundary sanity checks
   if l_rate < 0:
       l_rate = 6.5
   if d_rate < 0:
       d_rate = 2.5
   if total_assets <= 0:
       total_assets = 10.0
   if def_rate < 0:
       def_rate = 1.5
   ```

## Alignment with Developer Guidelines
This update directly strengthens the robust baseline calculation checks mentioned in `/develop-business-analytics-suite.md`. It guarantees that all net interest margins, spreads, and revenues remain financially coherent and positive under all projection inputs.
