"""Plan executor that runs tool steps sequentially."""
from typing import Dict, Any, List
from app.schemas.plan_schema import AgentPlan, PlanStep
from app.tools import (
    session,
    users,
    inventory,
    recommendations,
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
        user_message: str
    ) -> Dict[str, Any]:
        """
        Execute a validated plan.
        
        Args:
            plan: Validated AgentPlan object
            session_id: Current session identifier
            user_id: User identifier
            user_message: Original user message
            
        Returns:
            Dictionary containing execution results and final response
        """
        execution_steps = []
        context = {}
        final_result = {}
        
        # Get initial session context (user-centric, branched by session)
        try:
            context = session.get_session_context(user_id, session_id)
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

