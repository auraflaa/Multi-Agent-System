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

        # 1) Handle pure small talk regardless of planner intent
        if self._is_small_talk(user_message):
            return self._generate_small_talk(user_message, context)

        # 1b) Capability explanation should always be answered explicitly
        if self._is_capability_query(user_message):
            return (
                "I’m here to help you shop. I can check if items are in stock in your size, suggest products you might like, "
                "use your profile and membership benefits when they apply, give you a clear idea of what your order will cost, "
                "and walk you through delivery or pickup options."
            )

        # 1c) Inventory-style question missing details: ask for size / product instead
        if self._needs_inventory_clarification(user_message, intent):
            return (
                "I can definitely help with that. Could you tell me which product you’re looking at, and the size and gender you want me to check?"
            )

        # 2) Unanswerable / unsupported requests: explain capabilities (abstract)
        if intent == "unsupported_request":
            return (
                "I’m not able to fulfill that exact request with the current tools, but I can assist with core retail use cases such as "
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
            "Your job is to produce a natural, conversational reply:\n"
            "- BE PROACTIVE AND HELPFUL: When tool results contain product recommendations or inventory data, present them directly. Do NOT ask follow-up questions when you already have actionable results to share. Only ask questions if the tools returned no results or if critical information is truly missing.\n"
            "- Use ONLY the facts in the tool results; do not invent product availability, prices, or discounts.\n"
            "- ALL prices and amounts are in Indian Rupees (INR). Always mention prices with ₹ symbol or 'INR' when discussing costs.\n"
            "- When presenting product recommendations, list 2-4 products with their names and prices. Be specific and helpful.\n"
            "- Summarize results at a high level; do NOT expose internal database IDs, table names, or raw JSON.\n"
            "- You may mention product IDs or SKUs only if the user explicitly mentioned them first.\n"
            "- If inventory says a product is out of stock, clearly say so and, if recommendations are available, suggest a couple of alternatives.\n"
            "- If payment info is present, summarize totals and discounts clearly in plain language, always in INR.\n"
            "- Do NOT state the user's loyalty tier by name (e.g., bronze/silver/gold/platinum). "
            "You may refer generically to 'your loyalty benefits' or 'your membership'.\n"
            "- Keep responses concise but informative (2-4 sentences). Focus on delivering value, not asking questions.\n"
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


