"""Explainability and logging tool."""
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List
from app.config import BASE_DIR
from app.llm.client import LLMClient


def generate_workflow_flow(execution_steps: List[Dict[str, Any]], validation_passed: bool) -> List[Dict[str, Any]]:
    """
    Use LLM to generate a workflow flow visualization based on execution steps.
    
    Args:
        execution_steps: List of execution step results
        validation_passed: Whether validation passed
        
    Returns:
        List of flow step dictionaries with icon, label, class, and title
    """
    if not execution_steps:
        return [{
            "icon": "🛍️",
            "label": "Sales Agent",
            "class": "agent",
            "title": "Sales Agent: Direct response without tools."
        }]
    
    # Map tool names to their agents
    tool_to_agent = {
        'check_inventory': {'name': 'Inventory Agent', 'icon': '📦'},
        'recommend_products': {'name': 'Recommendation Agent', 'icon': '🎯'},
        'get_user_profile': {'name': 'Profile Agent', 'icon': '👤'},
        'get_session_context': {'name': 'Memory Agent', 'icon': '🧠'},
        'apply_offers': {'name': 'Loyalty Agent', 'icon': '⭐'},
        'calculate_payment': {'name': 'Payment Agent', 'icon': '💳'},
        'get_fulfillment_options': {'name': 'Fulfillment Agent', 'icon': '🚚'},
        'suggest_fulfillment': {'name': 'Fulfillment Agent', 'icon': '🚚'},
        'update_user_name': {'name': 'Profile Agent', 'icon': '👤'},
        'update_personalization': {'name': 'Memory Agent', 'icon': '🧠'}
    }
    
    db_backed_tools = ['check_inventory', 'recommend_products', 'apply_offers', 'calculate_payment', 
                       'get_fulfillment_options', 'suggest_fulfillment', 'get_user_profile']
    
    # Extract tool names in execution order
    tool_names = [step.get('step') for step in execution_steps if step.get('step')]
    
    # Build prompt for LLM
    system_prompt = (
        "You are a workflow visualization expert. Generate a JSON array representing the workflow flow "
        "based on execution steps. Each step should have: icon (emoji), label (short name), class (agent/tool), "
        "and title (description).\n\n"
        "Rules:\n"
        "1. Always start with Sales Agent (🛍️)\n"
        "2. Show agents in execution order\n"
        "3. Show DB (🗄️) right after the first agent that uses database-backed tools\n"
        "4. DO NOT add a generic 'Tool' node at the end - the flow should end with the last agent or DB\n"
        "5. Only show Tool node if there are multiple different tools/agents that need aggregation\n"
        "5. Use these agent mappings:\n"
        "- check_inventory → Inventory Agent (📦)\n"
        "- recommend_products → Recommendation Agent (🎯)\n"
        "- get_user_profile → Profile Agent (👤)\n"
        "- get_session_context → Memory Agent (🧠)\n"
        "- apply_offers → Loyalty Agent (⭐)\n"
        "- calculate_payment → Payment Agent (💳)\n"
        "- get_fulfillment_options/suggest_fulfillment → Fulfillment Agent (🚚)\n"
        "6. Database-backed tools: check_inventory, recommend_products, apply_offers, calculate_payment, "
        "get_fulfillment_options, suggest_fulfillment, get_user_profile\n"
        "7. Return ONLY valid JSON array, no markdown, no code blocks\n"
    )
    
    user_prompt = (
        f"Execution steps (in order): {json.dumps(tool_names, indent=2)}\n\n"
        f"Validation passed: {validation_passed}\n\n"
        "Generate the workflow flow as a JSON array of step objects. "
        "Each object should have: icon (string), label (string), class (string: 'agent' or 'tool'), "
        "title (string). Example:\n"
        'Example for single agent: [{"icon": "🛍️", "label": "Sales Agent", "class": "agent"}, {"icon": "🎯", "label": "Recommendation Agent", "class": "agent"}, {"icon": "🗄️", "label": "DB", "class": "tool"}]\n'
        'Example for multiple agents: [{"icon": "🛍️", "label": "Sales Agent", "class": "agent"}, {"icon": "📦", "label": "Inventory Agent", "class": "agent"}, {"icon": "🗄️", "label": "DB", "class": "tool"}, {"icon": "🎯", "label": "Recommendation Agent", "class": "agent"}]\n'
        'DO NOT add a generic "Tool" node unless there are 3+ different agents/tools that need aggregation.'
    )
    
    try:
        llm = LLMClient()
        response = llm.generate(user_prompt, system_prompt=system_prompt)
        
        # Parse JSON response (handle markdown code blocks if present)
        response = response.strip()
        if response.startswith('```'):
            # Extract JSON from markdown code block
            lines = response.split('\n')
            json_lines = [line for line in lines if not line.strip().startswith('```')]
            response = '\n'.join(json_lines)
        
        # Parse JSON
        flow = json.loads(response)
        
        # Validate structure
        if isinstance(flow, list):
            return flow
        else:
            raise ValueError("LLM response is not a list")
            
    except Exception as e:
        print(f"Warning: Could not generate workflow flow with LLM: {e}")
        # Fallback to deterministic generation
        return _generate_deterministic_flow(execution_steps, tool_to_agent, db_backed_tools, validation_passed)


def _generate_deterministic_flow(
    execution_steps: List[Dict[str, Any]],
    tool_to_agent: Dict[str, Dict[str, str]],
    db_backed_tools: List[str],
    validation_passed: bool
) -> List[Dict[str, Any]]:
    """Fallback deterministic flow generation."""
    steps = []
    
    # Always start with Sales Agent
    steps.append({
        "icon": "🛍️",
        "label": "Sales Agent",
        "class": "agent",
        "title": "Sales Agent: orchestrates planning, agents, and tools for your request."
    })
    
    tool_names = [step.get('step') for step in execution_steps if step.get('step')]
    last_agent_type = None
    db_shown = False
    
    for tool_name in tool_names:
        agent_info = tool_to_agent.get(tool_name)
        needs_db = tool_name in db_backed_tools
        
        if agent_info:
            if last_agent_type != agent_info['name']:
                steps.append({
                    "icon": agent_info['icon'],
                    "label": agent_info['name'],
                    "class": "agent",
                    "title": f"{agent_info['name']}: Handles {agent_info['name'].lower()} operations."
                })
                last_agent_type = agent_info['name']
                
                if needs_db and not db_shown:
                    steps.append({
                        "icon": "🗄️",
                        "label": "DB",
                        "class": "tool",
                        "title": "Database: Stores and retrieves product, inventory, user, and order data."
                    })
                    db_shown = True
        elif needs_db and not db_shown:
            steps.append({
                "icon": "🗄️",
                "label": "DB",
                "class": "tool",
                "title": "Database: Stores and retrieves product, inventory, user, and order data."
            })
            db_shown = True
    
    # Only add Tool node if there are multiple different agents/tools (3+)
    # For simple flows with 1-2 agents, end with the last agent/DB
    unique_tools = list(set(tool_names))
    if len(unique_tools) >= 3:
        # Multiple tools - add aggregated Tool node
        valid_text = "Valid" if validation_passed else "Invalid"
        steps.append({
            "icon": "🛠️",
            "label": "Tool",
            "class": "tool" if validation_passed else "error-state",
            "title": f"Tools executed:\n- {chr(10).join(unique_tools)}\nValidation: {valid_text}"
        })
    
    return steps


def log_execution_trace(trace: Dict[str, Any]) -> None:
    """
    Log execution trace for observability and explainability.
    
    Args:
        trace: Dictionary containing execution trace information
    """
    log_dir = BASE_DIR / "app" / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = log_dir / f"execution_trace_{timestamp}.json"
    
    try:
        trace_with_timestamp = {
            "timestamp": datetime.now().isoformat(),
            **trace
        }
        
        with open(log_file, 'w', encoding='utf-8') as f:
            json.dump(trace_with_timestamp, f, indent=2, ensure_ascii=False)
        
        print(f"Execution trace logged to {log_file}")
    except IOError as e:
        print(f"Error logging execution trace: {e}")

