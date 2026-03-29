"""
AudioTranscriptionService
Uses LangChain's ChatGoogleGenerativeAI (already installed) with multimodal
input to transcribe Malayalam voice messages and extract order details.
No additional packages required beyond what's already in requirements.txt.
"""
import os
import base64
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage


class AudioTranscriptionService:
    def __init__(self):
        self.name = "Audio Transcription Service"
        gemini_key = os.environ.get("GEMINI_API_KEY")
        
        # LangChain prefers GOOGLE_API_KEY over GEMINI_API_KEY when both exist.
        # For the audio service, force usage of the correct Gemini key explicitly.
        self.llm = ChatGoogleGenerativeAI(
            model="gemini-flash-latest",
            google_api_key=gemini_key,
            temperature=0
        )

    def transcribe(self, audio_bytes: bytes, mime_type: str = "audio/ogg") -> tuple:
        """
        Sends audio bytes to Gemini via LangChain multimodal input for Malayalam transcription.
        Returns (order_details_text, full_transcript) tuple.
        Returns ("", "") on failure.

        Args:
            audio_bytes: Raw audio content downloaded from WhatsApp
            mime_type: MIME type (typically audio/ogg; codecs=opus for WhatsApp voice notes)
        """
        print(f"[{self.name}] Sending {len(audio_bytes)} bytes ({mime_type}) to Gemini...")

        # WhatsApp sends audio/ogg; codecs=opus — strip the codec suffix for Gemini
        clean_mime = mime_type.split(";")[0].strip()

        try:
            audio_b64 = base64.b64encode(audio_bytes).decode("utf-8")

            prompt_text = (
                "This is a voice message from a customer of CJS Designs, an embroidery business in Kerala, India. "
                "The customer may be speaking in Malayalam, English, or a mix of both. "
                "Please do the following:\n"
                "1. Transcribe the audio accurately.\n"
                "2. Translate it clearly into English if it is in Malayalam.\n"
                "3. Identify any embroidery order details mentioned: "
                "fabric/material type, embroidery style or type, stitch count, and requested delivery date.\n\n"
                "Respond in this exact format:\n"
                "TRANSCRIPTION: <original text>\n"
                "TRANSLATION (English): <translated text>\n"
                "ORDER DETAILS: <plain English summary of order fields — fabric, embroidery type, stitch count, delivery date>"
            )

            message = HumanMessage(content=[
                {"type": "text", "text": prompt_text},
                {
                    "type": "media",
                    "mime_type": clean_mime,
                    "data": audio_b64,
                }
            ])

            response = self.llm.invoke([message])
            
            # LangChain multimodal responses return content as a list of blocks
            # Each block is a dict with "type" and "text". We join all text blocks.
            if isinstance(response.content, list):
                full_response = " ".join(
                    block.get("text", "") if isinstance(block, dict) else str(block)
                    for block in response.content
                ).strip()
            else:
                full_response = str(response.content).strip()
                
            print(f"[{self.name}] Raw Gemini response:\n{full_response}")

            order_details = self._extract_section(full_response, "ORDER DETAILS:")
            if not order_details:
                order_details = self._extract_section(full_response, "TRANSLATION (ENGLISH):")
            if not order_details:
                order_details = full_response  # fallback: use entire response

            print(f"[{self.name}] Extracted for pipeline: '{order_details}'")
            return order_details, full_response

        except Exception as e:
            print(f"[{self.name}] Transcription failed: {e}")
            return "", ""

    def _extract_section(self, text: str, label: str) -> str:
        """Extracts the value after a given label from a structured response."""
        for line in text.splitlines():
            if line.strip().upper().startswith(label.upper()):
                parts = line.split(":", 1)
                if len(parts) > 1:
                    return parts[1].strip()
        return ""
