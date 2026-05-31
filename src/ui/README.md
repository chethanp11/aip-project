# AIP Web UI Layer

This directory contains the unified web interface of the AIM Intelligence Platform (AIP), providing dynamic workspace canvases, metric tree explorers, interactive dashboards, and workflow editing interfaces.

## 🎨 Design Systems & Rules
1.  **Pure Vanilla CSS**: Implement a rich, high-quality, harmonious styling system. Avoid using bloated utility frameworks unless explicitly requested. Use curated dark modes, subtle glassmorphic backdrop-filters, custom Google typography, and smooth transitions.
2.  **No Scaffolding Bloat**: Keep dependencies lightweight and focused solely on dynamic web execution.
3.  **Unique IDs**: Ensure every interactive UI node has a unique, descriptive test-id for browser automated validation.


## Analyst Product Navigation

The unified shell renders persona-specific product tiles and sidebar links. Analytics Professional and Business Admin users see PRISM and Research as separate Analyst Action products: PRISM opens report rationalization workflows, while Research opens KMS-grounded context and artifact discovery.
