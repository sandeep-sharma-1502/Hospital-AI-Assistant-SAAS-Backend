from pipecat.services.sarvam.stt import SarvamSTTService
from pipecat.services.sarvam.tts import SarvamTTSService
from pipecat.services.groq.llm import GroqLLMService
from pipecat.transcriptions.language import Language
from pipecat.processors.aggregators.llm_context import LLMContext

from app.core.config import settings


def create_services():

    # STT
    stt = SarvamSTTService(
        api_key=settings.sarvam_api_key,
        model="saaras:v3",
    )

    # LLM (manual trigger only)
    llm = GroqLLMService(
        api_key=settings.groq_api_key,
        model=settings.llm_model,
        temperature=0.2,
    )

    # TTS
    tts = SarvamTTSService(
        api_key=settings.sarvam_api_key,
        model=settings.tts_model,
        voice_id=settings.tts_voice,
        params=SarvamTTSService.InputParams(
            language=Language.HI,
        ),
    )

    # Context for manual LLM
    context = LLMContext([
        {
            "role": "system",
            "content": """
You are 'Shubh' — a male AI Care Coordinator at St. Jude General Hospital.

Rules:
- Speak in Hinglish.
- Keep answers short.
- Be polite.
- Do not hallucinate doctor availability.
"""
        }
    ])

    return {
        "stt": stt,
        "llm": llm,
        "tts": tts,
        "context": context,
    }