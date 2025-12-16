"""LLM client abstraction for different providers."""
import os
import time
from typing import Dict, Any, Optional
from app.config import LLM_MODEL, GEMINI_API_KEY, LLM_PROVIDER


class LLMClient:
    """Abstracted LLM client supporting multiple providers."""
    
    # Timeout and retry configuration
    REQUEST_TIMEOUT = 15  # seconds
    MAX_RETRIES = 1  # Exactly one retry for transient failures
    
    def __init__(self):
        self.model = LLM_MODEL
        self.api_key = GEMINI_API_KEY
        self.provider = LLM_PROVIDER.lower()
        
        # Fail fast if configured model is not available for the provider
        self._validate_model()
    
    def generate(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        """
        Generate text using the configured LLM with timeout and retry.
        
        Args:
            prompt: User prompt
            system_prompt: Optional system prompt
            
        Returns:
            Generated text response
            
        Raises:
            TimeoutError: If request exceeds timeout
            ValueError: If all retries fail
        """
        last_error = None
        
        for attempt in range(self.MAX_RETRIES + 1):
            try:
                if self.provider == "google":
                    return self._generate_google(prompt, system_prompt)
                elif self.provider == "openai":
                    return self._generate_openai(prompt, system_prompt)
                else:
                    raise ValueError(f"Unsupported LLM provider: {self.provider}")
            except (TimeoutError, ValueError) as e:
                # Don't retry on ValueError (configuration errors)
                if isinstance(e, ValueError) and "not set" in str(e):
                    raise
                last_error = e
                if attempt < self.MAX_RETRIES:
                    time.sleep(0.5)  # Brief delay before retry
                    continue
                raise
            except Exception as e:
                last_error = e
                if attempt < self.MAX_RETRIES:
                    time.sleep(0.5)
                    continue
                raise ValueError(f"LLM request failed after {self.MAX_RETRIES + 1} attempts: {str(e)}") from last_error
        
        raise ValueError(f"LLM request failed: {str(last_error)}")
    
    def _get_model_candidates(self) -> Optional[list[str]]:
        """
        Return an ordered list of candidate models for rate-limit fallback.
        
        For Gemini, we prioritize the models the user actually has access to,
        based on the common text-out models they shared. The configured
        LLM_MODEL is always tried first.
        """
        if self.provider != "google":
            return None

        # Base list from the user's available models (text-out)
        base_candidates = [
            "gemini-2.5-flash",
            "gemini-2.5-flash-lite",
        ]

        # Ensure configured model is first if present
        candidates: list[str] = []
        if self.model:
            candidates.append(self.model)
        for name in base_candidates:
            if name not in candidates:
                candidates.append(name)
        return candidates

    def _validate_model(self) -> None:
        """
        Validate that the configured model exists and supports the required method.
        
        For Google Gemini:
        - Calls genai.list_models()
        - Ensures self.model is in the available list and supports generateContent
        
        For other providers:
        - Currently a no-op (OpenAI errors will surface on first call)
        """
        if self.provider != "google":
            return
        
        if not self.api_key:
            # validate_config() will already enforce this; no need to duplicate
            return
        
        try:
            import google.generativeai as genai
            genai.configure(api_key=self.api_key)
            
            available_models = []
            models = genai.list_models()
            for m in models:
                # m.name is like "models/gemini-1.5-flash"
                # We allow either full name or short name (gemini-1.5-flash)
                name = getattr(m, "name", "")
                short_name = name.split("/")[-1] if "/" in name else name
                supports_generate = "generateContent" in getattr(
                    m, "supported_generation_methods", []
                )
                if supports_generate:
                    available_models.append((name, short_name))
            
            # Build set of both full and short names for lookup
            valid_names = {full for full, short in available_models} | {
                short for full, short in available_models
            }
            
            if self.model not in valid_names and available_models:
                # Try to pick a sensible default from the available Gemini models
                short_names = [short for _, short in available_models]
                fallback = None
                for candidate in self._get_model_candidates() or []:
                    if candidate in short_names:
                        fallback = candidate
                        break
                if not fallback and short_names:
                    fallback = short_names[0]

                if fallback:
                    print(
                        f"[LLMClient] Warning: configured LLM_MODEL '{self.model}' is not "
                        f"available or does not support generateContent. "
                        f"Falling back to '{fallback}'."
                    )
                    self.model = fallback
        except Exception as e:
            # If listing models fails, log a warning but don't crash.
            # The first generate() call will still surface any model issues.
            print(f"[LLMClient] Warning: could not validate Gemini model '{self.model}': {e}")
    
    def _is_rate_limit_error(self, error: Exception) -> bool:
        """Heuristically detect rate-limit / quota errors."""
        msg = str(error).lower()
        return (
            "429" in msg
            or "rate limit" in msg
            or "quota" in msg
            or "exceeded" in msg
        )

    def _generate_google(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        """Generate using Google Gemini API with rate-limit-aware model fallback."""
        import google.generativeai as genai

        if not self.api_key:
            raise ValueError("GEMINI_API_KEY not set for Google provider")

        genai.configure(api_key=self.api_key)

        # Configure generation parameters
        generation_config = {
            "temperature": 0.3,
            "top_p": 0.95,
            "top_k": 40,
            "max_output_tokens": 2048,
        }

        # Combine system prompt and user prompt
        full_prompt = prompt
        if system_prompt:
            full_prompt = f"{system_prompt}\n\n{prompt}"

        candidates = self._get_model_candidates() or [self.model]
        last_error: Optional[Exception] = None

        for model_name in candidates:
            try:
                model = genai.GenerativeModel(
                    model_name=model_name,
                    generation_config=generation_config,
                )
                response = model.generate_content(full_prompt)
                if not response.text:
                    raise ValueError(f"Empty response from Gemini API for model '{model_name}'")

                # Update current model to the working one
                if model_name != self.model:
                    print(
                        f"[LLMClient] Info: switched Gemini model from '{self.model}' "
                        f"to '{model_name}' due to previous errors."
                    )
                    self.model = model_name

                return response.text
            except Exception as e:
                last_error = e
                # If it's a rate-limit/quota error, try the next candidate
                if self._is_rate_limit_error(e):
                    print(
                        f"[LLMClient] Warning: model '{model_name}' hit a rate limit or quota error. "
                        f"Trying next candidate if available."
                    )
                    continue
                # For other errors, raise immediately
                raise

        # If all candidates failed due to rate limits or other errors
        raise ValueError(
            f"All Gemini model candidates failed. Last error: {last_error}"
        )
    
    def _generate_openai(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        """Generate using OpenAI API with timeout."""
        from openai import OpenAI
        
        if not self.api_key:
            raise ValueError("API key not set for OpenAI provider")
        
        client = OpenAI(api_key=self.api_key, timeout=self.REQUEST_TIMEOUT)
        
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        
        try:
            response = client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0.3,
                max_tokens=2048
            )
            return response.choices[0].message.content
        except Exception as e:
            if "timeout" in str(e).lower() or "timed out" in str(e).lower():
                raise TimeoutError(f"LLM request timed out after {self.REQUEST_TIMEOUT}s") from e
            raise

