# Design: PRISM Report Rationalizer Overlap Threshold

## Overview
The PRISM Report Rationalizer screens and analyzes multiple report templates across diverse team domains. A core rationalization function is detecting high query overlaps and identical schemas using a tokenized Jaccard similarity index:

$$\text{Overlap Coefficient} = \frac{|A \cap B|}{|A \cup B|}$$

This document outlines the architectural update that parameterizes the similarity threshold to make the screening engine configurable and dynamic.

## Architectural Changes

### Parameterization of Jaccard Similarity Threshold
Previously, the threshold in `AIP/src/reporting/prism/main.py` was hardcoded to `0.5`. This hardcoding has been replaced by a customizable architecture:
1. **Module Constant**: `DEFAULT_JACCARD_THRESHOLD` is set to `0.5` to maintain perfect backward compatibility with existing tests and clients.
2. **Custom Parameter**: `run_prism_workflow` signature is updated to accept a `threshold: float = DEFAULT_JACCARD_THRESHOLD` argument.
3. **Flexible Evaluation**: The rationalization comparison conditional inside the main loop utilizes the parameterized threshold:
   ```python
   if similarity >= threshold and rep_a['query'] != rep_b['query']:
   ```

## Alignment with Developer Guidelines
This update directly implements the enhancement described in `/develop-reporting-suite.md`:
> Standard threshold trigger is set to $\ge 0.85$ for consolidation suggestions. To adjust the threshold, modify the comparison conditional parameter in `prism/main.py`.

With this parameterization, callers can dynamically pass a higher threshold (such as `0.85`) to trigger strict consolidation suggestions while retaining standard baseline performance.
