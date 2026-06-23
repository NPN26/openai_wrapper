This is a [Next.js](https://nextjs.org) project bootstrapped with [`create-next-app`](https://nextjs.org/docs/app/api-reference/cli/create-next-app).

## Project Overview

This project is dedicated to testing features of an AI chat application. It integrates a modern Next.js frontend with a sophisticated FastAPI backend powered by LangGraph to explore advanced conversational AI capabilities. Key features being tested include multi-turn context retention, financial domain guardrails, autonomous database querying via a ReAct agent, and dynamic conversation state management.

## Getting Started

Run the FastAPI backend on port 8000:

```bash
source .venv/bin/activate
python3 -m uvicorn api.index:app --reload --port 8000
```

Then run the Next.js frontend on port 3000:

```bash
cd frontend
# then
npm run dev
# or
yarn dev
# or
pnpm dev
# or
bun dev
```

Open [http://localhost:3000](http://localhost:3000) with your browser to see the result.

Requests to `/api/*` are proxied to `http://localhost:8000` by default. To use a different backend URL, set `BACKEND_URL` before starting the frontend:

```bash
BACKEND_URL=http://localhost:8000 npm run dev
```

This project uses [`next/font`](https://nextjs.org/docs/app/building-your-application/optimizing/fonts) to automatically optimize and load [Geist](https://vercel.com/font), a new font family for Vercel.

## AI Agent Architecture (Backend)

The backend is powered by a **LangGraph** state machine that manages conversation memory, context routing, and database interactions. 

### Graph Workflow
1. **Follow-Up Detection**: On subsequent turns, the `follow_up_node` determines if the user's query requires context from previous messages.
2. **History & Rewriter**: If it is a follow-up, the `history_and_rewriter_node` rewrites the query to be self-contained and identifies relevant past turns to inject into the agent's context.
3. **Financial Guardrails**: The `guardrail_node` classifies the query into one of 11 predefined financial domains. If the confidence score is ≤ 0.25, the agent safely declines to answer (`guardrail_end_node`).
4. **ReAct Agent**: The core `agent_node` uses an LLM to reason through the user's request and call tools to fetch data.
5. **Fact Compressor**: After the agent responds, the `compressor_node` extracts key financial facts from the interaction and saves them to the state ledger for future recall.

*Note: The graph uses a `PostgresSaver` checkpointer (if `POSTGRES_URI` is configured) to persist conversation state across sessions.*

### Available Tools
The agent is equipped with the following tools to interact with the database and its own memory:
- **`list_tables`**: Returns a high-level summary of all available database tables to help the agent plan its queries.
- **`get_table_schema`**: Fetches detailed schemas (columns, types, descriptions) for specific tables to ensure accurate SQL generation.
- **`db_query`**: Executes read-only (`SELECT`) SQL queries against the database and returns the results.
- **`recall_financial_facts`**: Retrieves the ledger of financial facts accumulated during the current conversation.

## Database Schema

The database is structured as a financial data warehouse with dimension, fact, and sub-ledger tables. 

### Table Overview

- **`customers`**: Customer master data for revenue, AR, credit risk, and sales analytics.
  - *Key Joins & Attributes*: `id` (surrogate), `id_external` (business code), `parent_customer_id` (hierarchy). Joins: `invoices`, `accounts_receivable`.

- **`suppliers`**: Supplier master data for procurement spend, AP, and vendor risk analytics.
  - *Key Joins & Attributes*: `id` (surrogate), `id_external` (business code), `parent_supplier_id` (hierarchy). Joins: `accounts_payable`, `purchase_registers`, `purchase_orders`.

- **`invoices`**: Transactional fact table for customer invoices (Income Statement revenue).
  - *Key Joins & Attributes*: Joins: `customers`, `invoice_lines`, `accounts_receivable`.

- **`invoice_lines`**: Line-level detail for customer invoices (item revenue, quantity, tax).
  - *Key Joins & Attributes*: Joins: `invoices`, `inventory_items`.

- **`accounts_receivable`**: Snapshot-based outstanding customer receivables (Balance Sheet metric).
  - *Key Joins & Attributes*: Joins: `customers`, `invoices`.

- **`purchase_orders`**: Transactional fact table for purchase orders (procurement commitments).
  - *Key Joins & Attributes*: Joins: `suppliers`, `purchase_order_lines`, `goods_receipt_notes`.

- **`purchase_order_lines`**: Line-level detail for purchase orders (quantities, pricing, delivery).
  - *Key Joins & Attributes*: Joins: `purchase_orders`, `inventory_items`.

- **`purchase_registers`**: ERP procurement exports with line-level detail (Income Statement expense).
  - *Key Joins & Attributes*: Joins: `suppliers`. Primary metric: AED-converted line total.

- **`accounts_payable`**: Snapshot-based outstanding supplier payables (Balance Sheet metric).
  - *Key Joins & Attributes*: Joins: `suppliers`.

### Important Querying Notes (For the AI Agent)
- **Balance Sheet vs. Income Statement**: Sub-ledgers (`accounts_receivable`, `accounts_payable`) are snapshot-based balance sheet metrics. Do not apply start-date filters to them; use the liability/recognition date as the cutoff. Fact tables (`invoices`, `purchase_registers`) are period-scoped income statement metrics.
- **Hierarchies**: Both `customers` and `suppliers` feature self-referencing foreign keys (`parent_customer_id`, `parent_supplier_id`) to roll up child accounts/subsidiaries to their parent for group-level exposure reporting.
- **Surrogate vs. Business Keys**: Always use `id_external` for business-facing outputs. The internal `id` is strictly a surrogate key used for joining tables.
- **Ratio KPIs (DSO/DPO)**: When calculating ratio KPIs like Days Sales Outstanding (DSO) or Days Payable Outstanding (DPO), combine sub-ledgers and fact tables in separate CTEs rather than direct joins.
- **Currency**: The primary amount metric in `purchase_registers` is the AED-converted line total. Always label spend aggregations explicitly as AED.

## Learn More

To learn more about Next.js, take a look at the following resources:

- [Next.js Documentation](https://nextjs.org/docs) - learn about Next.js features and API.
- [Learn Next.js](https://nextjs.org/learn) - an interactive Next.js tutorial.

You can check out [the Next.js GitHub repository](https://github.com/vercel/next.js) - your feedback and contributions are welcome!

## Deploy on Vercel

The easiest way to deploy your Next.js app is to use the [Vercel Platform](https://vercel.com/new?utm_medium=default-template&filter=next.js&utm_source=create-next-app&utm_campaign=create-next-app-readme) from the creators of Next.js.

Check out our [Next.js deployment documentation](https://nextjs.org/docs/app/building-your-application/deploying) for more details.