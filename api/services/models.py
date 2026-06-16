## models.py
from sqlmodel import SQLModel, Field, JSON
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

def get_schema() -> str:
    """
    Generates a text representation of all SQLModel table schemas, 
    including column descriptions for the AI agent to use.
    """
    all_schemas = []
    # Iterate over all models registered in SQLModel
    for model in SQLModel.__subclasses__():
        if getattr(model, "__table__", None) is None:
            continue
            
        table_name = getattr(model, "__tablename__", model.__name__.lower())
        comment = model.__table_args__.get("comment", "No context available") if hasattr(model, "__table_args__") else "No context available"
        
        schema_desc = f"Table: {table_name}\nContext: {comment}\nColumns:\n"
        
        for name, field in model.model_fields.items():
            desc = field.description or "No description available"
            field_type = str(field.annotation).replace("<class '", "").replace("'>", "")
            schema_desc += f"- {name} ({field_type}): {desc}\n"
        
        all_schemas.append(schema_desc)
        
    return "\n---\n".join(all_schemas)