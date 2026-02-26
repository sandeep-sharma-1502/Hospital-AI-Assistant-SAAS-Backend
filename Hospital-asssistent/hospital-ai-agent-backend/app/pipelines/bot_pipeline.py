import asyncio
import time
from datetime import datetime, timedelta
from loguru import logger

from pipecat.audio.vad.silero import SileroVADAnalyzer
from pipecat.frames.frames import LLMRunFrame, TTSSpeakFrame
from pipecat.pipeline.pipeline import Pipeline
from pipecat.pipeline.runner import PipelineRunner
from pipecat.pipeline.task import PipelineTask, PipelineParams

from pipecat.processors.aggregators.llm_context import LLMContext
from pipecat.processors.aggregators.llm_response_universal import (
    LLMContextAggregatorPair,
    LLMUserAggregatorParams,
)

from pipecat.services.sarvam.stt import SarvamSTTService
from pipecat.services.sarvam.tts import SarvamTTSService
from pipecat.transcriptions.language import Language
from pipecat.services.groq import GroqLLMService

from app.core.config import settings
from app.utils.retry import async_retry


async def start_bot_pipeline(transport):

    logger.info("Hospital AI Bot Started")

    # ---------------- SERVICES ----------------
    stt = SarvamSTTService(
        api_key=settings.sarvam_api_key,
        model="saaras:v3",
    )

    llm = GroqLLMService(
        api_key=settings.groq_api_key,
        model=settings.llm_model,
        params=GroqLLMService.InputParams(
            temperature=settings.llm_temperature,
            top_p=settings.llm_top_p,
            max_completion_tokens=settings.llm_max_tokens,
        ),
    )

    tts = SarvamTTSService(
        api_key=settings.sarvam_api_key,
        model=settings.tts_model,
        voice_id=settings.tts_voice,
        params=SarvamTTSService.InputParams(
            language=Language.HI,
            pace=settings.tts_pace,
            temperature=settings.tts_temperature,
        ),
    )

    # ---------------- CONTEXT ----------------
    context = LLMContext([
        {
            "role": "system",
            "content": """
You are 'Shubh' — a male AI Care Coordinator at St. Jude General Hospital.
Speak in Hinglish. Keep answers short and polite.
"""
        }
    ])

    MAX_CONTEXT_MESSAGES = 20

    user_agg, assistant_agg = LLMContextAggregatorPair(
        context,
        user_params=LLMUserAggregatorParams(
            vad_analyzer=SileroVADAnalyzer()
        ),
    )

    pipeline = Pipeline([
        transport.input(),
        stt,
        user_agg,
        llm,
        tts,
        transport.output(),
        assistant_agg,
    ])

    task = PipelineTask(
        pipeline,
        params=PipelineParams(
            audio_in_sample_rate=16000,
            audio_out_sample_rate=24000,
            enable_metrics=True,
        ),
    )

    # ---------------- ACTIVE CONNECTIONS ----------------
    active_connections = 0

    # ---------------- CIRCUIT BREAKER ----------------
    failure_count = 0
    last_failure_time = None
    FAILURE_THRESHOLD = 5
    RECOVERY_TIME = 60

    @async_retry(max_attempts=3)
    async def safe_llm_call():
        nonlocal failure_count, last_failure_time

        start_time = time.time()

        if failure_count >= FAILURE_THRESHOLD:
            if time.time() - last_failure_time < RECOVERY_TIME:
                raise Exception("Circuit open")
            else:
                failure_count = 0

        try:
            await task.queue_frames([LLMRunFrame()])
            duration = time.time() - start_time
            logger.info(f"LLM success | latency={duration:.2f}s")

        except Exception as e:
            failure_count += 1
            last_failure_time = time.time()
            duration = time.time() - start_time
            logger.error(f"LLM failure | latency={duration:.2f}s | error={e}")
            raise e

    # ---------------- INACTIVITY ----------------
    reminder_count = 0
    last_user_activity = datetime.utcnow()
    inactivity_task = None

    async def check_user_inactivity():
        nonlocal reminder_count, last_user_activity

        try:
            while reminder_count < settings.max_reminders:
                await asyncio.sleep(settings.reminder_interval)

                if datetime.utcnow() - last_user_activity >= timedelta(
                    seconds=settings.reminder_interval
                ):
                    reminder_count += 1

                    try:
                        if reminder_count < settings.max_reminders:
                            await task.queue_frames([
                                TTSSpeakFrame("Kya aap mujhe sun pa rahe hain?")
                            ])
                        else:
                            await task.queue_frames([
                                TTSSpeakFrame("Main session close kar raha hoon.")
                            ])
                            break
                    except Exception as e:
                        logger.error(f"TTS failure: {e}")
        except asyncio.CancelledError:
            logger.info("Inactivity task cancelled")

    # ---------------- EVENTS ----------------

    @transport.event_handler("on_client_connected")
    async def on_connected(transport, conn):
        nonlocal reminder_count, last_user_activity, inactivity_task, active_connections

        active_connections += 1
        logger.info(f"Client Connected | active={active_connections}")

        reminder_count = 0
        last_user_activity = datetime.utcnow()

        await task.queue_frames([
            TTSSpeakFrame("Namaste, main Shubh hoon. Kaise madad kar sakta hoon?")
        ])

        if inactivity_task:
            inactivity_task.cancel()

        inactivity_task = asyncio.create_task(check_user_inactivity())

    @transport.event_handler("on_app_message")
    async def on_message(transport, message, sender):
        nonlocal reminder_count, last_user_activity

        if not isinstance(message, dict):
            return

        data = message.get("data", {})
        if data.get("t") == "user-text":
            text = data.get("d", {}).get("text")
            if not text:
                return

            reminder_count = 0
            last_user_activity = datetime.utcnow()

            context.messages.append({
                "role": "user",
                "content": text,
            })

            if len(context.messages) > MAX_CONTEXT_MESSAGES:
                context.messages = (
                    [context.messages[0]] +
                    context.messages[-(MAX_CONTEXT_MESSAGES - 1):]
                )

            try:
                await asyncio.wait_for(
                    safe_llm_call(),
                    timeout=20
                )
            except asyncio.TimeoutError:
                logger.error("LLM timeout")
                await task.queue_frames([
                    TTSSpeakFrame("Server slow chal raha hai. Thoda baad try karein.")
                ])
            except Exception as e:
                logger.error(f"LLM failed after retries: {e}")
                await task.queue_frames([
                    TTSSpeakFrame("Technical issue aa raha hai. Kripya dobara try karein.")
                ])

    @transport.event_handler("on_client_disconnected")
    async def on_disconnected(transport, conn):
        nonlocal active_connections

        active_connections -= 1
        logger.info(f"Client Disconnected | active={active_connections}")

        if inactivity_task:
            inactivity_task.cancel()

        await task.cancel()

    runner = PipelineRunner(handle_sigint=False)
    await runner.run(task)