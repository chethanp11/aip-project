# Compliance Business Context

## Business Scope
Compliance manages regulatory obligations, controls, reviews, issues, evidence, and remediation tracking. This context is directional metadata only. It must not be treated as factual business data; all control statuses, review results, issue counts, dates, and client or transaction facts must come from querying `compliancedb`.

## Authorized Users
- `Compliance_Analyst`
- `Compliance_SME`

## Authorized Domains
- Regulatory Compliance
- Compliance Controls
- Compliance Assurance
- Issue and Remediation Management
- Customer and Transaction Compliance Review

## Data Authority Rule
Use this context to understand table purpose, joins, and analytical intent. Do not answer factual questions from this file. Query `compliancedb` for all facts.

## Table Metadata

### `corporate_clients`
- Business meaning: Corporate customer reference data used for compliance review and client-level monitoring.
- Typical use: customer segmentation, compliance scope identification, customer-related issue review.
- Key concepts: client identifier, client name, segment, relationship attributes, compliance-relevant customer metadata.

### `transactions`
- Business meaning: Transaction activity available for compliance review and monitoring workflows.
- Typical use: transaction review, customer activity assessment, exception investigation.
- Key concepts: transaction date, amount, transaction type, account/customer reference, currency where available.

### `regulatory_obligations`
- Business meaning: Inventory of regulatory requirements applicable to compliance operations.
- Typical use: obligation coverage, jurisdiction mapping, ownership review, filing/control planning.
- Key concepts: regulation, jurisdiction, obligation area, effective date, filing frequency, owner group, status.

### `compliance_controls`
- Business meaning: Controls mapped to regulatory obligations.
- Typical use: control inventory, control ownership, testing cadence, effectiveness assessment.
- Key concepts: obligation reference, control name, control type, frequency, control owner, last tested date, effectiveness rating.
- Common joins: `regulatory_obligations` by obligation identifier.

### `compliance_reviews`
- Business meaning: Review and testing outcomes for compliance controls.
- Typical use: pass/exception analysis, review evidence tracking, reviewer activity, review period reporting.
- Key concepts: control reference, review period, reviewer, review date, result, evidence reference.
- Common joins: `compliance_controls` by control identifier.

### `compliance_issues`
- Business meaning: Open and remediated issues identified against compliance controls.
- Typical use: issue aging, remediation status, severity mix, owner accountability.
- Key concepts: control reference, severity, issue summary, opened date, due date, remediation owner, status.
- Common joins: `compliance_controls` by control identifier.
