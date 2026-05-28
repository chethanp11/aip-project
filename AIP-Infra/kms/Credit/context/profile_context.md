# Credit Business Context

## Business Scope
Credit manages borrower exposure, credit facilities, internal ratings, delinquency events, portfolio quality, and borrower-level risk monitoring. This context is directional metadata only. It must not be treated as factual business data; all exposure, rating, delinquency, account, and transaction facts must come from querying `creditdb`.

## Authorized Users
- `Credit_Analyst`
- `Credit_SME`

## Authorized Domains
- Credit Portfolio Risk
- Borrower and Facility Monitoring
- Credit Exposure Management
- Delinquency and Collections Oversight
- Portfolio Quality Review

## Data Authority Rule
Use this context to understand table purpose, joins, and analytical intent. Do not answer factual questions from this file. Query `creditdb` for all facts.

## Table Metadata

### `corporate_clients`
- Business meaning: Corporate borrower and client reference data.
- Typical use: borrower segmentation, client-level exposure review, relationship-level credit analysis.
- Key concepts: client identifier, client name, segment, relationship attributes, borrower metadata.

### `accounts`
- Business meaning: Account-level balance records that may support borrower exposure analysis.
- Typical use: account balance review, account type mix, branch or currency concentration.
- Key concepts: account identifier, account type, branch, currency, balance, client/customer reference where available.

### `transactions`
- Business meaning: Transaction activity supporting borrower behavior and repayment analysis.
- Typical use: cash flow activity review, borrower transaction behavior, activity monitoring.
- Key concepts: transaction date, amount, transaction type, account/customer reference, currency where available.

### `credit_facilities`
- Business meaning: Credit lines, loans, and facilities extended to borrowers.
- Typical use: limit utilization, outstanding balance review, maturity schedule, portfolio segmentation.
- Key concepts: client reference, facility type, approved limit, outstanding balance, currency, origination date, maturity date, portfolio segment.

### `credit_risk_ratings`
- Business meaning: Internal credit risk ratings and risk parameter assessments for facilities.
- Typical use: rating distribution, probability-of-default review, loss-given-default review, watchlist monitoring.
- Key concepts: facility reference, rating date, internal rating, probability of default, loss given default, watchlist flag.
- Common joins: `credit_facilities` by facility identifier.

### `delinquency_events`
- Business meaning: Delinquency and collection events tied to credit facilities.
- Typical use: days-past-due analysis, collection status, amount-past-due monitoring, early warning review.
- Key concepts: facility reference, event date, days past due, amount past due, collection status.
- Common joins: `credit_facilities` by facility identifier.
