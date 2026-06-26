## models.py
from sqlmodel import Column, ForeignKey, Index, Relationship, SQLModel, Field, JSON, Session, String, Text, select, func
from datetime import datetime, date
from typing import Optional, List, Any


class Customers(SQLModel, table=True):
    """
    Python class definition for the Customer master data entity.
    This dimension table stores customer master data and serves as the central
    source of truth for Sales, Accounts Receivable (AR), credit management,
    and customer segmentation analytics across the financial platform.
    """
    __tablename__ = "customers"
    __table_args__ = {
        "comment": (
            "Customer master data dimension — the authoritative reference for all customer-facing "
            "financial analysis including revenue, receivables, credit risk, and sales performance. "
            "Each row represents one customer entity. "
            "KEY JOINS: invoices.customer_id = customers.id for revenue and billing analysis; "
            "accounts_receivable.customer_id = customers.id for AR aging, DSO, and collections; "
            "sales_orders.customer_id = customers.id for order pipeline and fulfillment metrics. "
            "Use id_external as the business-facing customer code in result sets — "
            "id is the internal surrogate key used only for joining. "
            "HIERARCHY: parent_customer_id is a self-referencing FK — use it to roll up child accounts "
            "to their parent for group-level exposure reporting."
        )
    }

    id: Optional[int] = Field(default=None, primary_key=True, description="System-generated internal primary key.")

    id_external: Optional[str] = Field(default=None, unique=True, description="Business-facing external customer code (e.g., 'CUST001'). Use this field for display, source reconciliation, and lookup context; use customers.id as the default join key after ingestion.")

    ingestion_log_id: Optional[int] = Field(default=None, foreign_key="data_ingestion_logs.id", description="Reference to the data ingestion job that created or updated this record.")

    source_system_id: Optional[str] = Field(default=None, max_length=50, index=True, description="Identifier of the ERP or CRM system that provided this record.")

    source_primary_key: Optional[str] = Field(default=None, max_length=100, description="Original primary key of the customer record in the source system.")

    parent_customer_id: Optional[int] = Field(default=None, foreign_key="customers.id", description="Self-referencing foreign key representing hierarchical customer relationships (e.g., parent company).")

    name: Optional[str] = Field(default=None, max_length=255, description="Customer's legal or registered business name.")

    address: Optional[str] = Field(default=None, description="Full primary business address of the customer.")

    city: Optional[str] = Field(default=None, max_length=100, description="City where the customer is located.")

    region: Optional[str] = Field(default=None, max_length=100, description="Geographic region or internal sales region associated with the customer.")

    country: Optional[str] = Field(default=None, max_length=100, description="Country where the customer is located.")

    email: Optional[str] = Field(default=None, max_length=255, description="Primary contact email address for the customer.")

    phone: Optional[str] = Field(default=None, max_length=50, description="Primary contact phone number for the customer.")

    contact_details: Optional[Any] = Field(default=None, sa_type=JSON, description="JSON field containing additional contact information such as secondary emails, phone numbers, or contact persons.")

    language_preference: Optional[str] = Field(default=None, max_length=50, description="Preferred language for communication with the customer.")

    document_currency: Optional[str] = Field(default="AED", max_length=3, description="Default transaction currency used for invoices and financial documents.")

    credit_limit: Optional[float] = Field(default=None, description="Maximum credit amount allowed for the customer before blocking new transactions (in document currency).")

    credit_control_area: Optional[str] = Field(default=None, max_length=20, description="ERP credit control grouping used for managing credit risk and credit limits.")

    is_credit_blocked: bool = Field(default=False, description="Flag indicating whether the customer is blocked from creating new sales orders due to credit risk.")

    payment_terms: Optional[str] = Field(default=None, max_length=100, description="Payment terms description (e.g., 'Net 30').")
    
    payment_terms_days: Optional[int] = Field(default=None, description="Number of days allowed for payment according to the payment terms.")

    risk_category: Optional[str] = Field(default=None, max_length=50, description="Credit risk category assigned to the customer.")

    dunning_procedure: Optional[str] = Field(default=None, max_length=50, description="Collections or dunning procedure used for overdue receivables.")

    business_unit: Optional[str] = Field(default=None, max_length=100, description="Internal business unit responsible for managing the customer relationship.")

    industry: Optional[str] = Field(default=None, max_length=100, description="Industry sector the customer operates in.")

    industry_code: Optional[str] = Field(default=None, max_length=50, description="Standardized industry classification code.")

    customer_category: Optional[str] = Field(default=None, max_length=100, description="High-level classification of the customer (e.g., distributor, retailer, enterprise).")

    customer_group: Optional[str] = Field(default=None, max_length=100, description="Sales or marketing grouping used for reporting and segmentation.")

    customer_segment: Optional[str] = Field(default=None, max_length=100, description="Detailed sales or marketing segment classification.")

    customer_type: Optional[str] = Field(default=None, max_length=50, description="Operational classification of the customer (e.g., B2B, B2C).")

    tax_id: Optional[str] = Field(default=None, max_length=50, description="Government-issued tax identification number.")

    vat_registration_number: Optional[str] = Field(default=None, max_length=50, description="VAT or GST registration number used for tax reporting.")

    is_active: bool = Field(default=True, description="Boolean active-status flag for the customer dimension. Use this field for active-customer KPIs after ingestion. Do not assume supplier_status or inventory state fields follow the same convention.")

    salesperson_name: Optional[str] = Field(default=None, max_length=255, description="Primary salesperson responsible for managing this customer account.")

    acquisition_date: Optional[datetime] = Field(default=None, description="Date when the customer relationship was established.")

class AccountsPayable(SQLModel, table=True):
    """
    Python class definition for the Accounts Payable sub-ledger entity.
    This table stores outstanding supplier payable obligations as a snapshot-based 
    balance sheet metric, representing a point-in-time stock of unpaid liabilities.
    """
    __tablename__ = "accounts_payable"
    __table_args__ = {
        "comment": (
            "Snapshot-based accounts payable sub-ledger storing outstanding supplier payable obligations. "
            "BALANCE SHEET metric — represents a point-in-time stock of unpaid liabilities, not a flow. "
            "Apply no start date filter; use the liability recognition date as the cutoff, not the due date. "
            "KEY JOINS: accounts_payable.supplier_id = suppliers.id for supplier-level liability and payment analysis. "
            "For DPO and similar ratio KPIs, use a sum of open balances as the numerator — never an average."
        )
    }

    id: Optional[int] = Field(default=None, primary_key=True, description="System-generated internal primary key.")

    id_external: Optional[str] = Field(default=None, max_length=100, description="External identifier of the payable document from the source ERP or accounting system (e.g., supplier invoice number).")

    supplier_id: Optional[int] = Field(default=None, foreign_key="suppliers.id", description="Foreign key referencing suppliers.id for the supplier on the payable.")

    expense_id: Optional[int] = Field(default=None, foreign_key="expenses.id", description="Foreign key referencing the originating expense record associated with this payable.")

    ingestion_log_id: Optional[int] = Field(default=None, foreign_key="data_ingestion_logs.id", description="Reference to the data ingestion job that created or updated this record.")

    transaction_date: Optional[datetime] = Field(default=None, description="Date when the payable liability was recognized (invoice booking date). Use this column — not due_date — for balance sheet cutoff queries (e.g., WHERE transaction_date <= '2025-03-31').")

    due_date: Optional[datetime] = Field(default=None, description="Date by which payment to the supplier is due. Use for aging analysis (days past due = snapshot_or_today - due_date). Do NOT use as a cutoff filter for AP balance queries — use transaction_date instead.")

    snapshot_date: Optional[datetime] = Field(default=None, description="Point-in-time reporting date for this AP record. All balance sheet AP queries must filter on this column using MAX(snapshot_date) <= cutoff_date. Do NOT apply a start_date filter — AP is a stock metric, not a flow.")

    last_payment_date: Optional[datetime] = Field(default=None, description="Date when the most recent payment was made toward this payable.")

    amount: Optional[float] = Field(default=None, description="Total payable amount including tax before payments or adjustments.")

    currency: Optional[str] = Field(default=None, max_length=3, description="Currency in which the payable transaction is recorded. When returning AED-denominated aggregates, label them explicitly as AED.")

    open_amount: Optional[float] = Field(default=None, description="Remaining unpaid balance of the payable. Primary metric for AP balance, DPO numerator, and supplier liability analysis. Filter open_amount > 0 to exclude fully paid invoices in balance queries, and use SUM(open_amount) rather than AVG(open_amount) for portfolio-level ratios.")

    paid_amount: Optional[float] = Field(default=None, description="Total amount paid toward this payable.")

    tax_amount: Optional[float] = Field(default=None, description="Tax component included in the payable amount.")

    discount_amount: Optional[float] = Field(default=None, description="Discounts applied to the payable, such as early payment discounts.")

    write_off_amount: Optional[float] = Field(default=None, description="Amount written off from the payable due to reconciliation or accounting adjustments.")

    adjustment_amount: Optional[float] = Field(default=None, description="Manual accounting adjustments applied to the payable balance.")

    status: Optional[str] = Field(default=None, max_length=50, description="Current status of the payable document (e.g., Open, Paid, Partially Paid, Cancelled).")

    payment_terms: Optional[str] = Field(default=None, max_length=100, description="Payment terms description associated with the payable (e.g., 'Net 30').")

    payment_terms_days: Optional[int] = Field(default=None, description="Number of days allowed for payment according to the payable terms.")

    reference_number: Optional[str] = Field(default=None, max_length=100, description="Reference number associated with the payable transaction such as the supplier invoice number.")

    gl_account: Optional[str] = Field(default=None, max_length=50, description="General ledger account used for posting the payable transaction.")

    company_code: Optional[str] = Field(default=None, max_length=50, description="Legal entity or company code responsible for the payable.")

    profit_center: Optional[str] = Field(default=None, max_length=50, description="Profit center associated with the transaction if applicable.")

    cost_center: Optional[str] = Field(default=None, max_length=50, description="Cost center responsible for the expense or payable transaction.")

    aging_bucket: Optional[str] = Field(default=None, max_length=50, description="Pre-computed AP aging category (e.g., '0–30 Days', '31–60 Days', 'Not Due'). Can be used directly for aging reports or recomputed from (CURRENT_DATE - due_date) for custom buckets.")

    payment_block: Optional[str] = Field(default=None, max_length=50, description="Flag or code indicating whether the payable is blocked from payment due to validation or approval issues.")

    description: Optional[str] = Field(default=None, description="Narrative description or memo associated with the payable transaction.")

    created_at: Optional[datetime] = Field(default=None, description="Timestamp when the payable record was created.")

    updated_at: Optional[datetime] = Field(default=None, description="Timestamp when the payable record was last updated.")
    
class AccountsReceivable(SQLModel, table=True):
    """
    Python class definition for the Accounts Receivable sub-ledger entity.
    This table stores outstanding customer receivable documents as a snapshot-based 
    balance sheet metric, representing a point-in-time stock of unpaid obligations.
    """
    __tablename__ = "accounts_receivable"
    __table_args__ = {
        "comment": (
            "Snapshot-based accounts receivable sub-ledger storing outstanding customer receivable documents. "
            "BALANCE SHEET metric — represents a point-in-time stock of unpaid obligations, not a flow. "
            "Apply no start date filter; query against the relevant snapshot to get the correct period-end position. "
            "KEY JOINS: accounts_receivable.customer_id = customers.id for customer-level exposure analysis; "
            "accounts_receivable.invoice_id = invoices.id to link receivables back to originating billing documents. "
            "For DSO and similar ratio KPIs, combine this table with invoices in separate CTEs — never join them directly for ratio calculations. "
            "For average days past due and exposure KPIs, prefer balance-weighted logic when the intent is to measure cash at risk."
        )
    }

    id: Optional[int] = Field(default=None, primary_key=True, description="System-generated internal primary key.")

    customer_id: Optional[int] = Field(default=None, foreign_key="customers.id", description="Foreign key referencing customers.id for the customer responsible for the receivable.")

    invoice_id: Optional[int] = Field(default=None, foreign_key="invoices.id", description="Foreign key referencing invoices.id for the originating invoice document.")

    ingestion_log_id: Optional[int] = Field(default=None, foreign_key="data_ingestion_logs.id", description="Reference to the data ingestion job that created or updated this record.")

    billing_date: Optional[datetime] = Field(default=None, description="Date the invoice or receivable document was originally issued. Use for determining when the receivable was created, not for aging calculations (use due_date and snapshot_date for aging).")

    due_date: Optional[datetime] = Field(default=None, description="Payment due date. For aging analysis: compute (snapshot_date::date - due_date::date) to get days past due. Positive = overdue, negative or zero = not yet due.")

    amount: Optional[float] = Field(default=None, description="Total invoice amount including tax before payments.")

    outstanding_amount: Optional[float] = Field(default=None, description="Remaining unpaid balance as of the snapshot_date. Primary metric for AR aging, DSO numerator, and concentration analysis. Use SUM(outstanding_amount) for total AR balance.")

    paid_amount: Optional[float] = Field(default=None, description="Cumulative amount collected against this receivable as of the snapshot_date. This is a running total, not a period-specific cash flow — cannot be used to determine collections during a specific date range without a payment date column.")

    tax_amount: Optional[float] = Field(default=None, description="Portion of the invoice amount attributable to tax.")

    discount_amount: Optional[float] = Field(default=None, description="Early payment or commercial discounts applied to the receivable.")

    adjustment_amount: Optional[float] = Field(default=None, description="Manual financial adjustments applied to the receivable balance.")

    currency: Optional[str] = Field(default=None, max_length=3, description="Currency in which the receivable transaction was recorded.")

    status: Optional[str] = Field(default=None, max_length=50, description="Current status of the receivable document (e.g., Open, Paid, Partially Paid).")

    aging_bucket: Optional[str] = Field(default=None, max_length=50, description="Pre-computed AR aging category (e.g., '0-30', '31-60', '91-180', 'Over 180', 'Not due'). Can be used directly for aging reports, or recomputed from (snapshot_date::date - due_date::date) for custom bucket definitions.")

    days_past_due: Optional[int] = Field(default=None, description="Number of days the receivable is overdue relative to the due date. If an average days past due KPI is requested, use a balance-weighted average over open AR unless the user explicitly asks for a simple-count or overdue-only variant.")

    dunning_level: Optional[int] = Field(default=None, description="Collection stage indicating how many dunning notices have been issued.")

    last_payment_date: Optional[datetime] = Field(default=None, description="Date of the most recent payment received for this receivable. NOTE: this column may be NULL in current data — do not rely on it for cash flow period filtering without first verifying data availability.")

    gl_account: Optional[str] = Field(default=None, max_length=50, description="General ledger account associated with the receivable posting.")

    company_code: Optional[str] = Field(default=None, max_length=50, description="Legal entity or company code responsible for the receivable.")

    business_unit: Optional[str] = Field(default=None, max_length=100, description="Internal business unit associated with the transaction.")

    profit_center: Optional[str] = Field(default=None, max_length=50, description="Profit center responsible for the revenue related to this receivable.")

    cost_center: Optional[str] = Field(default=None, max_length=50, description="Cost center associated with the transaction if applicable.")

    invoice_description: Optional[str] = Field(default=None, description="Narrative description or memo associated with the receivable document.")

    snapshot_date: Optional[datetime] = Field(default=None, description="Point-in-time reporting date for this AR record. All balance sheet AR queries must filter on this column using MAX(snapshot_date) <= cutoff_date. Do NOT apply a start_date filter — AR is a stock metric, not a flow.")

    payment_terms: Optional[str] = Field(default=None, max_length=100, description="Payment terms description applied to this receivable (e.g., 'Net 30').")

    payment_terms_days: Optional[int] = Field(default=None, description="Number of days allowed for payment according to the payment terms.")

    sales_channel: Optional[str] = Field(default=None, max_length=100, description="Sales channel through which the transaction originated (e.g., direct sales, distributor, online).")

    salesperson_name: Optional[str] = Field(default=None, max_length=255, description="Salesperson responsible for the transaction.")

    region: Optional[str] = Field(default=None, max_length=100, description="Geographic or sales region associated with the transaction.")

    vat_rate: Optional[float] = Field(default=None, description="Tax rate applied to the transaction.")

    created_at: Optional[datetime] = Field(default=None, description="Timestamp when the record was created.")

    updated_at: Optional[datetime] = Field(default=None, description="Timestamp when the record was last updated.")

class InvoiceLines(SQLModel, table=True):
    """
    Python class definition for the Invoice Lines detail entity.
    This table stores line-level detail for customer invoices, including item-level 
    revenue, quantity, and tax data.
    """
    __tablename__ = "invoice_lines"
    __table_args__ = {
        "comment": (
            "Line-level detail table for customer invoices, storing item-level revenue, quantity, and tax data. "
            "INCOME STATEMENT metric — period-scope via the parent invoice date rather than at the line level. "
            "KEY JOINS: invoice_lines.invoice_id = invoices.id for header context and period filtering; "
            "invoice_lines.inventory_item_id = inventory_items.id for product-level margin and COGS analysis. "
            "Use for revenue breakdowns by product, category, or SKU that are not available at the invoice header level."
        )
    }

    id: Optional[int] = Field(default=None, primary_key=True, description="System-generated internal primary key.")

    invoice_id: Optional[int] = Field(default=None, foreign_key="invoices.id", description="Foreign key referencing invoices.id.")

    ingestion_log_id: Optional[int] = Field(default=None, foreign_key="data_ingestion_logs.id", description="Reference to the data ingestion job that created or updated this record.")

    item_id: Optional[str] = Field(default=None, max_length=100, description="Internal SKU or item identifier.")

    inventory_item_id: Optional[int] = Field(default=None, foreign_key="inventory_items.id", description="Foreign key to inventory_items.id for reliable margin and COGS analysis.")

    item_name: Optional[str] = Field(default=None, max_length=255, description="Name or title of the item.")

    description: Optional[str] = Field(default=None, description="Narrative description or memo.")

    transaction_id: Optional[str] = Field(default=None, max_length=100, description="Business transaction identifier.")

    product_category: Optional[str] = Field(default=None, max_length=100, description="Product classification or category.")

    quantity: Optional[int] = Field(default=None, description="Quantity of units.")

    unit_price: Optional[float] = Field(default=None, description="Price per unit.")

    discount: Optional[float] = Field(default=None, description="Discount amount or rate applied to the line.")

    line_amount: Optional[float] = Field(default=None, description="Total line amount before tax.")

    tax_rate: Optional[float] = Field(default=None, description="Applicable tax rate.")

    vat_amount: Optional[float] = Field(default=None, description="VAT amount applied to the line.")

    created_at: Optional[datetime] = Field(default=None, description="Record creation timestamp.")

    updated_at: Optional[datetime] = Field(default=None, description="Record last-update timestamp.")

class Invoices(SQLModel, table=True):
    """
    Python class definition for the Invoices transactional fact entity.
    This table stores customer invoices issued for goods or services, serving as 
    the primary source for income statement revenue metrics.
    """
    __tablename__ = "invoices"
    __table_args__ = {
        "comment": (
            "Transactional fact table storing customer invoices issued for goods or services. "
            "INCOME STATEMENT metric — revenue is recognised at the invoice level and period-scoped. "
            "KEY JOINS: invoices.customer_id = customers.id for customer-level revenue analysis; "
            "invoice_lines.invoice_id = invoices.id for line-item revenue and margin breakdown; "
            "accounts_receivable.invoice_id = invoices.id to link billing to outstanding balances. "
            "Used as the credit sales source for DSO calculations — combine with accounts_receivable "
            "in separate CTEs rather than a direct join when computing ratio-based KPIs."
        )
    }

    id: Optional[int] = Field(default=None, primary_key=True, description="System-generated internal primary key.")

    id_external: Optional[str] = Field(default=None, max_length=100, description="External invoice number assigned by the ERP or billing system (legal invoice identifier).")

    ingestion_log_id: Optional[int] = Field(default=None, foreign_key="data_ingestion_logs.id", description="Reference to the data ingestion job that created or updated this record.")

    source_system_id: Optional[str] = Field(default=None, max_length=50, description="Identifier of the ERP or billing system that provided this invoice record.")

    source_primary_key: Optional[str] = Field(default=None, max_length=100, description="Original primary key of the invoice record in the source system.")

    customer_id: Optional[int] = Field(default=None, foreign_key="customers.id", description="Foreign key referencing customers.id for the primary customer responsible for paying the invoice. This is the canonical customer join key after ingestion.")

    bill_to_customer_id: Optional[int] = Field(default=None, foreign_key="customers.id", description="Foreign key referencing the customer entity designated as the billing recipient.")

    ship_to_customer_id: Optional[int] = Field(default=None, foreign_key="customers.id", description="Foreign key referencing the customer entity receiving the delivered goods or services.")

    sales_order_id: Optional[int] = Field(default=None, foreign_key="sales_orders.id", description="Foreign key referencing the originating sales order that generated this invoice.")

    original_invoice_id: Optional[int] = Field(default=None, foreign_key="invoices.id", description="Reference to the original invoice if this document is a reversal, correction, or credit memo.")

    invoice_date: Optional[datetime] = Field(default=None, description="Date the invoice was issued — the revenue recognition date for income statement reporting. Use this column (not accounting_date or due_date) for all period-based revenue and sales queries.")

    due_date: Optional[datetime] = Field(default=None, description="Date by which payment for the invoice is due.")

    accounting_date: Optional[datetime] = Field(default=None, description="General ledger posting date used for financial accounting and revenue reporting.")

    snapshot_date: Optional[datetime] = Field(default=None, description="Reporting snapshot date indicating when this invoice record was extracted for analytics.")

    status: Optional[str] = Field(default=None, max_length=50, description="Current lifecycle status of the invoice (e.g., Open, Paid, Cancelled).")

    invoice_type: Optional[str] = Field(default=None, max_length=50, description="Type of invoice document (e.g., Standard Invoice, Credit Memo, Debit Memo).")

    fiscal_year: Optional[int] = Field(default=None, description="Fiscal year associated with the invoice posting period.")

    complete_flag: Optional[bool] = Field(default=None, description="Flag indicating whether the invoice record is complete and finalized.")

    is_reversed: Optional[bool] = Field(default=None, description="Flag indicating whether this invoice has been reversed or cancelled.")

    total_amount: Optional[float] = Field(default=None, description="Gross invoice amount including tax (subtotal_amount + tax_amount). Use this for total revenue/sales queries. For pre-tax revenue, use subtotal_amount instead.")

    subtotal_amount: Optional[float] = Field(default=None, description="Invoice amount before taxes, freight, or additional charges.")

    balance_due: Optional[float] = Field(default=None, description="Outstanding unpaid balance remaining on the invoice.")

    currency: Optional[str] = Field(default=None, max_length=3, description="Currency in which the invoice was issued.")

    exchange_rate: Optional[float] = Field(default=None, description="Exchange rate used to convert the invoice amount to the company's local reporting currency.")

    local_currency_amount: Optional[float] = Field(default=None, description="Total invoice amount converted into the company's local reporting currency.")

    tax_amount: Optional[float] = Field(default=None, description="Total tax amount applied to the invoice.")

    vat_rate: Optional[float] = Field(default=None, description="VAT or sales tax rate applied to the invoice.")

    tax_code: Optional[str] = Field(default=None, max_length=50, description="Tax classification code applied to the invoice transaction.")

    discount_amount: Optional[float] = Field(default=None, description="Total discounts applied to the invoice.")

    freight_amount: Optional[float] = Field(default=None, description="Shipping or freight charges included in the invoice.")

    company_code: Optional[str] = Field(default=None, max_length=50, description="Legal entity or company code responsible for issuing the invoice.")

    business_unit: Optional[str] = Field(default=None, max_length=100, description="Internal business unit responsible for the transaction.")

    sales_organization: Optional[str] = Field(default=None, max_length=50, description="Sales organization responsible for the transaction.")

    distribution_channel: Optional[str] = Field(default=None, max_length=50, description="Distribution channel used for the sale (e.g., retail, wholesale, online).")

    division: Optional[str] = Field(default=None, max_length=50, description="Product or business division associated with the transaction.")

    profit_center: Optional[str] = Field(default=None, max_length=50, description="Profit center responsible for revenue generated by this invoice.")

    sales_channel: Optional[str] = Field(default=None, max_length=100, description="Sales channel through which the transaction originated (e.g., direct sales, distributor, online).")

    salesperson_name: Optional[str] = Field(default=None, max_length=255, description="Salesperson responsible for the customer account or transaction.")

    region: Optional[str] = Field(default=None, max_length=100, description="Geographic or sales region associated with the transaction.")

    payment_terms: Optional[str] = Field(default=None, max_length=100, description="Payment terms description applied to the invoice (e.g., 'Net 30').")

    payment_terms_days: Optional[int] = Field(default=None, description="Number of days allowed for payment according to the payment terms.")

    gl_document_number: Optional[str] = Field(default=None, max_length=100, description="General ledger document number associated with the accounting entry for this invoice.")

class PurchaseOrderLines(SQLModel, table=True):
    """
    Python class definition for the Purchase Order Lines detail entity.
    This table stores line-level detail for purchase orders, including item-level 
    quantities, pricing, and delivery data.
    """
    __tablename__ = "purchase_order_lines"
    __table_args__ = {
        "comment": (
            "Line-level detail table for purchase orders, storing item-level quantities, pricing, and delivery data. "
            "KEY JOINS: purchase_order_lines.purchase_order_id = purchase_orders.id for header context and supplier attribution; "
            "purchase_order_lines.inventory_item_id = inventory_items.id for product-level procurement analysis. "
            "Use for item-level spend breakdown, quantity ordered vs received vs invoiced analysis, and line-level matching against goods receipts and supplier invoices."
        )
    }

    id: Optional[int] = Field(default=None, primary_key=True, description="System-generated internal primary key.")

    purchase_order_id: Optional[int] = Field(default=None, foreign_key="purchase_orders.id", description="Foreign key referencing purchase_orders.id.")

    inventory_item_id: Optional[int] = Field(default=None, foreign_key="inventory_items.id", description="Foreign key referencing inventory_items.id.")

    line_number: Optional[int] = Field(default=None, description="Line number within the parent document.")

    sku: Optional[str] = Field(default=None, max_length=100, description="Stock Keeping Unit.")

    item_description: Optional[str] = Field(default=None, max_length=255, description="Description of the item on the line.")

    uom: Optional[str] = Field(default=None, max_length=50, description="Unit of measure.")

    line_status: Optional[str] = Field(default=None, max_length=50, description="Status of the line.")

    quantity_ordered: Optional[float] = Field(default=None, description="Quantity ordered.")

    quantity_received: Optional[float] = Field(default=None, description="Quantity received.")

    quantity_invoiced: Optional[float] = Field(default=None, description="Quantity invoiced.")

    unit_price: Optional[float] = Field(default=None, description="Price per unit.")

    subtotal_amount: Optional[float] = Field(default=None, description="Subtotal amount before tax.")

    tax_amount: Optional[float] = Field(default=None, description="Tax amount.")

    total_amount: Optional[float] = Field(default=None, description="Total monetary amount.")

    cost_center: Optional[str] = Field(default=None, max_length=100, description="Cost center responsible for the transaction.")

    project_code: Optional[str] = Field(default=None, max_length=100, description="Project code.")

    gl_account_code: Optional[str] = Field(default=None, max_length=100, description="General ledger account code.")

    gl_account_description: Optional[str] = Field(default=None, max_length=255, description="General ledger account description.")

    expected_delivery_date: Optional[datetime] = Field(default=None, description="Expected delivery date.")

    actual_delivery_date: Optional[datetime] = Field(default=None, description="Actual date of delivery.")

    buyer_notes: Optional[str] = Field(default=None, description="Notes from the buyer.")

    supplier_notes: Optional[str] = Field(default=None, description="Notes from the supplier.")

    created_at: Optional[datetime] = Field(default=None, description="Record creation timestamp.")

    updated_at: Optional[datetime] = Field(default=None, description="Record last-update timestamp.")


class PurchaseOrders(SQLModel, table=True):
    """
    Python class definition for the Purchase Orders transactional fact entity.
    This table stores purchase orders issued to suppliers for procurement of goods or services, 
    serving as the primary source for procurement and open commitment metrics.
    """
    __tablename__ = "purchase_orders"
    __table_args__ = {
        "comment": (
            "Transactional fact table storing purchase orders issued to suppliers for procurement of goods or services. "
            "PROCUREMENT metric — period-scope queries using the order date. "
            "KEY JOINS: purchase_orders.supplier_id = suppliers.id for supplier-level spend and commitment analysis; "
            "purchase_order_lines.purchase_order_id = purchase_orders.id for item-level procurement detail; "
            "goods_receipt_notes.purchase_order_id = purchase_orders.id for delivery and receipt tracking; "
            "ap_invoices.po_number for three-way matching against supplier invoices. "
            "Use for open order commitments, procurement lead time, and supplier delivery performance analysis."
        )
    }

    id: Optional[int] = Field(default=None, primary_key=True, description="System-generated internal primary key.")

    id_external: Optional[str] = Field(default=None, max_length=100, description="Business key reference to purchase_orders.id_external used for display and source reconciliation.")

    supplier_id: Optional[int] = Field(default=None, foreign_key="suppliers.id", description="Foreign key referencing suppliers.id for the supplier on the purchase order.")

    ingestion_log_id: Optional[int] = Field(default=None, foreign_key="data_ingestion_logs.id", description="Reference to the data ingestion job that created or updated this record.")

    source_system: Optional[str] = Field(default=None, max_length=100, description="Identifier of the source ERP or system.")

    revision_number: Optional[str] = Field(default=None, max_length=50, description="Document revision number.")

    supplier_reference: Optional[str] = Field(default=None, max_length=150, description="Supplier reference code or number.")

    po_date: Optional[datetime] = Field(default=None, description="Purchase order date.")

    expected_delivery_date: Optional[datetime] = Field(default=None, description="Expected delivery date.")

    final_delivery_date: Optional[datetime] = Field(default=None, description="Final or actual delivery date.")

    status: Optional[str] = Field(default=None, max_length=50, description="Record status (e.g., active, open, closed).")

    approval_status: Optional[str] = Field(default=None, max_length=50, description="Approval status.")

    approval_notes: Optional[str] = Field(default=None, description="Approval notes.")

    currency: Optional[str] = Field(default=None, max_length=3, description="Transaction currency. Keep monetary reporting labels explicit: AED-denominated outputs should be rendered as AED, not '$'.")

    total_order_amount: Optional[float] = Field(default=None, description="Total amount of the purchase order.")

    total_received_amount: Optional[float] = Field(default=None, description="Total amount received.")

    total_invoiced_amount: Optional[float] = Field(default=None, description="Total amount invoiced.")

    total_open_amount: Optional[float] = Field(default=None, description="Remaining open amount.")

    payment_terms: Optional[str] = Field(default=None, max_length=100, description="Payment terms description (e.g., 'Net 30').")

    incoterms: Optional[str] = Field(default=None, max_length=50, description="International Commercial Terms.")

    business_unit: Optional[str] = Field(default=None, max_length=100, description="Business unit.")

    legal_entity_code: Optional[str] = Field(default=None, max_length=100, description="Legal entity code.")

    cost_center: Optional[str] = Field(default=None, max_length=100, description="Cost center responsible for the transaction.")

    project_code: Optional[str] = Field(default=None, max_length=100, description="Project code.")

    spend_category: Optional[str] = Field(default=None, max_length=100, description="Spend category.")

    buyer_name: Optional[str] = Field(default=None, max_length=100, description="Name of the buyer.")

    buyer_department: Optional[str] = Field(default=None, max_length=100, description="Department of the buyer.")

    shipping_method: Optional[str] = Field(default=None, max_length=100, description="Method of shipping.")

    ship_to_location: Optional[str] = Field(default=None, description="Ship-to location.")

    bill_to_location: Optional[str] = Field(default=None, description="Bill-to location.")

    created_at: Optional[datetime] = Field(default=None, description="Record creation timestamp.")

    updated_at: Optional[datetime] = Field(default=None, description="Record last-update timestamp.")

class PurchaseRegisters(SQLModel, table=True):
    """
    Python class definition for the Purchase Registers entity.
    This table stores purchase transactions with line-level detail, sourced from 
    ERP procurement exports, serving as the primary source for income statement 
    expense and procurement spend metrics.
    """
    __tablename__ = "purchase_registers"
    __table_args__ = {
        "comment": (
            "Procurement register storing purchase transactions with line-level detail, sourced from ERP procurement exports. "
            "INCOME STATEMENT metric — expense is recognised at invoice date, not order creation date; period-scope all purchase and spend queries accordingly. "
            "KEY JOINS: purchase_registers.supplier_id = suppliers.id for supplier-level spend analysis. "
            "Primary amount metric is the AED-converted line total — use this for all spend aggregations and label outputs explicitly as AED. "
            "When comparing procurement spend and volume, keep both on the same invoice date basis unless the user explicitly asks for a different operational timing view."
        )
    }

    id: Optional[int] = Field(default=None, primary_key=True, description="System-generated internal primary key.")

    id_external: Optional[str] = Field(default=None, max_length=100, description="External identifier of the procurement document from the source ERP system.")

    ingestion_log_id: Optional[int] = Field(default=None, foreign_key="data_ingestion_logs.id", description="Reference to the data ingestion job that created or updated this record.")

    supplier_id: Optional[int] = Field(default=None, foreign_key="suppliers.id", description="Foreign key referencing suppliers.id for the supplier associated with the procurement transaction. This is the canonical supplier join key for downstream SQL. This column is blank in mock data and is populated during ingestion by matching supplier_external_id to suppliers.id.")

    document_type: Optional[str] = Field(default=None, max_length=50, description="Type of procurement document (e.g., Purchase Order, Supplier Invoice, Goods Receipt).")

    purchasing_organization: Optional[str] = Field(default=None, max_length=100, description="Purchasing organization responsible for the procurement transaction.")

    purchasing_group: Optional[str] = Field(default=None, max_length=50, description="Purchasing team or buyer group responsible for managing the procurement process.")

    company_code: Optional[str] = Field(default=None, max_length=50, description="Legal entity or company code responsible for the procurement transaction.")

    creation_date: Optional[date] = Field(default=None, description="Date the Purchase Order was created in the source system. Use for PO pipeline and procurement lead-time analysis. Do NOT use for income statement purchase totals — use invoice_date instead.")

    delivery_date: Optional[date] = Field(default=None, description="Expected or actual delivery date of goods or services.")

    status: Optional[str] = Field(default=None, max_length=50, description="Current lifecycle status of the procurement document.")

    payment_terms: Optional[str] = Field(default=None, max_length=100, description="Payment terms agreed with the supplier (e.g., 'Net 30').")

    payment_terms_days: Optional[int] = Field(default=None, description="Number of days allowed for payment according to the purchase terms.")

    incoterms: Optional[str] = Field(default=None, max_length=50, description="International Commercial Terms defining shipping responsibilities (e.g., FOB, CIF).")

    reference_number: Optional[str] = Field(default=None, max_length=100, description="Reference number associated with the procurement document, such as an external supplier reference.")

    approval_status: Optional[str] = Field(default=None, max_length=50, description="Approval state of the procurement document within the purchasing workflow.")

    goods_receipt_status: Optional[str] = Field(default=None, max_length=50, description="Status indicating whether goods have been received for the procurement transaction.")

    invoice_status: Optional[str] = Field(default=None, max_length=50, description="Status indicating whether the supplier invoice has been received or processed.")

    description: Optional[str] = Field(default=None, description="Narrative description or memo associated with the procurement transaction.")

    profit_center: Optional[str] = Field(default=None, max_length=50, description="Profit center associated with the procurement transaction.")

    cost_center: Optional[str] = Field(default=None, max_length=50, description="Cost center responsible for the procurement expense.")

    total_amount: Optional[float] = Field(default=None, description="Total value of the procurement document including taxes and charges.")

    currency: Optional[str] = Field(default=None, max_length=10, description="Currency in which the procurement transaction was recorded. Converted reporting totals such as linetotal_aed should still be labelled explicitly as AED.")

    po_number: Optional[str] = Field(default=None, max_length=100, description="Purchase order number associated with the procurement transaction.")

    invoice_number: Optional[str] = Field(default=None, max_length=100, description="Supplier invoice number linked to the procurement record.")

    invoice_date: Optional[date] = Field(default=None, description="Date the supplier invoice was issued — the expense recognition date for income statement reporting. Use this column (not creation_date) for all period-based purchase totals, YoY comparisons, and DPO calculations.")

    due_date: Optional[date] = Field(default=None, description="Date by which payment for the supplier invoice is due.")

    quantity_purchased: Optional[float] = Field(default=None, description="Total quantity of goods or services purchased.")

    fx_rate: Optional[float] = Field(default=None, description="Foreign exchange rate used to convert transaction amounts into the reporting currency.")

    unitcost_fc: Optional[float] = Field(default=None, description="Unit cost of the purchased item in the foreign currency.")

    unitcost_aed: Optional[float] = Field(default=None, description="Unit cost converted into AED (local reporting currency).")

    linetotal_aed: Optional[float] = Field(default=None, description="Line total in AED after FX conversion (quantity_purchased × unitcost_aed). Primary metric for purchase spend analysis — use SUM(linetotal_aed) for total purchase queries and label outputs as AED. Excludes VAT (VAT is in vat_aed).")

    vat_rate: Optional[float] = Field(default=None, description="VAT or tax rate applied to the procurement transaction.")

    vat_aed: Optional[float] = Field(default=None, description="VAT amount calculated in AED.")

    notes: Optional[str] = Field(default=None, description="Additional internal notes or comments related to the procurement transaction.")

    created_at: Optional[datetime] = Field(default=None, description="Timestamp when the record was created.")

    updated_at: Optional[datetime] = Field(default=None, description="Timestamp when the record was last updated.")

class Suppliers(SQLModel, table=True):
    """
    Python class definition for the Supplier master data dimension entity.
    This table stores supplier master data and serves as the central source of truth 
    for procurement spend, payables, and supplier risk analytics.
    """
    __tablename__ = "suppliers"
    __table_args__ = {
        "comment": (
            "Supplier master data dimension — the authoritative reference for all vendor-facing financial analysis including procurement spend, payables, and supplier risk. "
            "Each row represents one supplier entity. "
            "KEY JOINS: accounts_payable.supplier_id = suppliers.id for liability and payment analysis; "
            "purchase_registers.supplier_id = suppliers.id for procurement spend and volume analysis; "
            "purchase_orders.supplier_id = suppliers.id for open order and commitment analysis. "
            "Use id_external as the business-facing supplier code in result sets — id is the internal surrogate key used only for joining. "
            "HIERARCHY: parent_supplier_id is a self-referencing FK — use it to roll up subsidiaries to their parent for group-level spend and exposure reporting."
        )
    }

    id: Optional[int] = Field(default=None, primary_key=True, description="System-generated internal primary key.")

    id_external: Optional[str] = Field(default=None, max_length=100, description="Business-facing external supplier code (e.g., 'SUP-0001'). Use for display, reconciliation, and source lookups.")

    ingestion_log_id: Optional[int] = Field(default=None, foreign_key="data_ingestion_logs.id", description="Reference to the data ingestion job that created or updated this record.")

    source_system_id: Optional[str] = Field(default=None, max_length=50, description="Identifier of the ERP or procurement system that provided this supplier record.")

    source_primary_key: Optional[str] = Field(default=None, max_length=100, description="Original primary key of the supplier record in the source system.")

    parent_supplier_id: Optional[int] = Field(default=None, foreign_key="suppliers.id", description="Self-referencing foreign key representing hierarchical supplier relationships (e.g., parent vendor organization).")

    name: Optional[str] = Field(default=None, max_length=255, description="Legal or registered business name of the supplier.")

    contact_email: Optional[str] = Field(default=None, description="Primary contact email address for supplier communications.")

    contact_phone: Optional[str] = Field(default=None, description="Primary contact phone number for the supplier.")

    contact_name: Optional[str] = Field(default=None, max_length=255, description="Primary contact person name for the supplier, used for procurement and payment inquiries.")

    region: Optional[str] = Field(default=None, max_length=100, description="Geographic region or internal procurement region associated with the supplier.")

    country: Optional[str] = Field(default=None, max_length=100, description="Country where the supplier is headquartered or operates.")

    address_line_1: Optional[str] = Field(default=None, max_length=255, description="Primary business address of the supplier.")

    business_type: Optional[str] = Field(default=None, max_length=100, description="High-level classification of the supplier's business activity (e.g., manufacturer, distributor, service provider).")

    supplier_type: Optional[str] = Field(default=None, max_length=100, description="Operational classification of the supplier (e.g., strategic supplier, preferred vendor, contractor).")

    industry_code: Optional[str] = Field(default=None, max_length=50, description="Standardized industry classification code representing the supplier's industry sector.")

    minority_owned_status: Optional[str] = Field(default=None, max_length=50, description="Indicates whether the supplier qualifies as a minority-owned or diversity-certified business.")

    is_intercompany: Optional[bool] = Field(default=None, description="Flag indicating whether the supplier represents an internal company entity within the same corporate group.")

    preferred_currency: Optional[str] = Field(default=None, max_length=3, description="Preferred transaction currency used for payments to this supplier. Keep monetary reporting labels explicit: AED-denominated outputs should be rendered as AED, not '$'.")

    payment_terms: Optional[str] = Field(default=None, max_length=100, description="Payment terms description agreed with the supplier (e.g., 'Net 30').")

    payment_terms_days: Optional[int] = Field(default=None, description="Number of days allowed for payment according to the supplier payment terms.")

    payment_method: Optional[str] = Field(default=None, max_length=50, description="Preferred payment method used to pay the supplier (e.g., bank transfer, cheque, ACH).")

    remittance_email: Optional[str] = Field(default=None, max_length=255, description="Email address used by the supplier for receiving payment remittance notifications.")

    default_ship_method: Optional[str] = Field(default=None, max_length=50, description="Default shipping or delivery method used when receiving goods from the supplier.")

    tax_id: Optional[str] = Field(default=None, max_length=50, description="Government-issued tax identification number for the supplier.")

    vat_registration_number: Optional[str] = Field(default=None, max_length=50, description="VAT or GST registration number used for tax reporting and compliance.")

    duns_number: Optional[str] = Field(default=None, max_length=20, description="Dun & Bradstreet D-U-N-S number used for supplier identification and credit assessment.")

    certification: Optional[str] = Field(default=None, max_length=100, description="Supplier certification status such as ISO certifications or regulatory compliance credentials.")

    compliance_valid_until: Optional[datetime] = Field(default=None, description="Date until which supplier compliance or certification remains valid.")

    risk_category: Optional[str] = Field(default=None, max_length=50, description="Supplier risk rating used for procurement and supply chain risk management.")

    is_active: Optional[bool] = Field(default=None, description="Boolean active-status flag for the supplier dimension.")

    acquisition_date: Optional[datetime] = Field(default=None, description="Date when the supplier relationship was established.")

    created_at: Optional[datetime] = Field(default=None, description="Timestamp when the supplier record was created.")

    updated_at: Optional[datetime] = Field(default=None, description="Timestamp when the supplier record was last updated.")
    
class ConversationSession(SQLModel, table=True):
    """
    Python class definition for the Conversation Sessions entity.
    This table stores session-level metadata for user conversations with the AI assistant.
    """
    __tablename__ = "conversation_sessions"

    id: str = Field(default=None, primary_key=True, index=True, description="System-generated internal primary key.")

    user_id: str = Field(default=None, index=True , description="Foreign key referencing users.id for the user associated with this session.")
    
    turn_count: int = Field(default=0, description="Number of turns (user + assistant exchanges) in the conversation session.")

    created_at: datetime = Field(default_factory=datetime.now , description="Timestamp when the conversation session started.")

    updated_at: datetime = Field(default_factory=datetime.now , description="Timestamp when the session metadata was last updated.", sa_column_kwargs={"onupdate": datetime.now()})

    is_active: Optional[bool] = Field(default=True, description="Flag indicating whether the session is currently active.")
    
    chat_messages: list["ChatMessage"] = Relationship(
        back_populates="session", 
        cascade_delete=True, 
        passive_deletes=True
    )
    
class ChatMessage(SQLModel, table=True):
    __tablename__ = "chat_messages"
    __table_args__ = (
        Index("ix_chat_messages_session_created_id", "session_id", "created_at", "id"),
    )
    
    id: Optional[int] = Field(default=None, primary_key=True, index=True)
    
    # ForeignKey with ondelete requires explicit sa_column definition
    session_id: str = Field(
    sa_column=Column(
        String(36),
        ForeignKey("conversation_sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
)
    
    role: str = Field(max_length=20) 
    content: str = Field(sa_column=Column(Text, nullable=False))
    chat_metadata: Optional[dict] = Field(default=None, sa_column=Column(JSON))
    
    message_order: int = Field(default=0)
    message_uuid: Optional[str] = Field(default=None, max_length=36, index=True)
    routed_to: Optional[str] = Field(default=None, max_length=30)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    # This matches "chat_messages" on ConversationSession
    session: Optional["ConversationSession"] = Relationship(back_populates="chat_messages")
    
def get_tables_summary() -> str:
    """
    Utility: Returns a brief list of all available tables and their high-level descriptions.
    Does not require a DB session since it only reads Python class definitions.
    """
    tables_info = []
    for model in SQLModel.__subclasses__():
        if getattr(model, "__table__", None) is None:
            continue
            
        table_name = getattr(model, "__tablename__", model.__name__.lower())
        comment = "No context"
        if hasattr(model, "__table_args__") and isinstance(model.__table_args__, dict):
            comment = model.__table_args__.get("comment", "No context")
            
        tables_info.append(f"- {table_name}: {comment}")
    
    return "Available tables:\n" + "\n".join(tables_info)


def get_detailed_schema(session: Session, table_names: list[str]) -> str:
    """
    Utility: Returns detailed schema for specific tables, filtering out empty columns.
    """
    target_tables = {name.lower() for name in table_names}
    all_schemas = []
    
    for model in SQLModel.__subclasses__():
        if getattr(model, "__table__", None) is None:
            continue
            
        table_name = getattr(model, "__tablename__", model.__name__.lower())
        if table_name not in target_tables:
            continue
            
        comment = "No context"
        if hasattr(model, "__table_args__") and isinstance(model.__table_args__, dict):
            comment = model.__table_args__.get("comment", "No context")
            
        field_names = list(model.model_fields.keys())
        if not field_names:
            continue
            
        # Count non-nulls ONLY for the requested table
        counts_stmt = select(
            *[func.count(getattr(model, name)).label(name) for name in field_names]
        )
        result = session.exec(counts_stmt).one()
        
        schema_desc = f"Table: {table_name} ({comment})\n"
        has_populated_columns = False
        
        for name in field_names:
            non_null_count = getattr(result, name)
            if non_null_count > 0:
                has_populated_columns = True
                field = model.model_fields[name]
                desc = field.description or ""
                field_type = str(field.annotation).replace("<class '", "").replace("'>", "")
                
                # Compact format
                if desc and desc != "No description available":
                    schema_desc += f"  - {name} ({field_type}): {desc}\n"
                else:
                    schema_desc += f"  - {name} ({field_type})\n"
                    
        if has_populated_columns:
            all_schemas.append(schema_desc)
        else:
            all_schemas.append(f"Table: {table_name} ({comment}): (No populated columns)\n")
            
    if not all_schemas:
        return "No schemas found for the provided table names. Please check the table names using list_tables."
        
    return "\n---\n".join(all_schemas)