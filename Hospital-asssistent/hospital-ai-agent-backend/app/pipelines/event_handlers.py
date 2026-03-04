import asyncio
from datetime import datetime, timedelta, timezone

from pipecat.frames.frames import LLMRunFrame, TTSSpeakFrame

from app.services.ai.orchestrator import AIOrchestrator
from app.db.database import AsyncSessionLocal
from app.models.session import Session

MAX_CONTEXT_MESSAGES = 20


def register_event_handlers(transport, task, context, llm_service):

    # ✅ Always use timezone-aware UTC
    last_user_activity = datetime.now(timezone.utc)
    active_session_id = None

    # =====================================================
    # CLIENT CONNECTED
    # =====================================================
    @transport.event_handler("on_client_connected")
    async def on_connected(transport, conn):
        nonlocal active_session_id

        async with AsyncSessionLocal() as db:
            try:
                session = Session(
                    user_identifier=str(conn.id),
                    is_active=True,
                    booking_stage="ASK_DEPARTMENT",
                    booking_data={},
                    last_activity_at=datetime.now(timezone.utc)  # ✅ FIXED
                )

                db.add(session)
                await db.commit()
                await db.refresh(session)

                active_session_id = session.id

            except Exception as e:
                await db.rollback()
                print(f"Session create error: {e}")
                return

        await task.queue_frames([
            TTSSpeakFrame(
                "Namaste, main Shubh hoon. Kaise madad kar sakta hoon?"
            )
        ])

    # =====================================================
    # USER MESSAGE
    # =====================================================
    @transport.event_handler("on_app_message")
    async def on_message(transport, message, sender):
        nonlocal last_user_activity, active_session_id

        if not isinstance(message, dict):
            return

        data = message.get("data", {})
        if data.get("t") != "user-text":
            return

        text = data.get("d", {}).get("text")
        if not text or not active_session_id:
            return

        # ✅ FIXED
        last_user_activity = datetime.now(timezone.utc)

        # =====================================================
        # MAIN DB TRANSACTION BLOCK
        # =====================================================
        async with AsyncSessionLocal() as db:
            try:
                session = await db.get(Session, active_session_id)

                if not session:
                    return

                now = datetime.now(timezone.utc)

                # ✅ SAFE TIMEOUT CHECK
                if session.last_activity_at:
                    # Ensure both are aware (defensive programming)
                    if session.last_activity_at.tzinfo is None:
                        session.last_activity_at = session.last_activity_at.replace(tzinfo=timezone.utc)

                    if now - session.last_activity_at > timedelta(minutes=20):
                        session.booking_data = {}
                        session.booking_stage = "START"

                # ✅ Update activity timestamp
                session.last_activity_at = now

                # 🔥 Orchestrator handles intent internally
                response = await AIOrchestrator.handle_message(
                    text=text,
                    db=db,
                    session=session,
                )

                # Commit DB changes
                await db.commit()

                # If orchestrator returned structured response → speak it
                if response:
                    await task.queue_frames([
                        TTSSpeakFrame(response)
                    ])
                    return

            except Exception as e:
                await db.rollback()

                print("🔥 ORCHESTRATOR ERROR:", e)
                import traceback
                traceback.print_exc()

                await task.queue_frames([
                    TTSSpeakFrame(
                        "Technical issue 2 aa raha hai. Kripya dobara try karein."
                    )
                ])
                return

        # =====================================================
        # LLM FALLBACK (ONLY FOR GENERAL INTENT)
        # =====================================================
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
            await task.queue_frames([
                LLMRunFrame()
            ])
        except Exception as e:
            print("🔥 LLM FALLBACK ERROR:", e)

            await task.queue_frames([
                TTSSpeakFrame(
                    "Technical issue 1 aa raha hai. Kripya dobara try karein."
                )
            ])
            return

    # =====================================================
    # CLIENT DISCONNECTED
    # =====================================================
    @transport.event_handler("on_client_disconnected")
    async def on_disconnected(transport, conn):
        nonlocal active_session_id

        if not active_session_id:
            return

        async with AsyncSessionLocal() as db:
            try:
                session = await db.get(Session, active_session_id)

                if session:
                    session.is_active = False
                    session.ended_at = datetime.now(timezone.utc)  # ✅ FIXED
                    await db.commit()

            except Exception as e:
                await db.rollback()
                print(f"Disconnect error: {e}")

        await task.cancel()