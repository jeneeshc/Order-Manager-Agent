"""
AudioTranscriptionService
Uses Gemini 1.5 Flash's native multimodal audio capabilities to transcribe
Malayalam voice messages and extract embroidery order details from them.
No additional API keys required beyond the existing GEMINI_API_KEY.
"""
import os
import base64
import google.generativeai as genai


class AudioTranscriptionService:
    def __init__(self):
        self.name = "Audio Transcription Service"
        api_key = os.environ.get("GEMINI_API_KEY")
        genai.configure(api_key=api_key)
        # Use gemini-1.5-flash which supports inline audio input
        self.model = genai.GenerativeModel("gemini-1.5-flash")

    def transcribe(self, audio_bytes: bytes, mime_type: str = "audio/ogg") -> str:
        """
        Sends audio bytes directly to Gemini for Malayalam transcription.
        Returns a plain English description of what was said, ready for
        the Collector Agent to parse.

        Args:
            audio_bytes: Raw audio content downloaded from WhatsApp
            mime_type: MIME type of the audio (typically audio/ogg for WhatsApp voice notes)

        Returns:
            Transcribed and translated English text, or empty string on failure.
        """
        print(f"[{self.name}] Sending {len(audio_bytes)} bytes of audio to Gemini for Malayalam transcription...")

        try:
            # Encode audio as base64 for inline submission to Gemini
            audio_b64 = base64.b64encode(audio_bytes).decode("utf-8")

            prompt = (
                "This is a voice message from a customer of CJS Designs, an embroidery business in Kerala, India. "
                "The customer is speaking in Malayalam. "
                "Please do the following:\n"
                "1. Transcribe the Malayalam audio accurately.\n"
                "2. Translate it clearly into English.\n"
                "3. Highlight any embroidery order details mentioned: "
                "fabric/material type, embroidery style, stitch count, and requested delivery date.\n\n"
                "Return your response in this exact format:\n"
                "TRANSCRIPTION (Malayalam): <original text>\n"
                "TRANSLATION (English): <translated text>\n"
                "ORDER DETAILS: <plain English summary of order fields for the ordering system>"
            )

            response = self.model.generate_content([
                prompt,
                {
                    "inline_data": {
                        "mime_type": mime_type,
                        "data": audio_b64
                    }
                }
            ])

            full_response = response.text.strip()
            print(f"[{self.name}] Gemini transcription raw response:\n{full_response}")

            # Extract only the ORDER DETAILS line to pass to the Collector Agent
            # This is the actionable part of the response
            order_details = self._extract_order_details(full_response)
            print(f"[{self.name}] Extracted order details for pipeline: '{order_details}'")
            return order_details, full_response  # Return both for WhatsApp echo

        except Exception as e:
            print(f"[{self.name}] Transcription failed: {e}")
            return "", ""

    def _extract_order_details(self, gemini_response: str) -> str:
        """
        Pulls the ORDER DETAILS line out of Gemini's structured response.
        Falls back to the full TRANSLATION if the format wasn't followed.
        """
        lines = gemini_response.splitlines()

        for line in lines:
            if line.strip().upper().startswith("ORDER DETAILS:"):
                return line.split(":", 1)[1].strip()

        # Fallback: return the TRANSLATION line
        for line in lines:
            if line.strip().upper().startswith("TRANSLATION (ENGLISH):"):
                return line.split(":", 1)[1].strip()

        # Last resort: return whole response
        return gemini_response
