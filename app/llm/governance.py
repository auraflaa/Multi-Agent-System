"""Governance Agent - LLM-based validator that fixes invalid JSON plans."""
import json
from typing import Dict, Any, List
from app.llm.client import LLMClient
from app.llm.prompts import get_governance_system_prompt


class GovernanceAgent:
    """LLM-based governance agent that fixes invalid planner output."""
    
    def __init__(self):
        self.llm_client = LLMClient()
    
    def fix_plan(self, invalid_plan: Dict[str, Any], original_response: str) -> Dict[str, Any]:
        """
        Fix invalid plan JSON while preserving intent.
        
        Args:
            invalid_plan: The invalid plan dictionary
            original_response: Original LLM response text
            
        Returns:
            Fixed plan dictionary
            
        Raises:
            ValueError: If governance output violates semantic constraints
        """
        # Capture original plan structure for semantic validation
        original_intent = invalid_plan.get("intent", "")
        original_steps = invalid_plan.get("steps", [])
        original_step_count = len(original_steps) if isinstance(original_steps, list) else 0
        original_actions = []
        if isinstance(original_steps, list):
            for step in original_steps:
                if isinstance(step, dict) and "action" in step:
                    original_actions.append(step["action"])
        
        system_prompt = self._get_system_prompt()
        user_prompt = self._build_fix_prompt(invalid_plan, original_response)
        
        # Get LLM response
        llm_response = self.llm_client.generate(user_prompt, system_prompt)
        
        # Extract JSON
        fixed_plan = self._extract_json(llm_response)
        
        # SEMANTIC GUARDRAILS: Verify governance didn't change intent/steps
        self._validate_semantic_preservation(
            fixed_plan,
            original_intent,
            original_step_count,
            original_actions
        )
        
        return fixed_plan
    
    def _validate_semantic_preservation(
        self,
        fixed_plan: Dict[str, Any],
        original_intent: str,
        original_step_count: int,
        original_actions: List[str]
    ) -> None:
        """
        Validate that governance agent preserved semantic structure.
        
        Raises:
            ValueError: If semantic constraints are violated
        """
        fixed_intent = fixed_plan.get("intent", "")
        fixed_steps = fixed_plan.get("steps", [])
        fixed_step_count = len(fixed_steps) if isinstance(fixed_steps, list) else 0
        fixed_actions = []
        if isinstance(fixed_steps, list):
            for step in fixed_steps:
                if isinstance(step, dict) and "action" in step:
                    fixed_actions.append(step["action"])
        
        # Guardrail 1: Step count must match
        if fixed_step_count != original_step_count:
            raise ValueError(
                f"Governance violated constraint: step count changed from {original_step_count} to {fixed_step_count}"
            )
        
        # Guardrail 2: Action names must match exactly (order may differ, but same actions)
        if set(fixed_actions) != set(original_actions):
            raise ValueError(
                f"Governance violated constraint: actions changed from {original_actions} to {fixed_actions}"
            )
        
        # Guardrail 3: Intent must match (allowing minor normalization)
        # Normalize for comparison (lowercase, strip)
        normalized_original = original_intent.lower().strip()
        normalized_fixed = fixed_intent.lower().strip()
        
        # Allow some variation but core intent should be similar
        # If intent is completely different, reject
        if normalized_original and normalized_fixed:
            # Simple check: if fixed intent doesn't contain key words from original, reject
            original_words = set(normalized_original.split())
            fixed_words = set(normalized_fixed.split())
            
            # If original has meaningful words and none overlap, it's too different
            if len(original_words) > 2 and len(original_words.intersection(fixed_words)) == 0:
                raise ValueError(
                    f"Governance violated constraint: intent changed significantly from '{original_intent}' to '{fixed_intent}'"
                )
    
    def _get_system_prompt(self) -> str:
        """Get the system prompt for the governance agent - ultra-minimal."""
        return get_governance_system_prompt()
    
    def _build_fix_prompt(
        self,
        invalid_plan: Dict[str, Any],
        original_response: str
    ) -> str:
        """Build the prompt for fixing the plan - minimal context."""
        invalid_json = json.dumps(invalid_plan, indent=2)
        
        return f"""Invalid JSON plan:

{invalid_json}

Fix formatting and schema errors. Preserve intent, steps, and actions exactly."""
    
    def _normalize_llm_output(self, text: str) -> str:
        """Normalize LLM output (same logic as planner)."""
        text = text.strip()
        
        # Remove leading prose
        lines = text.split("\n")
        json_start_idx = 0
        
        for i, line in enumerate(lines):
            line_lower = line.lower().strip()
            if line_lower.startswith("{") or line_lower.startswith("```"):
                json_start_idx = i
                break
        
        text = "\n".join(lines[json_start_idx:])
        
        # Remove markdown code blocks
        if text.startswith("```"):
            lines = text.split("\n")
            if len(lines) > 1:
                lines = lines[1:]
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            text = "\n".join(lines)
        
        # Remove any trailing prose
        last_brace = text.rfind("}")
        if last_brace > 0:
            text = text[:last_brace + 1]
        
        return text.strip()
    
    def _extract_json(self, text: str) -> Dict[str, Any]:
        """Extract JSON from LLM response with normalization."""
        normalized_text = self._normalize_llm_output(text)
        
        try:
            return json.loads(normalized_text)
        except json.JSONDecodeError:
            # If governance also fails, raise error (don't return fallback)
            raise ValueError(f"Governance agent failed to produce valid JSON: {normalized_text[:200]}")

