# Wealth Management Business Context

## Business Scope
Wealth Management supports client advisory, suitability, portfolio management, household goals, financial planning, fee schedules, and relationship coverage. This context is directional metadata only. It must not be treated as factual business data; all client, portfolio, transaction, fee, and planning facts must come from querying `wealthdb`.

## Authorized Users
- `Wealth_Analyst`
- `Wealth_SME`

## Authorized Domains
- Wealth Management
- Client Advisory
- Investment Portfolio Management
- Suitability and Risk Profiling
- Financial Planning and Goals

## Data Authority Rule
Use this context to understand table purpose, joins, and analytical intent. Do not answer factual questions from this file. Query `wealthdb` for all facts.

## Table Metadata

### `wealth_clients`
- Business meaning: Wealth client and household master records.
- Typical use: client segmentation, household-level portfolio context, onboarding and KYC review.
- Key concepts: client identifier, household name, client segment, risk tolerance, investable assets, onboarding date, KYC status.

### `relationship_managers`
- Business meaning: Advisor and relationship-manager coverage information.
- Typical use: book-of-business analysis, advisor workload, office coverage, certification review.
- Key concepts: manager identifier, manager name, office location, certification, book AUM, active households.

### `investment_accounts`
- Business meaning: Wealth investment accounts linked to clients and relationship managers.
- Typical use: account inventory, custodian view, market value by client, account type analysis.
- Key concepts: account identifier, client reference, manager reference, account type, custodian, base currency, market value, opened date.
- Common joins: `wealth_clients` by client identifier; `relationship_managers` by manager identifier.

### `portfolio_holdings`
- Business meaning: Holdings within investment accounts by asset class and security name.
- Typical use: asset allocation, unrealized gain/loss review, concentration analysis.
- Key concepts: account reference, asset class, security name, market value, allocation percentage, unrealized gain/loss.
- Common joins: `investment_accounts` by account identifier.

### `advisory_mandates`
- Business meaning: Client advisory mandates and investment-policy direction.
- Typical use: mandate status review, benchmark alignment, target return and drawdown context.
- Key concepts: client reference, mandate type, start date, benchmark, target return, max drawdown, mandate status.
- Common joins: `wealth_clients` by client identifier.

### `financial_plans`
- Business meaning: Client financial plans and plan-level goal projection metadata.
- Typical use: plan review, retirement or estate planning oversight, next-review scheduling.
- Key concepts: client reference, plan type, planning date, goal amount, projected success, next review date.
- Common joins: `wealth_clients` by client identifier.

### `client_risk_profiles`
- Business meaning: Client suitability and investment risk assessment profiles.
- Typical use: suitability review, risk-score monitoring, liquidity needs assessment, horizon analysis.
- Key concepts: client reference, assessment date, risk score, liquidity need, investment horizon, suitability status.
- Common joins: `wealth_clients` by client identifier.

### `investment_transactions`
- Business meaning: Trades and investment-account transaction records.
- Typical use: transaction review, settlement monitoring, account activity analysis.
- Key concepts: account reference, trade date, transaction type, security name, amount, settlement status.
- Common joins: `investment_accounts` by account identifier.

### `fee_schedules`
- Business meaning: Wealth service tier and advisory fee schedule metadata.
- Typical use: pricing analysis, segment-level fee review, billing frequency context.
- Key concepts: client segment, service tier, annual fee basis points, minimum fee, billing frequency.

### `client_goals`
- Business meaning: Household goals tracked for planning and advisory follow-up.
- Typical use: goal funding progress, priority review, target-date monitoring.
- Key concepts: client reference, goal name, target amount, target date, funded percentage, priority.
- Common joins: `wealth_clients` by client identifier.
