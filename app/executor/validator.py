"""Plan validator that checks plan structure and tool availability."""
from typing import List, Tuple, Dict, Any
from app.schemas.plan_schema import AgentPlan, PlanStep
from app.config import AVAILABLE_TOOLS
from app.llm.governance import GovernanceAgent
from app.tools.tool_specs import TOOL_PARAM_REQUIREMENTS


class PlanValidator:
    """Validates agent plans and triggers governance agent if needed."""
    
    def __init__(self):
        self.governance_agent = GovernanceAgent()
    
    def validate(
        self,
        plan_dict: Dict[str, Any],
        original_response: str = ""
    ) -> Tuple[bool, AgentPlan, List[str], bool]:
        """
        Validate a plan dictionary.
        
        Args:
            plan_dict: Plan dictionary to validate
            original_response: Original LLM response for governance agent
            
        Returns:
            Tuple of:
            - is_valid: boolean
            - validated_plan: AgentPlan object
            - errors: list of error messages
            - was_fixed: boolean indicating if governance agent fixed it
        """
        errors = []
        was_fixed = False
        
        # Check if plan_dict is a dictionary
        if not isinstance(plan_dict, dict):
            errors.append("Plan must be a dictionary")
            return False, self._create_fallback_plan(), errors, was_fixed
        
        # Check required fields
        if "intent" not in plan_dict:
            errors.append("Missing required field: intent")
        if "steps" not in plan_dict:
            errors.append("Missing required field: steps")
        if "response_style" not in plan_dict:
            errors.append("Missing required field: response_style")
        
        # Validate steps
        if "steps" in plan_dict:
            if not isinstance(plan_dict["steps"], list):
                errors.append("Steps must be a list")
            else:
                for i, step in enumerate(plan_dict["steps"]):
                    step_errors = self._validate_step(step, i)
                    errors.extend(step_errors)
        
        # If there are errors, try governance agent
        if errors and original_response:
            try:
                fixed_plan_dict = self.governance_agent.fix_plan(plan_dict, original_response)
                # Re-validate the fixed plan (without governance recursion)
                is_valid, validated_plan, new_errors, _ = self.validate(fixed_plan_dict, "")
                if is_valid:
                    return True, validated_plan, [], True  # Was fixed
                else:
                    errors.extend([f"Governance fix failed: {e}" for e in new_errors])
            except ValueError as e:
                # Semantic constraint violation
                errors.append(f"Governance agent violated constraints: {str(e)}")
            except Exception as e:
                errors.append(f"Governance agent error: {str(e)}")
        
        # If still invalid, return errors
        if errors:
            return False, self._create_fallback_plan(), errors, was_fixed
        
        # Try to create AgentPlan object
        try:
            validated_plan = AgentPlan(**plan_dict)
            return True, validated_plan, [], was_fixed
        except Exception as e:
            errors.append(f"Schema validation error: {str(e)}")
            return False, self._create_fallback_plan(), errors, was_fixed
    
    def _validate_step(self, step: Any, index: int) -> List[str]:
        """Validate a single step including required parameters."""
        errors = []
        
        if not isinstance(step, dict):
            errors.append(f"Step {index} must be a dictionary")
            return errors
        
        if "action" not in step:
            errors.append(f"Step {index} missing required field: action")
            return errors
        
        action = step["action"]
        if action not in AVAILABLE_TOOLS:
            errors.append(
                f"Step {index} has invalid action '{action}'. "
                f"Available: {', '.join(sorted(AVAILABLE_TOOLS))}"
            )
            return errors
        
        if "params" not in step:
            errors.append(f"Step {index} missing required field: params")
            return errors
        
        if not isinstance(step["params"], dict):
            errors.append(f"Step {index} params must be a dictionary")
            return errors
        
        # Validate required parameters for this tool
        required_params = TOOL_PARAM_REQUIREMENTS.get(action, set())
        provided_params = set(step["params"].keys())
        missing_params = required_params - provided_params
        
        if missing_params:
            errors.append(
                f"Step {index} (action: {action}) missing required parameters: {', '.join(missing_params)}"
            )
        
        return errors
    
    def _create_fallback_plan(self) -> AgentPlan:
        """Create a minimal fallback plan."""
        return AgentPlan(
            intent="Error in plan validation - using fallback",
            steps=[],
            response_style="professional"
        )

