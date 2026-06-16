# Database Management Documentation

This document outlines the procedures for extending the database schema and restoring data within the financial platform.

---

## 1. Adding New Tables to `models.py`

The system uses **SQLModel** to bridge Pydantic models with SQLAlchemy tables. To ensure the AI agent can effectively query new data, follow these steps when adding a model to `/Users/nirup/Documents/openai_wrapper/api/services/models.py`.

### Step-by-Step Instructions

1.  **Inherit from SQLModel**: Define your class inheriting from `SQLModel` and set `table=True`.
2.  **Define Table Metadata**:
    *   Set `__tablename__`.
    *   Add `__table_args__` with a `comment`. This comment provides the high-level business context that the AI agent uses to understand the table's purpose.
3.  **Define Columns using `Field`**:
    *   Use `Optional[type] = Field(default=None, ...)` for nullable fields.
    *   **Description (Required)**: Every `Field` must include a `description` string. This text is automatically exported to the AI agent via the `db_schema` tool. Without clear descriptions, the agent may struggle to generate accurate SQL queries.
4.  **Relationships**: Use `foreign_key="tablename.column"` to define joins.

### Example Implementation

```python
class Invoices(SQLModel, table=True):
    __tablename__ = "invoices"
    __table_args__ = {
        "comment": "Stores billing records. Joins to customers on customer_id."
    }

    id: Optional[int] = Field(default=None, primary_key=True, description="Internal unique ID.")
    customer_id: int = Field(foreign_key="customers.id", description="Join key to the customers table.")
    amount: float = Field(description="Total invoice amount in document currency.")
    invoice_date: date = Field(description="The date the invoice was issued.")
```

**Note**: Because `get_schema()` in `models.py` uses `SQLModel.__subclasses__()`, new tables are automatically registered and made visible to the AI agent once the class is defined.

---

## 2. Restoring Data Manually using SQL Backup

If you need to restore the database from a backup, use the PostgreSQL command-line utilities.

### Prerequisites

*   Locate your `POSTGRES_URI` in the `.env` file.
*   Ensure the `psql` or `pg_restore` tools are installed on your machine.

### Option A: Restoring from a Plain Text File (`.sql`)

If your backup is a standard SQL script:

```bash
# Using the connection URI
psql "your_postgres_uri_here" -f path/to/backup.sql
```

### Option B: Restoring from a Custom/Tar Format (`.dump` or `.bak`)

If your backup was created using `pg_dump -Fc` (compressed format):

```bash
pg_restore -d "your_postgres_uri_here" --clean --if-exists path/to/backup.dump
```

**Flags Explanation:**
*   `-d`: Specifies the target database connection string.
*   `--clean`: Drops existing database objects (tables, etc.) before restoring them.
*   `--if-exists`: Used with `--clean` to ignore errors if an object doesn't exist in the current DB.

---

## 3. Verifying Changes

After adding a table or restoring data, you can verify the AI's awareness by asking the agent:
> "What columns are available in the [new_table_name] table?"