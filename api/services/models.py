## models.py
from sqlmodel import SQLModel, Field, Relationship, Column, Integer, String, ForeignKey, DateTime, Text, JSON, Float, Boolean, Date
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

    id: Optional[int] = Field(default=None, sa_column=Column(Integer, primary_key=True, index=True, comment="System-generated internal primary key."))

    id_external: Optional[str] = Field(default=None, sa_column=Column(String(100), unique=True, index=True, comment="Business-facing external customer code (e.g., 'CUST001'). Use this field for display, source reconciliation, and lookup context; use customers.id as the default join key after ingestion."))

    ingestion_log_id: Optional[int] = Field(default=None, sa_column=Column(Integer, ForeignKey("data_ingestion_logs.id"), comment="Reference to the data ingestion job that created or updated this record."))

    source_system_id: Optional[str] = Field(default=None, sa_column=Column(String(50), nullable=True, index=True, comment="Identifier of the ERP or CRM system that provided this record."))

    source_primary_key: Optional[str] = Field(default=None, sa_column=Column(String(100), nullable=True, comment="Original primary key of the customer record in the source system."))

    parent_customer_id: Optional[int] = Field(default=None, sa_column=Column(Integer, ForeignKey("customers.id"), nullable=True, comment="Self-referencing foreign key representing hierarchical customer relationships (e.g., parent company)."))

    name: Optional[str] = Field(default=None, sa_column=Column(String(255), nullable=True, comment="Customer's legal or registered business name."))

    address: Optional[str] = Field(default=None, sa_column=Column(Text, comment="Full primary business address of the customer."))

    city: Optional[str] = Field(default=None, sa_column=Column(String(100), comment="City where the customer is located."))

    region: Optional[str] = Field(default=None, sa_column=Column(String(100), comment="Geographic region or internal sales region associated with the customer."))

    country: Optional[str] = Field(default=None, sa_column=Column(String(100), nullable=True, comment="Country where the customer is located."))

    email: Optional[str] = Field(default=None, sa_column=Column(String(255), comment="Primary contact email address for the customer."))

    phone: Optional[str] = Field(default=None, sa_column=Column(String(50), comment="Primary contact phone number for the customer."))

    contact_details: Optional[Any] = Field(default=None, sa_column=Column(JSON, comment="JSON field containing additional contact information such as secondary emails, phone numbers, or contact persons."))

    language_preference: Optional[str] = Field(default=None, sa_column=Column(String(50), nullable=True, comment="Preferred language for communication with the customer."))

    document_currency: Optional[str] = Field(default="AED", sa_column=Column(String(3), default="AED", nullable=True, comment="Default transaction currency used for invoices and financial documents."))

    credit_limit: Optional[float] = Field(default=None, sa_column=Column(Float, comment="Maximum credit amount allowed for the customer before blocking new transactions (in document currency)."))

    credit_control_area: Optional[str] = Field(default=None, sa_column=Column(String(20), nullable=True, comment="ERP credit control grouping used for managing credit risk and credit limits."))

    is_credit_blocked: bool = Field(default=False, sa_column=Column(Boolean, default=False, comment="Flag indicating whether the customer is blocked from creating new sales orders due to credit risk."))

    payment_terms: Optional[str] = Field(default=None, sa_column=Column(String(100), comment="Payment terms description (e.g., 'Net 30')."))
    
    payment_terms_days: Optional[int] = Field(default=None, sa_column=Column(Integer, comment="Number of days allowed for payment according to the payment terms."))

    risk_category: Optional[str] = Field(default=None, sa_column=Column(String(50), nullable=True, comment="Credit risk category assigned to the customer."))

    dunning_procedure: Optional[str] = Field(default=None, sa_column=Column(String(50), nullable=True, comment="Collections or dunning procedure used for overdue receivables."))

    business_unit: Optional[str] = Field(default=None, sa_column=Column(String(100), comment="Internal business unit responsible for managing the customer relationship."))

    industry: Optional[str] = Field(default=None, sa_column=Column(String(100), comment="Industry sector the customer operates in."))

    industry_code: Optional[str] = Field(default=None, sa_column=Column(String(50), nullable=True, comment="Standardized industry classification code."))

    customer_category: Optional[str] = Field(default=None, sa_column=Column(String(100), nullable=True, comment="High-level classification of the customer (e.g., distributor, retailer, enterprise)."))

    customer_group: Optional[str] = Field(default=None, sa_column=Column(String(100), nullable=True, comment="Sales or marketing grouping used for reporting and segmentation."))

    customer_segment: Optional[str] = Field(default=None, sa_column=Column(String(100), comment="Detailed sales or marketing segment classification."))

    customer_type: Optional[str] = Field(default=None, sa_column=Column(String(50), nullable=True, comment="Operational classification of the customer (e.g., B2B, B2C)."))

    tax_id: Optional[str] = Field(default=None, sa_column=Column(String(50), nullable=True, comment="Government-issued tax identification number."))

    vat_registration_number: Optional[str] = Field(default=None, sa_column=Column(String(50), nullable=True, comment="VAT or GST registration number used for tax reporting."))

    is_active: bool = Field(default=True, sa_column=Column(Boolean, default=True, comment="Boolean active-status flag for the customer dimension. Use this field for active-customer KPIs after ingestion. Do not assume supplier_status or inventory state fields follow the same convention."))

    salesperson_name: Optional[str] = Field(default=None, sa_column=Column(String(255), comment="Primary salesperson responsible for managing this customer account."))

    acquisition_date: Optional[datetime] = Field(default=None, sa_column=Column(DateTime, nullable=True, comment="Date when the customer relationship was established."))

    created_at: datetime = Field(default_factory=datetime.utcnow, sa_column=Column(DateTime, default=datetime.utcnow, comment="Timestamp when the record was created."))

    updated_at: datetime = Field(default_factory=datetime.utcnow, sa_column=Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, comment="Timestamp when the record was last updated."))

def get_schema() -> str:
    """
    Generates a text representation of the Customer table schema, 
    including column descriptions for the AI agent to use.
    """
    schema_desc = f"Table: {Customers.__tablename__}\n"
    schema_desc += f"Context: {Customers.__table_args__['comment']}\n\nColumns:\n"
    
    # Iterate through the model fields to build a documentation string
    for name, field in Customers.model_fields.items():
        # Extract the comment from the SQLAlchemy column definition
        sa_col = field.json_schema_extra.get("sa_column") if field.json_schema_extra else None
        comment = getattr(sa_col, "comment", "No description available") if sa_col is not None else "No description available"
        field_type = str(field.annotation).replace("<class '", "").replace("'>", "")
        schema_desc += f"- {name} ({field_type}): {comment}\n"
        
    return schema_desc