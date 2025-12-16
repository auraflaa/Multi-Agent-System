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
        """Build the user prompt with bounded but richer session context, including user data and personalization."""
        essential_context: Dict[str, Any] = {}

        # Last intent / message (if exists)
        if "last_message" in session_context:
            essential_context["last_message"] = session_context["last_message"]
        if "last_intent" in session_context:
            essential_context["last_intent"] = session_context["last_intent"]

        # User preferences (if exists)
        if "preferred_category" in session_context:
            essential_context["preferred_category"] = session_context["preferred_category"]
        if "budget" in session_context:
            essential_context["budget"] = session_context["budget"]

        # Loyalty tier (if exists)
        if "loyalty_tier" in session_context:
            essential_context["loyalty_tier"] = session_context["loyalty_tier"]

        # ENTIRE conversation history - pass full session conversation to LLM
        history = session_context.get("message_history", [])
        if isinstance(history, list) and history:
            # Include ALL conversation turns (entire session), but truncate very long messages to avoid token limits
            full_history = []
            for turn in history:  # Include all turns, not just last 5
                full_history.append(
                    {
                        "user": str(turn.get("user", ""))[:500],  # Increased from 300 to 500
                        "response": str(turn.get("response", ""))[:500],  # Increased from 300 to 500
                        "intent": str(turn.get("intent", "")),
                    }
                )
            essential_context["conversation_history"] = full_history  # Renamed from "recent_history" to "conversation_history"
            essential_context["total_turns"] = len(full_history)  # Add count for reference

        # Include full user profile data (from database)
        if "user_profile" in session_context:
            essential_context["user_profile"] = session_context["user_profile"]

        # Include full personalization data (from User directory) - ALWAYS include if available
        if "personalization" in session_context:
            personalization = session_context["personalization"]
            if isinstance(personalization, dict) and personalization:
                essential_context["personalization"] = personalization
                # Surface key personalization fields for easier inference
                if "gender" in personalization:
                    essential_context["user_gender"] = personalization["gender"]
                if "preferred_size" in personalization:
                    essential_context["user_preferred_size"] = personalization["preferred_size"]
        else:
            # Explicitly note if personalization is missing
            essential_context["personalization"] = {}

        context_str = json.dumps(essential_context, indent=2) if essential_context else "{}"
        
        # Build comprehensive summary for prompt clarity
        summary_parts = []
        
        # Personalization summary
        if "personalization" in essential_context and essential_context["personalization"]:
            p = essential_context["personalization"]
            summary_parts.append("\n=== PERSONALIZATION DATA ===")
            if "gender" in p:
                summary_parts.append(f"User Gender: {p['gender']}")
            if "preferred_size" in p:
                summary_parts.append(f"Preferred Size: {p['preferred_size']}")
            if "preferred_category" in p:
                summary_parts.append(f"Preferred Category: {p['preferred_category']}")
            if "style_preferences" in p:
                summary_parts.append(f"Style Preferences: {p['style_preferences']}")
            if "orders_being_processed" in p:
                summary_parts.append(f"Orders Being Processed: {p['orders_being_processed']}")
            summary_parts.append("- Use this data to filter recommendations and infer categories.")
            summary_parts.append("- Always include gender parameter when calling recommend_products if available.")
        
        # User profile summary
        if "user_profile" in essential_context and essential_context["user_profile"]:
            up = essential_context["user_profile"]
            summary_parts.append("\n=== USER PROFILE DATA ===")
            if isinstance(up, dict):
                if "name" in up:
                    summary_parts.append(f"Name: {up['name']}")
                if "loyalty_tier" in up:
                    summary_parts.append(f"Loyalty Tier: {up['loyalty_tier']}")
                if "email" in up:
                    summary_parts.append(f"Email: {up['email']}")
        
        # Conversation history summary
        if "conversation_history" in essential_context:
            hist = essential_context["conversation_history"]
            summary_parts.append(f"\n=== CONVERSATION HISTORY ({essential_context.get('total_turns', len(hist))} turns) ===")
            summary_parts.append("- Full conversation history is available in the context JSON above.")
            summary_parts.append("- Use this to understand context, previous requests, and user preferences mentioned earlier.")
        
        summary_text = "\n".join(summary_parts) if summary_parts else ""

        return f"""User Message: "{user_message}"

User ID: {user_id}
Session ID: {session_id}

=== FULL CONTEXT (Session + User Profile + Personalization + Entire Conversation) ===
{context_str}
{summary_text}

CRITICAL INSTRUCTIONS - EXTRACT FIRST, THEN ACT:
- STEP 1: Extract ALL information from user message: category, gender, product type, style, price range, etc.
- STEP 2: Use personalization and conversation history to fill gaps
- STEP 3: Make reasonable inferences for missing information
- STEP 4: Only ask questions if you truly cannot proceed (rare cases)
- STEP 5: Call tools immediately with extracted/inferred information

- MANDATORY TOOL CALLS: If user asks for products, clothing, fashion items, or shopping help (e.g., "find me X", "show me X", "I want X", "looking for X", "browse", "all of them", "all of their"), you MUST:
  1. Extract category and gender from message + personalization
  2. Set "needs_tools": true
  3. Include a step with action "recommend_products" with extracted parameters
  4. NEVER return empty steps array
  5. NEVER set needs_tools=false
  6. DO NOT ask questions - extract, infer, and take action immediately

- Gender inference: "female"/"women"/"woman"/"ladies"/"girl" → gender="female". "male"/"men"/"man"/"guys"/"boy" → gender="male". ALWAYS include gender parameter when calling recommend_products.

- Size and inventory queries: When users ask about sizes, availability, or stock for products, use check_inventory with product_id (from previous recommend_products results) or extract product_id from product names. Size information is in the inventory table, NOT products table. Example: "give me size for each" → call check_inventory(product_id="PROD-001"), check_inventory(product_id="PROD-002") for each product.

- Category inference - GENERALIZE SEARCHES: Map user queries to broader categories (the tool handles fuzzy matching automatically):
  * "clothing", "clothes", "fashion", "apparel", "wear" → "Women's Fashion" (if female) or "Men's Fashion" (if male) or "Fashion" (if unclear)
  * "shirt", "top", "blouse", "t-shirt", "tee" → "Women's Fashion" (if female) or "Men's Fashion" (if male) or "Fashion" (if unclear)
  * "dress", "gown", "frock" → "Women's Fashion"
  * "pants", "trousers", "jeans", "shorts" → "Women's Fashion" (if female) or "Men's Fashion" (if male) or "Fashion" (if unclear)
  * "branded", "designer", "premium" → Use gender-based category (Women's/Men's Fashion)
  * Use broad categories - the tool will automatically search for variations and related terms

- Examples:
  * "find me female clothing" → {{"needs_tools": true, "steps": [{{"action": "recommend_products", "params": {{"category": "Women's Fashion", "gender": "female"}}}}]}}
  * "show me women's fashion" → {{"needs_tools": true, "steps": [{{"action": "recommend_products", "params": {{"category": "Women's Fashion", "gender": "female"}}}}]}}
  * "browse" or "all of them" → {{"needs_tools": true, "steps": [{{"action": "recommend_products", "params": {{"category": "Fashion"}}}}]}}

- NEVER return intent "unsupported_request" or empty steps when user asks for products/clothing/fashion. ALWAYS call recommend_products with appropriate parameters.

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

