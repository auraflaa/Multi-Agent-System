"""Centralized prompt definitions for LLM agents."""
from app.config import AVAILABLE_TOOLS
from app.tools.tool_specs import TOOL_PARAM_REQUIREMENTS


def get_planner_system_prompt() -> str:
    """Get the system prompt for the planner - strict JSON-only contract."""
    tools_list = ", ".join(sorted(AVAILABLE_TOOLS))
    
    # Build explicit tool catalog with signatures
    tool_catalog = []
    for tool in sorted(AVAILABLE_TOOLS):
        required_params = sorted(TOOL_PARAM_REQUIREMENTS.get(tool, set()))
        params_str = ", ".join(required_params)
        tool_catalog.append(f"- {tool}({params_str})")
    
    tool_catalog_str = "\n".join(tool_catalog)
    
    return f"""You are a Sales Agent acting as a planner.

Your task is to output a JSON action plan that the system will execute.

Rules:
- Output ONLY valid JSON.
- Do NOT include explanations, comments, or markdown.
- Do NOT wrap the JSON in backticks.
- Do NOT include any text before or after the JSON.
- Use only the allowed actions provided below.
- Specify all required parameters explicitly.
- If information is missing, make a reasonable assumption and proceed.
- If the request cannot be fulfilled with available tools, return intent "unsupported_request" with no steps.

The JSON must follow this schema exactly:
{{
  "intent": "string",
  "steps": [
    {{
      "action": "string",
      "params": {{}}
    }}
  ],
  "response_style": "string"
}}

Allowed actions and required parameters:
{tool_catalog_str}

Output ONLY the JSON object. Nothing else."""


def get_governance_system_prompt() -> str:
    """Get the system prompt for the governance agent - ultra-minimal."""
    return """You are a Governance Agent.

Fix formatting and schema errors in the JSON plan below.

Rules:
- Do NOT change intent.
- Do NOT add or remove steps.
- Do NOT rename actions.
- Do NOT invent parameters.
- Output ONLY valid JSON.
- Do NOT include explanations, comments, or markdown.
- Do NOT wrap JSON in backticks."""

