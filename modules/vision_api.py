import requests
import base64
import cv2
import numpy as np
import logging  # Add logging

logger = logging.getLogger(__name__)  # Add logger

class VisionAPI:
    def __init__(self, api_key=None, api_url=None, system_prompt=None):
        self.api_key = api_key
        self.api_url = api_url  # Use the value passed in, not hardcoded
        self.system_prompt = system_prompt
        print(f"[VisionAPI] Using API URL: {self.api_url}")

    def _call_gemini_api(self, prompt_parts, model_url=None):
        """Helper function to call the Gemini API."""
        if not self.api_key:
            logger.error("API key is not configured.")
            return {"text": "Error: Vision API key not configured."}
        if model_url is None:
            model_url = self.api_url  # Default to the main analysis URL if not specified
        if not model_url:
            logger.error("API URL is not configured.")
            return {"text": "Error: Vision API URL not configured."}

        payload = {"contents": [{"parts": prompt_parts}]}
        request_url = f"{model_url}?key={self.api_key}"
        logger.debug(f"Calling Gemini API: {request_url}")

        try:
            response = requests.post(
                request_url,
                headers={"Content-Type": "application/json"},
                json=payload,
                timeout=45  # Increased timeout slightly
            )
            response.raise_for_status()
            data = response.json()
            candidates = data.get("candidates")
            if not candidates:
                logger.warning(f"No candidates found in response: {data}")
                return {"text": "No response content received from AI."}
            parts = candidates[0].get("content", {}).get("parts")
            if not parts:
                logger.warning(f"No parts found in candidate content: {candidates[0]}")
                return {"text": "No response text received from AI."}
            text = parts[0].get("text", "")
            if not text:
                logger.warning(f"Empty text in response part: {parts[0]}")
                text = "No feedback received from the AI."
            return {"text": text.strip()}
        except requests.exceptions.RequestException as e:
            error_text = f"Error communicating with Gemini API: {e}"
            if hasattr(e, 'response') and e.response is not None:
                error_text += f" | Status: {e.response.status_code} | Response: {e.response.text[:500]}"  # Limit response text length
            logger.error(error_text)
            return {"text": error_text}
        except Exception as e:
            logger.error(f"Unexpected error during Gemini API call: {e}", exc_info=True)
            return {"text": f"Unexpected error communicating with Gemini API: {e}"}

    def analyze_drawing(self, frame):
        """Analyzes drawing for critique using the configured system prompt."""
        logger.info("Requesting drawing analysis/critique...")
        _, buffer = cv2.imencode('.jpg', frame)
        img_b64 = base64.b64encode(buffer).decode('utf-8')
        prompt_parts = [
            {"text": self.system_prompt},
            {"inline_data": {"mime_type": "image/jpeg", "data": img_b64}}
        ]
        return self._call_gemini_api(prompt_parts)

    def get_image_description(self, frame):
        """Gets a detailed textual description of the image."""
        logger.info("Requesting image description...")
        _, buffer = cv2.imencode('.jpg', frame)
        img_b64 = base64.b64encode(buffer).decode('utf-8')
        description_prompt = (
            "Describe this drawing in detail. Focus on the main subject, pose, "
            "key elements, overall composition, and apparent artistic style (e.g., sketch, line art, cartoon). "
            "Be objective and factual."
        )
        prompt_parts = [
            {"text": description_prompt},
            {"inline_data": {"mime_type": "image/jpeg", "data": img_b64}}
        ]
        return self._call_gemini_api(prompt_parts)

    def refine_generation_prompt(self, description, critique):
        """Creates a text-to-image prompt based on description and critique."""
        logger.info("Refining text-to-image generation prompt...")
        refinement_system_prompt = (
            "You are an expert prompt engineer for text-to-image models, specializing in comic book art. "
            "Based on the following description of an original drawing and the critique provided, "
            "create a concise and effective text-to-image prompt. "
            "The goal is to generate a *new* reference image that addresses the critique points (especially anatomy and perspective) "
            "while retaining the core subject, pose, and style described in the original description. "
            "Focus the prompt on visual elements. Do not include conversational text, just the final prompt."
            "\n\n"
            "ORIGINAL DRAWING DESCRIPTION:\n"
            f"{description}\n\n"
            "CRITIQUE/SUGGESTIONS:\n"
            f"{critique}\n\n"
            "GENERATED IMAGE PROMPT:"
        )
        prompt_parts = [{"text": refinement_system_prompt}]
        result = self._call_gemini_api(prompt_parts)
        if "GENERATED IMAGE PROMPT:" in result.get("text", ""):
            result["text"] = result["text"].split("GENERATED IMAGE PROMPT:")[-1].strip()
        return result

    def quick_analysis(self, frame):
        # Optionally implement a lightweight check or just return no suggestion
        return {"needs_assistance": False}

