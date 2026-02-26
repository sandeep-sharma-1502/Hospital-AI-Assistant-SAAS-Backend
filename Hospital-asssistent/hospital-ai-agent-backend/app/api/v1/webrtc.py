from fastapi import APIRouter, BackgroundTasks
from pipecat.transports.smallwebrtc.request_handler import (
    SmallWebRTCRequest,
    SmallWebRTCPatchRequest,
    SmallWebRTCRequestHandler,
)
from pipecat.transports.smallwebrtc.transport import SmallWebRTCTransport
from pipecat.transports.base_transport import TransportParams

from app.pipelines.bot_pipeline import start_bot_pipeline

router = APIRouter()
handler = SmallWebRTCRequestHandler()


@router.post("/offer")
async def offer(req: SmallWebRTCRequest, bg: BackgroundTasks):

    async def on_connection(conn):
        transport = SmallWebRTCTransport(
            webrtc_connection=conn,
            params=TransportParams(
                audio_in_enabled=True,
                audio_out_enabled=True,
            ),
        )
        bg.add_task(start_bot_pipeline, transport)

    return await handler.handle_web_request(req, on_connection)


@router.patch("/offer")
async def patch(req: SmallWebRTCPatchRequest):
    return await handler.handle_patch_request(req)