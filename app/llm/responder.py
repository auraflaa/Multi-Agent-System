"""Response generator - second LLM call for natural language replies.

This module keeps business logic in deterministic tools and uses the LLM
ONLY to phrase the final response or handle small-talk.
"""
import json
import re
from typing import Dict, Any, List

from app.llm.client import LLMClient
from app.schemas.plan_schema import AgentPlan


class ResponseGenerator:
    """Generates human-friendly responses from tool results and intent."""

    def __init__(self) -> None:
        self.llm = LLMClient()

    def _is_small_talk(self, user_message: str) -> bool:
        """Heuristic: detect greetings / chit-chat that don't need tools."""
        text = user_message.lower()
        small_talk_keywords = [
            "hi",
            "hello",
            "hey",
            "how are you",
            "how's your day",
            "what's up",
            "good morning",
            "good evening",
            "thank you",
            "thanks",
        ]
        if any(k in text for k in small_talk_keywords):
            # Avoid treating product-id queries as small talk
            if "sku-" in text or "prod-" in text or "product_id" in text:
                return False
            return True
        return False

    def _is_capability_query(self, user_message: str) -> bool:
        """Detect questions asking what the assistant/system can do."""
        text = user_message.lower()
        keywords = [
            "what can you do",
            "your capabilities",
            "your capability",
            "explain your capability",
            "how can you help",
            "what are you able to do",
            "what do you do",
        ]
        return any(k in text for k in keywords)

    def _is_user_info_query(self, user_message: str) -> bool:
        """Detect queries asking about user's own information (name, loyalty tier, size, etc.)."""
        text = user_message.lower().strip()
        user_info_patterns = [
            "what is my name",
            "what's my name",
            "my name",
            "who am i",
            "what is my loyalty",
            "what's my loyalty",
            "my loyalty tier",
            "what tier am i",
            "my tier",
            "what is my tier",
            "what's my tier",
            "do you remember my size",
            "do u remember my size",
            "what is my size",
            "what's my size",
            "my size",
            "what size am i",
            "remember my",
            "my preferred size",
            "my gender",
            "what is my gender",
        ]
        return any(pattern in text for pattern in user_info_patterns)

    def _generate_user_info_response(self, user_message: str, context: Dict[str, Any]) -> str:
        """Generate response for user info queries using available context."""
        text = user_message.lower().strip()
        user_profile = context.get("user_profile", {})
        personalization = context.get("personalization", {})
        name = user_profile.get("name", "Guest")
        loyalty_tier = user_profile.get("loyalty_tier", "bronze")
        profile_gender = user_profile.get("gender") or user_profile.get("user_gender") if isinstance(user_profile, dict) else None
        
        # Determine what info is being asked
        if "name" in text:
            return f"Your name is {name}."
        elif "loyalty" in text or "tier" in text:
            # Don't reveal the tier name directly per user requirements
            return f"You're enrolled in our loyalty program with great benefits!"
        elif "size" in text or "remember" in text:
            # Check personalization for size
            preferred_size = personalization.get("preferred_size") if isinstance(personalization, dict) else None
            if preferred_size:
                # Format size for display (M -> Medium)
                from app.utils.size_mapping import get_full_size
                size_display = get_full_size(preferred_size)
                return f"Yes, I remember! Your preferred size is {size_display}."
            else:
                return "I don't have your size preference saved yet. Would you like to tell me your preferred size?"
        elif "gender" in text:
            # Check personalization or profile for gender
            gender = None
            if isinstance(personalization, dict):
                gender = personalization.get("gender")
            if not gender and profile_gender:
                gender = profile_gender

            if gender:
                return f"Based on what I have, your preferred gender is set to {gender}."
            else:
                return (
                    "I don't have your gender preference saved yet. "
                    "Tell me your preferred gender (e.g., female or male) and I'll update it for you."
                )
        else:
            # Generic user info response
            return f"Your name is {name}, and you're enrolled in our loyalty program."

    def _check_if_needs_tools(self, user_message: str, context: Dict[str, Any]) -> bool:
        """
        Lightweight check to determine if a query needs tools BEFORE running the planner.
        Returns True if tools are needed, False ONLY for very trivial queries.
        
        STRICT POLICY: Default to True (use tools) unless it's clearly trivial small talk.
        """
        # Use simple heuristics first
        text = user_message.lower().strip()
        
        # VERY TRIVIAL queries that don't need tools (very short list)
        trivial_patterns = [
            "hi", "hello", "hey", "hi there", "hello there",
            "how are you", "how's your day", "what's up",
            "good morning", "good evening", "good afternoon",
            "thank you", "thanks", "thank you very much",
            "bye", "goodbye", "see you", "see ya"
        ]
        
        # Check if it's pure trivial small talk (exact match or very short)
        if len(text.split()) <= 3:  # Very short messages
            if any(pattern in text for pattern in trivial_patterns):
                # But exclude if it mentions products/clothing/fashion even in small talk
                if not any(term in text for term in ["product", "clothing", "clothes", "fashion", "item", "shirt", "dress"]):
                    return False
        
        # EVERYTHING ELSE needs tools - be very conservative
        # Expanded list of tool-related keywords
        tool_keywords = [
            "check", "inventory", "stock", "available", "availability",
            "recommend", "suggest", "recommendation",
            "find", "find me", "show me", "show", "want", "looking", "need",
            "products", "product", "items", "item",
            "clothing", "clothes", "fashion", "wear", "apparel",
            "shirt", "dress", "top", "pants", "jeans", "skirt", "jacket",
            "female", "male", "women", "men", "woman", "man", "ladies", "guys",
            "browse", "browsing", "all of them", "all of their", "everything",
            "calculate", "payment", "discount", "price", "cost",
            "loyalty", "tier", "membership",
            "fulfillment", "delivery", "pickup", "shipping",
            "order", "cart", "checkout",
            "what", "which", "where", "when", "how much", "how many"  # Questions about products
        ]
        
        # If query contains ANY tool-related keywords, definitely needs tools
        if any(keyword in text for keyword in tool_keywords):
            return True
        
        # Default: if unsure, ALWAYS use tools (be conservative)
        # Only skip tools for pure trivial small talk
        return True

    def _generate_direct_response(self, user_message: str, context: Dict[str, Any]) -> str:
        """
        Generate a direct response for queries that don't need tools.
        Uses LLM to answer general questions, explanations, etc.
        
        NOTE: This should NOT be used for product queries - those MUST go through the planner
        to call recommend_products tool.
        """
        user_profile = context.get("user_profile", {})
        name = user_profile.get("name", "Guest")
        loyalty_tier = user_profile.get("loyalty_tier", "bronze")
        
        # Check if this is actually a product query that should use tools
        text = user_message.lower().strip()
        product_keywords = ["find", "show", "want", "looking", "clothing", "clothes", "fashion", 
                           "shirt", "dress", "top", "pants", "female", "male", "women", "men"]
        if any(keyword in text for keyword in product_keywords):
            # This should have been caught by _check_if_needs_tools, but as a safety net,
            # redirect to tool-based flow
            return None  # Signal that this needs tools
        
        system_prompt = (
            "You are a helpful retail assistant. "
            "Answer the user's question directly and conversationally. "
            "You have access to the user's profile information:\n"
            f"- Name: {name}\n"
            f"- Loyalty Tier: {loyalty_tier}\n"
            "- Do NOT reveal the loyalty tier name (bronze/silver/gold/platinum) explicitly.\n"
            "- Keep responses concise (2-4 sentences).\n"
            "- Be helpful and friendly.\n"
            "- If you don't know something, say so politely.\n"
        )
        
        user_prompt = (
            f"User question: {user_message}\n\n"
            "Answer this question directly. If it's about the user's information, "
            "use the profile data provided above."
        )
        
        try:
            return self.llm.generate(user_prompt, system_prompt=system_prompt)
        except Exception as e:
            return (
                f"I understand your question, but I'm having trouble generating a response right now. "
                f"Please try rephrasing or ask about products, inventory, or recommendations."
            )

    def _has_explicit_ids(self, user_message: str) -> bool:
        """Detect if the user explicitly mentioned product/sku IDs."""
        pattern = r"\b(?:prod-\w+|sku-\w+)\b"
        return re.search(pattern, user_message, flags=re.IGNORECASE) is not None

    def _needs_inventory_clarification(self, user_message: str, intent: str) -> bool:
        """
        Detect requests where the user clearly wants an inventory check but
        hasn't provided enough detail (e.g., size/product) yet.

        In these cases, instead of saying the request is unsupported, we should
        politely ask follow-up questions to collect size and related details.
        """
        text = user_message.lower()
        # Must look like an inventory / availability question
        wants_stock = any(
            k in text
            for k in [
                "in stock",
                "stock",
                "available",
                "availability",
                "check if",
                "is there any",
            ]
        )
        mentions_size = "size" in text
        # No explicit product/SKU IDs given
        has_ids = self._has_explicit_ids(user_message)

        # Trigger only when planner thought it was unsupported,
        # but the pattern clearly matches an inventory-style request.
        return intent == "unsupported_request" and wants_stock and mentions_size and not has_ids

    def _generate_small_talk(self, user_message: str, context: Dict[str, Any]) -> str:
        """Use LLM to handle greetings / chit-chat."""
        system_prompt = (
            "You are a friendly retail assistant. "
            "The user is making small talk or greeting you.\n"
            "- Respond briefly in 1-3 sentences.\n"
            "- Be warm and conversational.\n"
            "- You do NOT need to mention tools, systems, or capabilities.\n"
        )
        last_message = context.get("last_message") or ""
        user_prompt = (
            f"User: {user_message}\n\n"
            f"Previous message from this user (if any): {last_message}\n\n"
            "Reply naturally, as a human assistant would."
        )
        try:
            return self.llm.generate(user_prompt, system_prompt=system_prompt)
        except Exception:
            # Very simple deterministic fallback
            return "I'm doing well, thanks for asking! How can I help you with your shopping today?"

    def _compact_history(
        self,
        history: List[Dict[str, Any]],
        max_items: int = 10,
        max_chars_per_msg: int = 400,
    ) -> List[Dict[str, str]]:
        """
        Return a compact, bounded conversation history to avoid context blow-up.
        Keeps the last `max_items` turns and truncates long messages.
        """
        if not isinstance(history, list):
            return []
        trimmed = history[-max_items:]
        compacted = []
        for turn in trimmed:
            user_text = str(turn.get("user", ""))[:max_chars_per_msg]
            resp_text = str(turn.get("response", ""))[:max_chars_per_msg]
            compacted.append(
                {
                    "user": user_text,
                    "response": resp_text,
                    "intent": turn.get("intent", ""),
                }
            )
        return compacted

    def _is_product_query(self, user_message: str) -> bool:
        """Check if the user message is asking for products/clothing/fashion."""
        user_lower = user_message.lower().strip()
        product_keywords = [
            "find", "show", "want", "looking", "clothing", "clothes", "fashion", 
            "shirt", "dress", "top", "pants", "female", "male", "women", "men",
            "products", "items", "browse", "all of them", "all of their", "anything",
            "give me", "need", "help me", "can you", "could you", "shop", "shopping",
            "branded", "designer", "apparel", "wear", "garment", "outfit", "style",
            "trending", "popular", "recommend", "suggest", "see", "view", "display"
        ]
        return (
            any(keyword in user_lower for keyword in product_keywords) or
            "anything" in user_lower or
            user_lower.startswith("anything") or
            "female" in user_lower or "male" in user_lower or
            "women" in user_lower or "men" in user_lower
        )

    def generate(
        self,
        user_message: str,
        plan: AgentPlan,
        execution_steps: List[Dict[str, Any]],
        context: Dict[str, Any],
    ) -> str:
        """
        Generate a conversational response based on the plan and tool outputs.

        - For normal flows: tools already ran; we summarize their results.
        - For small-talk or unsupported_request: we let the LLM chat normally.
        """
        intent = (plan.intent or "").lower()
        message_history = context.get("message_history", [])
        recent_history = self._compact_history(message_history, max_items=10, max_chars_per_msg=400)

        # CRITICAL: For product queries, NEVER generate response without tool results
        is_product_query = self._is_product_query(user_message)
        if is_product_query and len(execution_steps) == 0:
            # This should never happen if the system is working correctly
            # But if it does, return an error message
            return (
                "I need to search our inventory to find products for you. Let me do that now..."
            )

        # 1) Handle pure small talk regardless of planner intent
        if self._is_small_talk(user_message):
            return self._generate_small_talk(user_message, context)

        # 1b) Capability explanation should always be answered explicitly
        if self._is_capability_query(user_message):
            return (
                "I'm here to help you shop. I can check if items are in stock in your size, suggest products you might like, "
                "use your profile and membership benefits when they apply, give you a clear idea of what your order will cost, "
                "and walk you through delivery or pickup options."
            )

        # 1c) User info queries (name, gender, size, loyalty tier) - answer directly from context
        if self._is_user_info_query(user_message):
            return self._generate_user_info_response(user_message, context)

        # 1d) Inventory-style question missing details: ask for size / product instead
        if self._needs_inventory_clarification(user_message, intent):
            return (
                "I can definitely help with that. Could you tell me which product you're looking at, and the size and gender you want me to check?"
            )

        # 2) Unanswerable / unsupported requests: explain capabilities (abstract)
        # BUT: If it's a product query, we should have called tools, so this shouldn't happen
        if intent == "unsupported_request" and not is_product_query:
            return (
                "I'm not able to fulfill that exact request with the current tools, but I can assist with core retail use cases such as "
                "checking product availability, providing tailored product suggestions, reviewing your existing benefits, "
                "estimating order totals, and outlining delivery or pickup options."
            )

        # 3) Build compact tool results summary
        tool_results: List[Dict[str, Any]] = []
        for step in execution_steps:
            tool_results.append(
                {
                    "action": step.get("step"),
                    "success": step.get("success"),
                    "params": step.get("params"),
                    "result": step.get("result"),
                    "error": step.get("error"),
                }
            )

        successful = [s for s in tool_results if s.get("success")]

        # If there are no successful tool steps and it's not clearly chat, apologize
        if not successful and intent not in ("", "small_talk", "general_chat"):
            return (
                "I tried to process your request but ran into an unexpected issue. "
                "Please try again or rephrase your question."
            )

        has_ids = self._has_explicit_ids(user_message)

        system_prompt = (
            "You are a friendly retail assistant for an e-commerce fashion and electronics store. "
            "You are given the user's message, the detected intent, and the results from "
            "deterministic tools (inventory, recommendations, loyalty, payment, fulfillment, etc.).\n\n"
            "CRITICAL RESPONSE POLICY - EXTRACT AND PRESENT FIRST:\n"
            "- Extract ALL information from tool results and present it immediately\n"
            "- When tool results contain product recommendations, you MUST list the products immediately with names and prices\n"
            "- DO NOT ask questions before showing results - present what you have first\n"
            "- Only ask follow-up questions AFTER presenting results, and only if truly needed for refinement\n"
            "- Make the response actionable and informative, not interrogative\n\n"
            "Your job is to produce a natural, conversational reply:\n"
            "- MANDATORY: When tool results contain product recommendations, you MUST list the products immediately. Show product names and prices. DO NOT ask questions before showing products.\n"
            "- BE PROACTIVE AND HELPFUL: Present tool results directly. Do NOT ask follow-up questions when you already have actionable results to share.\n"
            "- ONLY ask questions AFTER showing products, and only if you want to offer more specific options.\n"
            "- Use ONLY the facts in the tool results; do not invent product availability, prices, or discounts.\n"
            "- ALL prices and amounts are in Indian Rupees (INR). Always mention prices with ₹ symbol or 'INR' when discussing costs.\n"
            "- When presenting product recommendations, list 2-4 products with their names and prices. Be specific and helpful.\n"
            "- Summarize results at a high level; do NOT expose internal database IDs, table names, or raw JSON.\n"
            "- If inventory says a product is out of stock, clearly say so and, if recommendations are available, suggest a couple of alternatives.\n"
            "- If payment info is present, summarize totals and discounts clearly in plain language, always in INR.\n"
            "- Do NOT state the user's loyalty tier by name (e.g., bronze/silver/gold/platinum). "
            "You may refer generically to 'your loyalty benefits' or 'your membership'.\n"
            "- CRITICAL - EXTRACT AND PRESENT FIRST: When tool_results contain product recommendations, you MUST list the products IMMEDIATELY with names and prices. DO NOT ask questions BEFORE showing products.\n"
            "- PRESENTATION ORDER: 1) Show results first, 2) Provide context/explanation, 3) Only then ask specific refinement questions if needed\n"
            "- Keep responses concise but informative (2-4 sentences). Focus on delivering value, not asking questions.\n"
            "- If products were found, present them directly: 'Here are some great options: [Product Name] - ₹[price], [Product Name] - ₹[price]...'\n"
            "- If NO products were found in tool_results, explain what you searched for and why no matches were found, then ask ONE specific clarifying question if needed.\n"
            "- AFTER showing products, you can ask ONE follow-up question like 'Would you like to see more options?' or 'Are you looking for a specific size?' - but only if it adds value.\n"
            "- NEVER ask multiple questions. NEVER ask 'what are you looking for' or 'what kind of X' BEFORE showing products. Show products first, then ask ONE specific question if needed.\n"
            "- For product queries (clothing, fashion, items), ALWAYS show products from tool_results. If tool_results is empty, explain what you searched for and why no results were found.\n"
            "- If the user directly referenced a product ID or SKU, add a short follow-up like "
            "\"By the way, how did you get that ID?\" to understand their journey, but keep it to one sentence.\n"
            "- Use recent conversation history to keep context, but do not repeat it verbatim. Avoid exposing raw JSON or internals.\n"
        )

        payload = {
            "user_message": user_message,
            "intent": plan.intent,
            "tool_results": successful or tool_results,
            "context_summary": {
                "last_intent": context.get("last_intent"),
                "last_message": context.get("last_message"),
            },
            "user_mentioned_ids": has_ids,
            "recent_history": recent_history,
        }

        user_prompt = (
            "User message:\n"
            f"{user_message}\n\n"
            "Intent:\n"
            f"{plan.intent}\n\n"
            "Tool results (JSON, for your reference only):\n"
            f"{json.dumps(payload['tool_results'], indent=2)}\n\n"
            "Context summary (if any):\n"
            f"{json.dumps(payload['context_summary'], indent=2)}\n\n"
            f"User explicitly mentioned product/sku IDs: {payload['user_mentioned_ids']}\n\n"
            "Recent conversation (most recent last, trimmed for brevity):\n"
            f"{json.dumps(payload['recent_history'], indent=2)}\n\n"
            "Now respond to the user following the instructions. Do not reveal raw JSON or internal structures."
        )

        try:
            return self.llm.generate(user_prompt, system_prompt=system_prompt)
        except Exception as e:
            # Fallback: if the responder fails, don't break the flow
            return (
                "I completed the requested checks, but I couldn't generate a detailed response "
                f"due to an internal error ({e}). The tools executed successfully."
            )
