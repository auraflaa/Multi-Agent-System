"""Tool specifications - required parameters for each tool."""
from typing import Dict, Set

# Required parameters for each tool
TOOL_PARAM_REQUIREMENTS: Dict[str, Set[str]] = {
    # Session tools now require both user_id and session_id
    "get_session_context": {"user_id", "session_id"},
    "save_session_context": {"user_id", "session_id", "context"},
    "get_user_profile": {"user_id"},
    "update_user_name": {"user_id", "name"},
    # Size is optional; planner may only know SKU. Tool will handle both cases.
    "check_inventory": {"sku"},
    "recommend_products": {"category"},  # price_range is optional
    "apply_offers": {"cart", "loyalty_tier"},
    "calculate_payment": {"cart", "discounts"},
    "get_fulfillment_options": {"location"},
    "log_execution_trace": {"trace"},
}

