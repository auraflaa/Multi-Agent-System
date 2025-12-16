"""Sales Agent - LLM-based Planner that generates JSON action plans."""
import json
from typing import Dict, Any, Tuple
from app.llm.client import LLMClient
from app.llm.prompts import get_planner_system_prompt


class SalesAgentPlanner:
    """LLM-based planner that generates structured JSON action plans."""
    
    def __init__(self):
        self.llm_client = LLMClient()
    
    def generate_plan(
        self,
        user_message: str,
        session_id: str,
        user_id: str,
        session_context: Dict[str, Any]
    ) -> Tuple[Dict[str, Any], str]:
        """
        Generate an action plan based on user message and context.
        
        Args:
            user_message: User's input message
            session_id: Current session identifier
            user_id: User identifier
            session_context: Current session context
            
        Returns:
            Tuple of (plan_dict, original_llm_response)
        """
        system_prompt = self._get_system_prompt()
        user_prompt = self._build_user_prompt(
            user_message, session_id, user_id, session_context
        )
        
        # Get LLM response
        llm_response = self.llm_client.generate(user_prompt, system_prompt)
        
        # Try to extract JSON from response
        plan_json = self._extract_json(llm_response)
        
        return plan_json, llm_response
    
    def _get_system_prompt(self) -> str:
        """Get the system prompt for the planner - strict JSON-only contract."""
        return get_planner_system_prompt()
    
    def _build_user_prompt(
        self,
        user_message: str,
        session_id: str,
        user_id: str,
        session_context: Dict[str, Any]
    ) -> str:
        """Build the user prompt with minimal essential context."""
        # Extract only essential context (avoid token bloat)
        essential_context = {}
        
        # Last message (if exists)
        if "last_message" in session_context:
            essential_context["last_message"] = session_context["last_message"]
        
        # User preferences (if exists)
        if "preferred_category" in session_context:
            essential_context["preferred_category"] = session_context["preferred_category"]
        if "budget" in session_context:
            essential_context["budget"] = session_context["budget"]
        
        # Loyalty tier (if exists)
        if "loyalty_tier" in session_context:
            essential_context["loyalty_tier"] = session_context["loyalty_tier"]
        
        context_str = json.dumps(essential_context) if essential_context else "{}"
        
        return f"""User Message: "{user_message}"

User ID: {user_id}
Essential Context: {context_str}

Generate a JSON action plan."""
    
    def _normalize_llm_output(self, text: str) -> str:
        """
        Normalize LLM output before validation.
        Strips markdown fences, backticks, and prose safely.
        """
        text = text.strip()
        
        # Remove leading prose (e.g., "Here is the JSON:")
        lines = text.split("\n")
        json_start_idx = 0
        
        for i, line in enumerate(lines):
            line_lower = line.lower().strip()
            # Look for JSON start indicators
            if line_lower.startswith("{") or line_lower.startswith("```"):
                json_start_idx = i
                break
        
        text = "\n".join(lines[json_start_idx:])
        
        # Remove markdown code blocks
        if text.startswith("```"):
            lines = text.split("\n")
            # Remove first line (```json or ```)
            if len(lines) > 1:
                lines = lines[1:]
            # Remove last line (```)
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            text = "\n".join(lines)
        
        # Remove any trailing prose
        # Find the last closing brace
        last_brace = text.rfind("}")
        if last_brace > 0:
            text = text[:last_brace + 1]
        
        return text.strip()
    
    def _extract_json(self, text: str) -> Dict[str, Any]:
        """Extract JSON from LLM response with normalization."""
        # Normalize output first
        normalized_text = self._normalize_llm_output(text)
        
        # Try to parse as JSON
        try:
            return json.loads(normalized_text)
        except json.JSONDecodeError as e:
            # Return a default plan if JSON parsing fails
            # The governance agent will fix this
            return {
                "intent": "Parse error - needs governance fix",
                "steps": [],
                "response_style": "professional",
                "_parse_error": str(e),
                "_raw_response": normalized_text[:500]  # First 500 chars for debugging
            }

