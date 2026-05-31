# AIM Intelligence Platform (AIP) Project Context

## 📌 Overview

The AIM Intelligence Platform (AIP) is an enterprise-grade Analytics Intelligence Platform designed to transform how business users consume intelligence and how analysts create intelligence.

The platform serves as a cognitive layer connecting enterprise data, institutional knowledge, and agentic analytical workflows.

AIP is built around three core principles:

1. Business users should be able to consume intelligence with minimal analyst dependency.
2. Analysts should be able to create intelligence significantly faster through AI-assisted workflows.
3. Enterprise knowledge should become a reusable organizational asset rather than remaining trapped in reports, presentations, and individual expertise.

The platform is organized into three major layers:

### 1. Business Suite

Provides self-service intelligence capabilities for business users.

Modules:

- Dashboards
- Conversational BI
- Proactive Alerts
- Deep Insights
- Scenario Analysis

### 2. Analyst Actions

Provides AI-assisted analytical workflows for analysts.

Actions:

- PRISM
- Research
- Explore Data
- Build Report
- Root Cause Analysis
- Recommend Actions

### 3. Shared Foundation

Provides reusable enterprise capabilities used by both Business Suite and Analyst Actions.

Components:

- Knowledge Management System (KMS)
- Enterprise Data Layer

---

## 🎯 Platform Vision

### Current State

```text
Data
 ↓
Analyst
 ↓
Report
 ↓
Business User
```

### Future State

```text
Knowledge + Data
        ↓
AIP Intelligence Platform
        ↓
Business Intelligence Consumption
        ↓
Business Decisions
```

### Business User Outcomes

- Faster access to information
- Reduced dependency on analysts
- Proactive intelligence
- Better business understanding

### Analyst Outcomes

- Accelerated research
- Faster data exploration
- Automated reporting
- Structured investigations
- Reusable knowledge

---

# 🏢 Business Suite

## 1. Dashboards

### Purpose

Monitor business performance through curated KPI dashboards.

- Static dashboards
- KPI monitoring
- Executive dashboards
- Operational dashboards
- Dashboard catalog
- Dashboard search
- Published report display from `Infra/storage/reports/report_*/index.html`


---

## 2. Conversational BI

### Purpose

Allow business users to ask questions and explore business performance using natural language.

### Capabilities

- Natural language querying
- Metric explanations
- Drill-down conversations
- Follow-up questioning
- Dashboard-aware conversations
- Business-friendly responses

---

## 3. Proactive Alerts

### Purpose

Surface important business changes before users actively search for them.

### Capabilities

- KPI monitoring
- Threshold breaches
- Trend detection
- Anomaly detection
- Alert subscriptions
- Alert history

---

## 4. Deep Insights

### Purpose

Provide AI-generated understanding of business outcomes.

### Capabilities

- Trend interpretation
- Driver analysis
- Risk identification
- Opportunity identification
- Narrative generation
- Supporting evidence generation

---

## 5. Scenario Analysis

### Purpose

Evaluate potential future outcomes under different business assumptions.

### Capabilities

- What-if analysis
- Forecasting
- Impact analysis
- Assumption management
- Scenario comparison
- Sensitivity analysis

---

# 👨‍💻 Analyst Actions

## 1. PRISM

### Purpose

Help analysts rationalize reporting inventories by identifying duplicate reports, overlapping report logic, redundant schemas, and consolidation opportunities.

### Capabilities

- Report inventory screening
- Duplicate report detection
- Query and schema overlap analysis
- Usage pattern interpretation
- Consolidation recommendation generation
- Uploaded report parsing
- Report rationalization evidence packaging

### Primary Sources

- Report catalogs
- Uploaded Excel, HTML, and CSV report artifacts
- Report Builder outputs
- KMS business context

---

## 2. Research

### Purpose

Assist analysts in discovering business context, enterprise knowledge, historical work products, and organizational intelligence.

### Capabilities

- Business glossary search
- Metric definition search
- Data element search
- Knowledge retrieval
- Historical analysis retrieval
- Similar project discovery
- Historical report discovery
- Artifact discovery
- Outcome discovery
- Conversational research experience

### Primary Sources

- KMS
- Historical reports
- Knowledge repositories
- Metadata stores

---

## 3. Explore Data

### Purpose

Provide a workspace for understanding, profiling, and evaluating enterprise datasets.

### Capabilities

- Natural language to SQL
- Query generation
- Query execution
- Data profiling
- Data quality assessment
- Schema exploration
- Distribution analysis
- Missing value analysis
- Sample generation
- Column-level exploration

---

## 4. Build Report

### Purpose

Generate enterprise-grade reports from requirements through publication.

### Capabilities

- Requirement gathering
- Scope definition
- Data modeling
- Analytical execution
- Insight generation
- Visualization generation
- HTML report generation
- Review workflows
- Publication workflows
- Version management

### Outputs

- Requirements package
- Data model artifacts
- Analysis artifacts
- Visualizations
- Final HTML report
- Audit artifacts

---

## 5. Root Cause Analysis

### Purpose

Identify and explain drivers behind business outcomes.

### Capabilities

- Problem framing
- Hypothesis generation
- Driver decomposition
- Segmentation analysis
- Comparative analysis
- Statistical analysis
- Root cause ranking
- Evidence generation
- Narrative generation
- Executive storytelling

### Outputs

- Root causes
- Supporting evidence
- Investigation summary
- Executive-ready storyline
- Confidence assessment

---

## 6. Recommend Actions

### Purpose

Suggest evidence-backed actions based on analytical findings and historical outcomes.

### Capabilities

- Historical pattern retrieval
- Similar case retrieval
- Action recommendations
- Opportunity identification
- Risk identification
- Impact estimation
- Alternative options generation
- Narrative generation
- Executive storytelling

### Outputs

- Recommended actions
- Supporting rationale
- Expected impact
- Risks and trade-offs
- Executive-ready storyline
- Confidence assessment

### Important

Recommend Actions supports decision-making but does not make decisions on behalf of the business.

---

# 🧠 Shared Foundation

## Knowledge Management System (KMS)

### Purpose

Serve as the enterprise intelligence backbone for AIP.

### Responsibilities

- Business glossary
- Metric definitions
- Data definitions
- Business rules
- Historical analyses
- Historical reports
- Artifact repository
- Knowledge graph
- Vector retrieval
- Semantic search
- Context assembly
- Retrieval orchestration

### Technology

- PostgreSQL + pgvector
- Neo4j Knowledge Graph
- Git-managed canonical knowledge assets

### Design Principle

The KMS is both the organizational knowledge repository and the context engine powering all AIP intelligence workflows.

---

## Enterprise Data Layer

### Purpose

Provide governed access to enterprise data assets.

### Responsibilities

- Data connections
- Metadata management
- Query execution
- Data catalog integration
- Governance controls
- Security controls
- Access management

---

# 🏗️ Platform Architecture & Folder Structure

```text
/Users/chethan/GitHub/AIP-Project/
├── src/
│   ├── main.py
│   ├── shared/
│   │   ├── config/
│   │   ├── infra/
│   │   ├── capabilities/
│   │   ├── intelligence.py
│   │
│   ├── kms/
│   │
│   ├── business_suite/
│   │   ├── dashboards/
│   │   ├── conversational_bi/
│   │   ├── proactive_alerts/
│   │   ├── deep_insights/
│   │   └── scenario_analysis/
│   │
│   └── analyst_actions/
│       ├── research/
│       ├── explore_data/
│       ├── build_report/
│       ├── root_cause_analysis/
│       └── recommend_actions/
│
├── design/
│   ├── UX_flows.md
│   ├── product_vision.md
│   ├── system_design.md
│
├── tests/
│
└── Infra/
    ├── docker/
    ├── storage/
    └── secrets/
```

---

# 🔒 Session & Security Parameters


- Role-based access controls govern:
  - Knowledge access
  - Data access
  - Report access
  - Analyst actions
  - Business suite permissions
- KMS retrieval results must be dynamically filtered based on authorized domains and user context.
- Enterprise data access must be dynamically restricted based on approved datasets, tables, and role permissions.
- SME personas maintain governance capabilities over canonical knowledge assets.

---

# ⚙️ Shared Platform Integration Rules

## Infrastructure Access

Workflows must never directly access:

- Raw database drivers
- Local storage paths
- Infrastructure endpoints

All infrastructure access must occur through reusable clients under:

```python
src/shared/infra
```

---

## Capability Design

Capabilities must be:

- Stateless
- Idempotent
- Reusable
- Request-scoped

Capabilities must never maintain session state.

---

## Configuration Management

All configuration values, credentials, storage locations, and infrastructure mappings must be sourced through:

```python
src/shared/config/config.py
```

---

## Knowledge-First Design

Any workflow requiring:

- Business context
- Definitions
- Metrics
- Historical analyses
- Reports
- Organizational intelligence

must retrieve context from KMS before invoking LLM reasoning.

KMS is the authoritative intelligence source across the platform.

---

---

# 🖥️ Unified Platform Experience

## Main Application Shell

The AIP application provides a single unified user experience through a central platform UI hosted under:

```text
src/
```

This serves as the primary entry point into the platform and acts as the orchestration layer for all Business Suite modules, Analyst Actions, and KMS administration capabilities.

The main application shell is responsible for:

- Authentication
- Authorization
- Business selection
- Persona selection
- Navigation
- Context management
- Cross-product orchestration
- Shared notifications
- Shared search
- Session management

Individual products remain modular but are surfaced through a single platform experience.

---

## Platform Modules

The unified platform hosts the following modules:

### Business Suite

- Dashboards
- Conversational BI
- Proactive Alerts
- Deep Insights
- Scenario Analysis

### Analyst Actions

- PRISM
- Research
- Explore Data
- Build Report
- Root Cause Analysis
- Recommend Actions

### Shared Foundation

- KMS Administration & Governance

Each module owns its own workflows, APIs, orchestration, and storage structures while integrating into the common AIP platform shell.

---

# 🔐 Authentication & Persona Selection

Upon login, users are required to select:

### Business

Examples:

- Treasury
- Liquidity Management Services
- Credit Risk
- Regulatory Compliance
- Commercial Banking
- Retail Banking

The selected business establishes the user's operating context.

---

### Persona

Users must select one of the following personas:

#### Business User

Provides access to:

- Dashboards
- Conversational BI
- Proactive Alerts
- Deep Insights
- Scenario Analysis

---

#### Analyst

Provides access to:

- PRISM
- Research
- Explore Data
- Build Report
- Root Cause Analysis
- Recommend Actions

---

#### Admin / SME

Provides access to:

- KMS Governance
- Knowledge Review
- Knowledge Approval
- Knowledge Publishing
- User Administration
- Platform Configuration
- Business Configuration

---

# 🧠 Business-Aware Context Management

The selected business context dynamically controls:

## Knowledge Access

KMS retrieval is automatically scoped to:

- Business-specific glossaries
- Business-specific metrics
- Business-specific reports
- Business-specific analyses
- Business-specific knowledge assets

Users retrieve only knowledge approved for their selected business.

---

## Data Access

Enterprise Data Layer access is automatically scoped to:

- Business-approved databases
- Business-approved schemas
- Business-approved tables
- Business-approved datasets

Cross-business access is governed through RBAC and platform controls.

---

## Context-Aware Intelligence

All AI workflows automatically inherit:

- Selected business
- User persona
- Business-specific knowledge
- Business-specific metrics
- Business-specific reporting assets
- Business-specific analytical history

This ensures all generated outputs remain relevant to the user's operating context.

---

# 📦 Output Management

All outputs generated by AIP are stored outside the application runtime and managed through Infra.

```text
Infra/
```

This ensures complete separation between:

- Application code
- Infrastructure services
- Generated outputs
- Knowledge assets
- Execution artifacts

---

## Output Categories

Examples include:

### Reports

```text
storage/reports/
```

### Chats from Conv BI

```text
storage/chats/
```
### Alerts from Proactive Alerts

```text
storage/alerts/
```

### Deep Insights from Deep Insights

```text
storage/insights/
```
---

### Analyses

```text
storage/analyses/
```

- Root cause investigations
- Recommendations
- Scenario analyses
- Research outputs

---

### Knowledge Assets

Lives in PostGres+pgvector and neo4j 

---

### Logs & Audit

```text
storage/logs/
storage/audit/
```

- User actions
- Workflow execution logs
- Publication history
- Governance activity

---

## Design Principle

Application code lives inside `src/`.

Infrastructure services live inside `Infra/`.

Generated intelligence lives inside `Infra/`.

Knowledge lives inside KMS.

Users experience a single platform, while the underlying architecture remains modular, governed, and business-aware.

---

# 🎯 Core Platform Principle

**Business users consume intelligence.**

**Analysts create intelligence.**

**KMS institutionalizes intelligence.**

AIP continuously transforms enterprise data, knowledge, reports, analyses, and historical outcomes into reusable organizational intelligence.