"""FastAPI main application with sales agent and admin endpoints."""
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi import UploadFile, File
from typing import Dict, Any, List
import json
from pathlib import Path

from app.db.database import init_database, get_db_connection
from app.llm.planner import SalesAgentPlanner
from app.executor.validator import PlanValidator
from app.executor.runner import PlanRunner
from app.schemas.plan_schema import (
    SalesAgentRequest,
    SalesAgentResponse,
    ExecutionTrace,
    AdminUserRequest,
    AdminProductRequest,
    AdminInventoryRequest,
    AdminOrderRequest,
    AdminCategoryRequest,
)
from pydantic import BaseModel
from typing import Dict, Any
from app.tools import session, explainability
from app.db.database import get_db_connection

# Initialize FastAPI app
app = FastAPI(
    title="Multi-Agent Retail System",
    description="Enterprise-style agentic AI system for retail domain",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files for frontend
static_dir = Path(__file__).parent / "static"
if static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

# Initialize components
planner = SalesAgentPlanner()
validator = PlanValidator()
runner = PlanRunner()


def require_user_in_db(user_id: str) -> None:
    """
    Enforce DB-first sync: user must exist in the `users` table
    before we read or write any simple memory or run the sales agent.
    """
    if not user_id:
        raise HTTPException(status_code=400, detail="user_id is required")

    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT 1 FROM users WHERE user_id = ?", (user_id,))
        if not cursor.fetchone():
            raise HTTPException(
                status_code=404,
                detail=(
                    f"User '{user_id}' not found in database. "
                    "Please create the user via /admin/users or CSV upload before using the sales agent."
                ),
            )
    finally:
        conn.close()

# Initialize database on startup
@app.on_event("startup")
async def startup_event():
    """Initialize database and validate configuration on application startup."""
    from app.config import validate_config
    
    # Validate configuration (fail fast if API key missing)
    validate_config()
    
    # Initialize database
    init_database()
    
    print("=" * 60)
    print("Multi-Agent Retail System - Application Started")
    print("=" * 60)
    print("✓ Configuration validated")
    print("✓ Database initialized")
    print("✓ Frontend available at: http://localhost:8000/")
    print("✓ API docs available at: http://localhost:8000/docs")
    print("=" * 60)


@app.get("/")
async def root():
    """Root endpoint - serves frontend UI."""
    ui_file = Path(__file__).parent / "static" / "index.html"
    if ui_file.exists():
        return FileResponse(str(ui_file))
    return {
        "message": "Multi-Agent Retail System API",
        "version": "1.0.0",
        "endpoints": {
            "ui": "GET / (frontend)",
            "sales_agent": "POST /sales-agent",
            "admin_users": "POST /admin/users",
            "admin_products": "POST /admin/products",
            "admin_inventory": "POST /admin/inventory",
            "admin_orders": "POST /admin/orders"
        }
    }


@app.get("/api")
async def api_info():
    """API information endpoint."""
    return {
        "message": "Multi-Agent Retail System API",
        "version": "1.0.0",
        "endpoints": {
            "ui": "GET / (frontend)",
            "sales_agent": "POST /sales-agent",
            "admin_users": "POST /admin/users",
            "admin_products": "POST /admin/products",
            "admin_inventory": "POST /admin/inventory",
            "admin_orders": "POST /admin/orders"
        }
    }


@app.post("/sales-agent", response_model=SalesAgentResponse)
async def sales_agent(request: SalesAgentRequest) -> SalesAgentResponse:
    """
    Main sales agent endpoint that orchestrates the agent flow.
    
    Flow: Planner → Validator → Executor
    """
    execution_trace = ExecutionTrace(
        validation_passed=False,
        validation_errors=[],
        execution_steps=[],
        final_result=None,
        governance_fixes=None
    )
    
    try:
        # Enforce DB-first sync: user must exist in SQLite
        require_user_in_db(request.user_id)

        # Get session context (user-centric, branched by session)
        session_context = session.get_session_context(request.user_id, request.session_id)
        
        # Step 1: Planner generates plan
        plan_dict, original_llm_response = planner.generate_plan(
            user_message=request.message,
            session_id=request.session_id,
            user_id=request.user_id,
            session_context=session_context
        )
        
        execution_trace.plan = None  # Will be set after validation
        
        # Step 2: Validate plan
        is_valid, validated_plan, errors, was_fixed = validator.validate(
            plan_dict, original_llm_response
        )
        
        execution_trace.plan = validated_plan
        execution_trace.validation_passed = is_valid
        execution_trace.validation_errors = errors
        execution_trace.governance_used = was_fixed
        
        if was_fixed:
            # Determine governance reason from errors
            if any("json" in e.lower() or "parse" in e.lower() for e in errors):
                reason = "Invalid JSON format - governance repaired formatting"
            elif any("schema" in e.lower() or "field" in e.lower() for e in errors):
                reason = "Schema violation - governance fixed structure"
            elif any("action" in e.lower() or "tool" in e.lower() for e in errors):
                reason = "Invalid action - governance corrected tool name"
            else:
                reason = "Validation error - governance fixed plan"
            execution_trace.governance_fixes = [reason]
        
        if not is_valid:
            # Return error response
            return SalesAgentResponse(
                response=f"I encountered an error planning your request: {', '.join(errors)}",
                execution_trace=execution_trace
            )
        
        # Step 3: Execute plan
        execution_result = runner.execute(
            plan=validated_plan,
            session_id=request.session_id,
            user_id=request.user_id,
            user_message=request.message
        )
        
        execution_trace.execution_steps = execution_result.get("execution_steps", [])
        execution_trace.final_result = execution_result.get("final_result")
        
        # Log execution trace for explainability
        try:
            explainability.log_execution_trace({
                "session_id": request.session_id,
                "user_id": request.user_id,
                "message": request.message,
                "plan": validated_plan.dict(),
                "execution_steps": execution_trace.execution_steps,
                "validation_errors": errors
            })
        except Exception as e:
            print(f"Warning: Could not log execution trace: {e}")
        
        return SalesAgentResponse(
            response=execution_result.get("response", "Request processed successfully."),
            execution_trace=execution_trace
        )
    
    except HTTPException as http_exc:
        # Surface a friendly, user-facing message while keeping details in the trace
        detail = http_exc.detail if isinstance(http_exc.detail, str) else str(http_exc.detail)
        execution_trace.validation_errors.append(f"Request error: {detail}")
        return SalesAgentResponse(
            response=(
                "I couldn't process that request yet because something about the setup or data "
                f"needs attention: {detail}"
            ),
            execution_trace=execution_trace,
        )
    except Exception as e:
        # Generic catch-all: keep raw error only in the trace, not in the user message
        execution_trace.validation_errors.append(f"Unexpected error: {str(e)}")
        return SalesAgentResponse(
            response=(
                "I ran into an internal issue while processing your request. "
                "Please try again in a moment or check the admin console/logs for more details."
            ),
            execution_trace=execution_trace,
        )


# ==================== ADMIN ENDPOINTS (JSON / FORM) ====================

@app.post("/admin/users")
async def add_user(user_data: AdminUserRequest):
    """Add a new user to the database."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("""
            INSERT OR REPLACE INTO users (user_id, name, loyalty_tier)
            VALUES (?, ?, ?)
        """, (user_data.user_id, user_data.name, user_data.loyalty_tier))
        
        conn.commit()
        return {
            "status": "success",
            "message": f"User {user_data.user_id} added/updated successfully",
            "user_id": user_data.user_id
        }
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=400, detail=f"Error adding user: {str(e)}")
    finally:
        conn.close()


@app.get("/admin/users/{user_id}")
async def get_user(user_id: str):
    """Fetch a user by ID (for existence checks)."""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "SELECT user_id, name, loyalty_tier FROM users WHERE user_id = ?",
            (user_id,),
        )
        row = cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail=f"User {user_id} not found")
        return {
            "status": "success",
            "user": {
                "user_id": row["user_id"],
                "name": row["name"],
                "loyalty_tier": row["loyalty_tier"],
            },
        }
    finally:
        conn.close()


@app.delete("/admin/users/{user_id}")
async def delete_user(user_id: str):
    """
    Delete a user from the database and clear their simple memory.
    
    This enforces DB-first sync: if a user is removed from `users`,
    their corresponding memory file is also deleted.
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute("DELETE FROM users WHERE user_id = ?", (user_id,))
        deleted = cursor.rowcount
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=400, detail=f"Error deleting user: {str(e)}")
    finally:
        conn.close()

    # Clear simple memory regardless of whether the row existed,
    # to avoid stale memory files.
    memory_result = session.clear_user_memory(user_id)

    return {
        "status": "success",
        "user_id": user_id,
        "deleted_from_db": bool(deleted),
        "memory_cleared": memory_result.get("status") == "cleared",
        "memory_status": memory_result.get("status"),
    }


@app.post("/admin/products")
async def add_product(product_data: AdminProductRequest):
    """Add a new product to the database."""
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        # If a normalized category_id is provided, ensure it exists
        category_id: str | None = None
        if hasattr(product_data, "category") and product_data.category:
            # Keep existing free-text category for backward compatibility
            category_text = product_data.category
        else:
            category_text = None

        # Try to derive or validate category_id from categories table
        cursor.execute(
            "SELECT category_id FROM categories WHERE name = ?",
            (category_text,),
        )
        row = cursor.fetchone()
        if row:
            category_id = row["category_id"]

        cursor.execute(
            """
            INSERT OR REPLACE INTO products (product_id, name, category, base_price, category_id)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                product_data.product_id,
                product_data.name,
                category_text,
                product_data.base_price,
                category_id,
            ),
        )

        conn.commit()
        return {
            "status": "success",
            "message": f"Product {product_data.product_id} added/updated successfully",
            "product_id": product_data.product_id,
            "category_id": category_id,
        }
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=400, detail=f"Error adding product: {str(e)}")
    finally:
        conn.close()


@app.delete("/admin/products/{product_id}")
async def delete_product(product_id: str):
    """Delete a product from the database."""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM products WHERE product_id = ?", (product_id,))
        deleted = cursor.rowcount
        conn.commit()
        return {
            "status": "success",
            "product_id": product_id,
            "deleted_from_db": bool(deleted),
        }
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=400, detail=f"Error deleting product: {str(e)}")
    finally:
        conn.close()


@app.post("/admin/inventory")
async def add_inventory(inventory_data: AdminInventoryRequest):
    """Add inventory entry to the database."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Check if product exists
        cursor.execute(
            "SELECT product_id FROM products WHERE product_id = ?",
            (inventory_data.product_id,)
        )
        if not cursor.fetchone():
            raise HTTPException(
                status_code=400,
                detail=f"Product {inventory_data.product_id} does not exist"
            )
        
        cursor.execute("""
            INSERT OR REPLACE INTO inventory (sku, product_id, size, quantity, location)
            VALUES (?, ?, ?, ?, ?)
        """, (
            inventory_data.sku,
            inventory_data.product_id,
            inventory_data.size,
            inventory_data.quantity,
            inventory_data.location
        ))
        
        conn.commit()
        return {
            "status": "success",
            "message": f"Inventory entry for SKU {inventory_data.sku} added/updated successfully",
            "sku": inventory_data.sku
        }
    except HTTPException:
        raise
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=400, detail=f"Error adding inventory: {str(e)}")
    finally:
        conn.close()


@app.post("/admin/categories")
async def add_category(category: AdminCategoryRequest):
    """Add or update a product category."""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            """
            INSERT OR REPLACE INTO categories (category_id, name)
            VALUES (?, ?)
            """,
            (category.category_id, category.name),
        )
        conn.commit()
        return {
            "status": "success",
            "message": f"Category {category.category_id} added/updated successfully",
            "category_id": category.category_id,
        }
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=400, detail=f"Error adding category: {str(e)}")
    finally:
        conn.close()


@app.delete("/admin/categories/{category_id}")
async def delete_category(category_id: str):
    """Delete a category from the database."""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM categories WHERE category_id = ?", (category_id,))
        deleted = cursor.rowcount
        conn.commit()
        return {
            "status": "success",
            "category_id": category_id,
            "deleted_from_db": bool(deleted),
        }
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=400, detail=f"Error deleting category: {str(e)}")
    finally:
        conn.close()


@app.delete("/admin/inventory/{sku}/{size}")
async def delete_inventory(sku: str, size: str):
    """Delete an inventory entry for a given sku+size."""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "DELETE FROM inventory WHERE sku = ? AND size = ?",
            (sku, size),
        )
        deleted = cursor.rowcount
        conn.commit()
        return {
            "status": "success",
            "sku": sku,
            "size": size,
            "deleted_from_db": bool(deleted),
        }
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=400, detail=f"Error deleting inventory: {str(e)}")
    finally:
        conn.close()


@app.post("/admin/orders")
async def add_order(order_data: AdminOrderRequest):
    """Add an order to the database."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        from datetime import datetime
        
        created_at = order_data.created_at or datetime.now().isoformat()
        
        cursor.execute("""
            INSERT OR REPLACE INTO orders (order_id, user_id, total_amount, status, created_at)
            VALUES (?, ?, ?, ?, ?)
        """, (
            order_data.order_id,
            order_data.user_id,
            order_data.total_amount,
            order_data.status,
            created_at
        ))
        
        conn.commit()
        return {
            "status": "success",
            "message": f"Order {order_data.order_id} added/updated successfully",
            "order_id": order_data.order_id
        }
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=400, detail=f"Error adding order: {str(e)}")
    finally:
        conn.close()


# ==================== ADMIN ENDPOINTS (CSV + DB VIEW) ====================

ALLOWED_TABLES = {"users", "products", "inventory", "orders", "categories"}


@app.post("/admin/upload-csv/{table}")
async def upload_csv(table: str, file: UploadFile = File(...)):
    """
    Upload CSV data for a given table (users, products, inventory, orders).
    The CSV must have headers matching the table columns.
    """
    table = table.lower()
    if table not in ALLOWED_TABLES:
        raise HTTPException(status_code=400, detail=f"Unsupported table: {table}")

    try:
        content = await file.read()
        text = content.decode("utf-8")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error reading CSV file: {str(e)}")

    import csv
    from io import StringIO

    reader = csv.DictReader(StringIO(text))
    rows = list(reader)

    if not rows:
        return {"status": "success", "message": "No rows found in CSV.", "table": table}

    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        if table == "users":
            for row in rows:
                cursor.execute(
                    """
                    INSERT OR REPLACE INTO users (user_id, name, loyalty_tier)
                    VALUES (?, ?, ?)
                    """,
                    (
                        row.get("user_id"),
                        row.get("name"),
                        row.get("loyalty_tier", "bronze"),
                    ),
                )
        elif table == "products":
            for row in rows:
                cursor.execute(
                    """
                    INSERT OR REPLACE INTO products (product_id, name, category, base_price)
                    VALUES (?, ?, ?, ?)
                    """,
                    (
                        row.get("product_id"),
                        row.get("name"),
                        row.get("category"),
                        float(row.get("base_price", 0) or 0),
                    ),
                )
        elif table == "inventory":
            for row in rows:
                cursor.execute(
                    """
                    INSERT OR REPLACE INTO inventory (sku, product_id, size, quantity, location)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (
                        row.get("sku"),
                        row.get("product_id"),
                        row.get("size"),
                        int(row.get("quantity", 0) or 0),
                        row.get("location", "warehouse"),
                    ),
                )
        elif table == "orders":
            for row in rows:
                cursor.execute(
                    """
                    INSERT OR REPLACE INTO orders (order_id, user_id, total_amount, status, created_at)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (
                        row.get("order_id"),
                        row.get("user_id"),
                        float(row.get("total_amount", 0) or 0),
                        row.get("status", "pending"),
                        row.get("created_at"),
                    ),
                )
        elif table == "categories":
            for row in rows:
                cursor.execute(
                    """
                    INSERT OR REPLACE INTO categories (category_id, name)
                    VALUES (?, ?)
                    """,
                    (
                        row.get("category_id"),
                        row.get("name"),
                    ),
                )

        conn.commit()
        return {
            "status": "success",
            "table": table,
            "rows_imported": len(rows),
        }
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=400, detail=f"Error importing CSV: {str(e)}")
    finally:
        conn.close()


@app.get("/admin/db/{table}")
async def get_table_data(table: str):
    """Return all rows from a given table (for demo/inspection)."""
    table = table.lower()
    if table not in ALLOWED_TABLES:
        raise HTTPException(status_code=400, detail=f"Unsupported table: {table}")

    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute(f"SELECT * FROM {table}")
        rows = cursor.fetchall()
        result: List[Dict[str, Any]] = []
        for row in rows:
            result.append({k: row[k] for k in row.keys()})
        return {"status": "success", "table": table, "rows": result}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error reading table {table}: {str(e)}")
    finally:
        conn.close()


@app.get("/admin/memory/{user_id}")
async def get_user_memory(user_id: str):
    """Return all sessions and memory for a given user."""
    try:
        memory = session.get_user_memory(user_id)
        return {"status": "success", "user_id": user_id, "memory": memory}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error reading memory for user {user_id}: {str(e)}")


@app.get("/admin/ui")
async def admin_ui():
    """Serve a simple admin UI for CSV upload and data inspection."""
    ui_file = Path(__file__).parent / "static" / "admin.html"
    if ui_file.exists():
        return FileResponse(str(ui_file))
    return {
        "message": "Admin UI not found.",
        "hint": "Create app/static/admin.html to enable the admin console.",
    }


# ==================== SESSION MEMORY ENDPOINTS ====================

class SessionContextRequest(BaseModel):
    """Request model for updating session context."""
    user_id: str
    session_id: str
    context: Dict[str, Any]


@app.post("/admin/session")
async def update_session_context(request: SessionContextRequest):
    """Add or update session context."""
    try:
        session.save_session_context(request.user_id, request.session_id, request.context)
        return {
            "status": "success",
            "message": f"Session {request.session_id} context updated successfully",
            "session_id": request.session_id
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error updating session context: {str(e)}")


@app.delete("/admin/session/{user_id}/{session_id}")
async def clear_session(user_id: str, session_id: str):
    """Clear session context."""
    try:
        result = session.clear_session(user_id, session_id)
        if result["status"] == "cleared":
            message = f"Session {session_id} for user {user_id} cleared successfully"
        else:
            message = f"Session {session_id} for user {user_id} does not exist (already cleared)"
        return {
            "status": "success",
            "message": message,
            "user_id": user_id,
            "session_id": session_id
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error clearing session: {str(e)}")


@app.get("/admin/session/{user_id}/{session_id}")
async def get_session_context_endpoint(user_id: str, session_id: str):
    """Get session context for a specific user/session."""
    try:
        context = session.get_session_context(user_id, session_id)
        return {
            "status": "success",
            "user_id": user_id,
            "session_id": session_id,
            "context": context
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error retrieving session context: {str(e)}")


if __name__ == "__main__":
    import uvicorn
    import os
    # Render deployment: use PORT environment variable, default to 8000
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)

