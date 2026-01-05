import os
from typing import *
import google.generativeai as genai

class GeminiLLM:
    """
    A class wrapper for interacting with the Gemini API using the google-genai SDK.
    """
    def __init__(self, config=None):
        cfg = config or {}
        genai.configure(api_key=os.getenv("GEMINI_API_KEY"))    
        self.model_name = cfg.get("gemini_model", "gemini-2.5-flash")
        self.model = genai.GenerativeModel(self.model_name)
        
        
        self.default_llm_kwargs = {
            "model": self.model_name,
            "temperature": cfg.get("temperature", 0.2),
            "max_output_tokens": cfg.get("max_output_tokens", 30000)
        }
    
    def submit_prompt(self, prompt, **kwargs):
        """
        Submits a text prompt to the configured Gemini model and safely extracts the text response.

        Args:
            prompt (str): The text prompt to send to the model.
            **kwargs: Overrides for generation parameters like 'temperature'.

        Returns:
            str: The generated text or an error message if generation fails.
        """
        try:
            # Default generation params
            gen_kwargs = {}
            gen_kwargs["temperature"] = kwargs.get("temperature", self.default_llm_kwargs["temperature"])
            gen_kwargs["max_output_tokens"] = kwargs.get("max_output_tokens", self.default_llm_kwargs["max_output_tokens"])

            # Build GenerationConfig 
            generation_config = genai.types.GenerationConfig(
                temperature=gen_kwargs["temperature"],
                max_output_tokens=gen_kwargs["max_output_tokens"],
            )

            resp = self.model.generate_content(
                prompt,
                generation_config=generation_config,stream=False
            )

            
            text_out = ""

            
            try:
                maybe_text = getattr(resp, "text", None)
                if maybe_text:
                    text_out = maybe_text
            except ValueError:
                 maybe_text = None

            
            if not text_out:
                try:
                    candidates = getattr(resp, "candidates", None) or []
                    for cand in candidates:
                        # Candidate content may be in cand.content or cand.output
                        content = getattr(cand, "content", None) or getattr(cand, "output", None)

                        # If content has 'parts'
                        if content and hasattr(content, "parts"):
                            for part in content.parts:
                                text_out += getattr(part, "text", "") or getattr(part, "plain_text", "") or ""
                        else:
                            if isinstance(content, (str,)):
                                text_out += content
                            else:
                                text_out += getattr(content, "text", "") or ""
                        text_out += getattr(cand, "text", "") or ""

                except Exception:
                    pass
            if not text_out:
                try:
                    text_out = str(resp) if resp is not None else ""
                except Exception:
                    text_out = ""
            if not text_out:
                finish_reason = None
                # finish_reason might be on candidate
                try:
                    if getattr(resp, "candidates", None):
                        finish_reason = getattr(resp.candidates[0], "finish_reason", None)
                    else:
                        finish_reason = getattr(resp, "finish_reason", None)
                except Exception:
                    finish_reason = None

                return f"(No text returned by model. finish_reason={finish_reason}. Consider increasing max_output_tokens or reducing context.)"

            return text_out

        except Exception as e:
            # Returning the error string so your caller doesn't crash
            return f"Error during generation: {e}"
        
    def  system_message(self, message: str) -> str:
        return message
    def user_message(self, message: str) -> str:
        return message
    def assistant_message(self, message: str) -> str:
        return message


if __name__ == "__main__":
    print("GeminiLLM module loaded successfully ✅")