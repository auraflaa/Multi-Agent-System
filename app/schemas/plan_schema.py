"""Schema definitions for agent plans and API requests/responses."""
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field


class PlanStep(BaseModel):
    """A single step in the execution plan."""
    action: str = Field(..., description="Tool name to execute")
    params: Dict[str, Any] = Field(..., description="Parameters for the tool")


class AgentPlan(BaseModel):
    """The JSON plan output by the planner agent."""
    intent: str = Field(..., description="User intent summary")
    steps: List[PlanStep] = Field(..., description="Sequential execution steps")
    response_style: str = Field(..., description="Style for final response")


class SalesAgentRequest(BaseModel):
    """Request model for /sales-agent endpoint."""
    session_id: str = Field(..., description="Unique session identifier")
    user_id: str = Field(..., description="User identifier")
    message: str = Field(..., description="User message/query")


class ExecutionTrace(BaseModel):
    """Trace of execution for explainability."""
    plan: Optional[AgentPlan] = None
    validation_passed: bool = False
    validation_errors: List[str] = []
    execution_steps: List[Dict[str, Any]] = []
    final_result: Optional[Dict[str, Any]] = None
    governance_fixes: Optional[List[str]] = None
    governance_used: bool = Field(default=False, description="Whether governance agent was activated")


class SalesAgentResponse(BaseModel):
    """Response model for /sales-agent endpoint."""
    response: str = Field(..., description="Natural language response to user")
    execution_trace: ExecutionTrace = Field(..., description="Full execution trace")


class AdminUserRequest(BaseModel):
    """Request model for adding a user."""
    user_id: str
    name: str
    loyalty_tier: str = Field(default="bronze", description="bronze, silver, gold, platinum")


class AdminProductRequest(BaseModel):
    """Request model for adding a product."""
    product_id: str
    name: str
    category: str
    base_price: float


class AdminCategoryRequest(BaseModel):
    """Request model for adding a category."""
    category_id: str
    name: str


class AdminInventoryRequest(BaseModel):
    """Request model for adding inventory."""
    sku: str
    product_id: str
    size: str
    quantity: int
    location: str = "warehouse"


class AdminOrderRequest(BaseModel):
    """Request model for adding an order."""
    order_id: str
    user_id: str
    total_amount: float
    status: str = "pending"
    created_at: Optional[str] = None

