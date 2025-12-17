"""Plan executor that runs tool steps sequentially."""
from typing import Dict, Any, List
from app.schemas.plan_schema import AgentPlan, PlanStep
from app.tools import (
    session,
    users,
    inventory,
    recommendations,
    orders,
    loyalty,
    payment,
    fulfillment,
    explainability,
)
from app.llm.responder import ResponseGenerator


class PlanRunner:
    """Executes validated plans by running tools sequentially."""
    
    # Tool mapping
    TOOL_MAP = {
        "get_session_context": session.get_session_context,
        "save_session_context": session.save_session_context,
        "get_user_profile": users.get_user_profile,
        "update_user_name": users.update_user_name,
        "update_personalization": session.update_personalization,
        "get_orders": orders.get_orders,
        "check_inventory": inventory.check_inventory,
        "recommend_products": recommendations.recommend_products,
        "apply_offers": loyalty.apply_offers,
        "calculate_payment": payment.calculate_payment,
        "get_fulfillment_options": fulfillment.get_fulfillment_options,
        "log_execution_trace": explainability.log_execution_trace
    }

    def __init__(self) -> None:
        # Second LLM call for conversational response
        self.responder = ResponseGenerator()
    
    def execute(
        self,
        plan: AgentPlan,
        session_id: str,
        user_id: str,
        user_message: str,
        session_context: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Execute a validated plan.
        
        Args:
            plan: Validated AgentPlan object
            session_id: Current session identifier
            user_id: User identifier
            user_message: Original user message
            session_context: Optional pre-loaded session context (includes personalization, user_profile)
            
        Returns:
            Dictionary containing execution results and final response
        """
        execution_steps = []
        context = {}
        final_result = {}
        
        # Use provided session context if available (includes personalization), otherwise load it
        if session_context:
            context = session_context.copy()  # Use the provided context with all data
        else:
            # Fallback: Get initial session context (user-centric, branched by session)
            try:
                context = session.get_session_context(user_id, session_id)
                # Also load personalization if not in context
                try:
                    personalization = session.get_personalization(user_id)
                    if personalization:
                        context["personalization"] = personalization
                except Exception:
                    pass
            except Exception as e:
                print(f"Warning: Could not load session context for user {user_id}, session {session_id}: {e}")
        
        # Execute each step sequentially
        for i, step in enumerate(plan.steps):
            step_result = self._execute_step(
                step, session_id, user_id, context, execution_steps
            )
            execution_steps.append(step_result)
            
            # Update context with step results
            if step_result.get("success"):
                context[f"step_{i}_result"] = step_result.get("result")
        
        # Generate final response (second LLM call for natural language)
        response_text = self._generate_response(plan, execution_steps, user_message, context)
        
        # Save updated session context (user-centric) with bounded history
        try:
            context["last_message"] = user_message
            context["last_intent"] = plan.intent
            # Append to message history for conversational memory
            history = context.get("message_history", [])
            history.append({
                "user": user_message,
                "intent": plan.intent,
                "response": response_text
            })
            context["message_history"] = history
            # Append a light trace entry
            trace_history = context.get("trace_history", [])
            trace_history.append({
                "intent": plan.intent,
                "steps": execution_steps
            })
            context["trace_history"] = trace_history
            session.save_session_context(user_id, session_id, context)
        except Exception as e:
            print(f"Warning: Could not save session context for user {user_id}, session {session_id}: {e}")
        
        return {
            "response": response_text,
            "execution_steps": execution_steps,
            "final_result": final_result,
            "context": context
        }
    
    def _execute_step(
        self,
        step: PlanStep,
        session_id: str,
        user_id: str,
        context: Dict[str, Any],
        previous_steps: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Execute a single step."""
        tool_func = self.TOOL_MAP.get(step.action)
        
        if not tool_func:
            return {
                "step": step.action,
                "success": False,
                "error": f"Tool '{step.action}' not found",
                "result": None
            }
        
        # Resolve parameters (replace placeholders with actual values)
        resolved_params = self._resolve_params(
            step.params, session_id, user_id, context, previous_steps
        )
        
        # Auto-inject gender from personalization for recommend_products if not explicitly provided
        if step.action == "recommend_products" and "gender" not in resolved_params:
            personalization = context.get("personalization", {})
            if isinstance(personalization, dict) and "gender" in personalization:
                resolved_params["gender"] = personalization["gender"]
            elif "gender" in context:
                resolved_params["gender"] = context["gender"]
            elif "user_gender" in context:
                resolved_params["gender"] = context["user_gender"]
            # Filter out unsupported params for recommend_products
        if step.action == "recommend_products":
            allowed_params = {"category", "price_range", "gender"}
            resolved_params = {k: v for k, v in resolved_params.items() if k in allowed_params}
        
        # Auto-inject product_id for check_inventory from previous recommend_products results
        if step.action == "check_inventory":
            # Allow planner to pass product_name; map it to product_id from prior recommendations
            product_name = resolved_params.get("product_name")

            # If neither sku nor product_id is provided, try to extract from previous steps/results
            if "sku" not in resolved_params and "product_id" not in resolved_params:
                # If product_name is present, try to match it to a recommended product_id
                if product_name:
                    name_lower = str(product_name).strip().lower()
                    for prev_step in reversed(previous_steps):
                        if prev_step.get("step") == "recommend_products" and prev_step.get("success"):
                            products = prev_step.get("result", [])
                            if isinstance(products, list):
                                for item in products:
                                    if not isinstance(item, dict):
                                        continue
                                    if str(item.get("name", "")).strip().lower() == name_lower and "product_id" in item:
                                        resolved_params["product_id"] = item["product_id"]
                                        break
                        if "product_id" in resolved_params:
                            break

                # Otherwise, use the first recommended product as fallback
                if "product_id" not in resolved_params:
                    for prev_step in reversed(previous_steps):
                        if prev_step.get("step") == "recommend_products" and prev_step.get("success"):
                            products = prev_step.get("result", [])
                            if isinstance(products, list) and len(products) > 0:
                                first_product = products[0]
                                if isinstance(first_product, dict) and "product_id" in first_product:
                                    resolved_params["product_id"] = first_product["product_id"]
                                    break

                # If still no product_id, scan any previous list results for a product_id
                if "product_id" not in resolved_params:
                    for prev_step in reversed(previous_steps):
                        result = prev_step.get("result")
                        if isinstance(result, list):
                            for item in result:
                                if isinstance(item, dict) and "product_id" in item:
                                    resolved_params["product_id"] = item["product_id"]
                                    break
                            if "product_id" in resolved_params:
                                break

                # If still no product_id and we have a product_name, try DB lookup by exact/like name
                if "product_id" not in resolved_params and product_name:
                    try:
                        from app.db.database import get_db_connection as _get_db_conn  # local import to avoid cycles
                        conn = _get_db_conn()
                        cur = conn.cursor()
                        cur.execute(
                            "SELECT product_id FROM products WHERE lower(name) = ? LIMIT 1",
                            (name_lower,),
                        )
                        row = cur.fetchone()
                        if row and row[0]:
                            resolved_params["product_id"] = row[0]
                        else:
                            cur.execute(
                                "SELECT product_id FROM products WHERE lower(name) LIKE ? LIMIT 1",
                                (f"%{name_lower}%",),
                            )
                            row = cur.fetchone()
                            if row and row[0]:
                                resolved_params["product_id"] = row[0]
                    except Exception:
                        pass
                    finally:
                        try:
                            conn.close()
                        except Exception:
                            pass

                # Still nothing resolved -> bail early with a clear error
                if "product_id" not in resolved_params and "sku" not in resolved_params:
                    return {
                        "step": step.action,
                        "success": False,
                        "error": "check_inventory requires product_id or sku; none could be inferred. Run recommend_products first.",
                        "params": resolved_params,
                        "result": None,
                    }

            # If product_id was supplied but doesn't match any previous recommended product_ids,
            # try to map a slugified name to an actual product_id from prior recommendations.
            if "product_id" in resolved_params:
                provided_pid = str(resolved_params["product_id"]).strip().lower()
                # Also derive a slug without common prefixes like "prod-"
                provided_slug = provided_pid
                for prefix in ("prod-", "prod_"):
                    if provided_slug.startswith(prefix):
                        provided_slug = provided_slug[len(prefix):]
                        break
                recommended = []
                for prev_step in reversed(previous_steps):
                    if prev_step.get("step") == "recommend_products" and prev_step.get("success"):
                        recs = prev_step.get("result", [])
                        if isinstance(recs, list):
                            recommended.extend([r for r in recs if isinstance(r, dict)])
                ids = {str(r.get("product_id", "")).strip().lower() for r in recommended}
                if provided_pid not in ids and recommended:
                    def slugify(name: str) -> str:
                        import re
                        return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
                    for r in recommended:
                        name = str(r.get("name", "")).strip()
                        pid = r.get("product_id")
                        if not pid or not name:
                            continue
                        name_slug = slugify(name)
                        # Looser match: exact, or prefix/suffix match to handle trailing prices/noise
                        if (
                            name_slug == provided_pid
                            or name_slug == provided_slug
                            or provided_slug.startswith(name_slug)
                            or name_slug.startswith(provided_slug)
                        ):
                            resolved_params["product_id"] = pid
                            break
                    # If still not matched, fall back to the first recommended product_id
                    if "product_id" not in resolved_params and recommended:
                        resolved_params["product_id"] = recommended[0].get("product_id")

            # Filter out unsupported params (e.g., product_name, gender) before calling tool
            allowed_params = {"sku", "product_id", "size"}
            resolved_params = {k: v for k, v in resolved_params.items() if k in allowed_params}
        
        try:
            # Execute the tool
            result = tool_func(**resolved_params)
            
            return {
                "step": step.action,
                "success": True,
                "params": resolved_params,
                "result": result
            }
        except Exception as e:
            return {
                "step": step.action,
                "success": False,
                "error": str(e),
                "params": resolved_params,
                "result": None
            }
    
    def _resolve_params(
        self,
        params: Dict[str, Any],
        session_id: str,
        user_id: str,
        context: Dict[str, Any],
        previous_steps: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Resolve parameter placeholders with actual values."""
        resolved = {}
        
        for key, value in params.items():
            if isinstance(value, str):
                # Replace placeholders
                if value == "extracted_from_context" or value in ["{{session_id}}", "{{user_id}}"]:
                    if key == "session_id" or "session" in key.lower():
                        resolved[key] = session_id
                    elif key == "user_id" or "user" in key.lower():
                        resolved[key] = user_id
                    else:
                        # Try to get from context or use the key name to infer
                        if key in context:
                            resolved[key] = context[key]
                        elif "session" in key.lower():
                            resolved[key] = session_id
                        elif "user" in key.lower():
                            resolved[key] = user_id
                        else:
                            resolved[key] = value
                else:
                    resolved[key] = value
            elif isinstance(value, dict):
                # Recursively resolve nested dicts
                resolved[key] = self._resolve_params(
                    value, session_id, user_id, context, previous_steps
                )
            elif isinstance(value, list):
                # Resolve list items
                resolved[key] = [
                    self._resolve_params(
                        item if isinstance(item, dict) else {"_": item},
                        session_id, user_id, context, previous_steps
                    ).get("_", item) if isinstance(item, dict) else item
                    for item in value
                ]
            else:
                resolved[key] = value
        
        return resolved
    
    def _generate_response(
        self,
        plan: AgentPlan,
        execution_steps: List[Dict[str, Any]],
        user_message: str,
        context: Dict[str, Any]
    ) -> str:
        """Generate natural language response from execution results.

        Uses a second LLM call (ResponseGenerator) for phrasing.
        """
        try:
            return self.responder.generate(user_message, plan, execution_steps, context)
        except Exception as e:
            # Fallback: keep a simple deterministic response so we never break
            successful_steps = [s for s in execution_steps if s.get("success")]
            if not successful_steps:
                return (
                    "I completed your request, but I couldn't generate a detailed response "
                    f"due to an internal error ({e}). Please try again."
                )

            # Very simple fallback using inventory or generic message
            for step in successful_steps:
                action = step.get("step", "")
                result = step.get("result", {})
                if action == "check_inventory":
                    if result.get("available"):
                        return (
                            f"The product is available, with quantity {result.get('quantity')} "
                            f"at location {result.get('location')}."
                        )
                    else:
                        return "I'm sorry, but this product is currently out of stock."

            return (
                f"I've processed your request about '{plan.intent}', and all steps "
                "completed successfully, but I couldn't generate a richer response."
            )

