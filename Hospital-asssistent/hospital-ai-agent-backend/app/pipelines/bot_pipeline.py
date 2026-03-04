# app/pipelines/bot_pipeline.py

from pipecat.pipeline.pipeline import Pipeline
from pipecat.pipeline.runner import PipelineRunner
from pipecat.pipeline.task import PipelineTask, PipelineParams

from app.pipelines.pipeline_factory import create_services
from app.pipelines.event_handlers import register_event_handlers


async def start_bot_pipeline(transport):
    """
    Starts the voice bot pipeline.

    Architecture:
    Audio In → STT → (Handled via event orchestrator) → TTS → Audio Out

    IMPORTANT:
    LLM is NOT part of automatic pipeline.
    It is triggered manually via LLMRunFrame() from event_handlers.
    """

    # -------------------------------------------------
    # Create Services
    # -------------------------------------------------
    services = create_services()

    # -------------------------------------------------
    # Pipeline (NO auto LLM execution)
    # -------------------------------------------------
    pipeline = Pipeline([
        transport.input(),     # 🎤 Mic Input
        services["stt"],       # 🗣 Speech → Text
        services["tts"],       # 🔊 Text → Speech
        transport.output(),    # 📢 Speaker Output
    ])

    # -------------------------------------------------
    # Pipeline Task Configuration
    # -------------------------------------------------
    task = PipelineTask(
        pipeline,
        params=PipelineParams(
            audio_in_sample_rate=16000,
            audio_out_sample_rate=24000,
            enable_metrics=True,
        ),
    )

    # -------------------------------------------------
    # Register Custom Event Handlers
    # -------------------------------------------------
    # Booking logic + LLM fallback handled here
    register_event_handlers(
        transport=transport,
        task=task,
        context=services["context"],
        llm_service=services["llm"],
    )

    # -------------------------------------------------
    # Run Pipeline
    # -------------------------------------------------
    runner = PipelineRunner(handle_sigint=False)
    await runner.run(task)