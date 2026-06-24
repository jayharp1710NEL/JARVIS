"""Chat endpoints — full pipeline and streaming."""
from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from ..agent.orchestrator import AgentOrchestrator, stream_answer
from ..agent.schemas import ChatRequest, ChatResponse

router = APIRouter(tags=["chat"])


@router.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest) -> ChatResponse:
    orchestrator = AgentOrchestrator()
    return orchestrator.run(req)


@router.post("/chat/stream")
async def chat_stream(req: ChatRequest):
    orchestrator = AgentOrchestrator()

    async def gen():
        try:
            async for token in stream_answer(orchestrator, req):
                yield token
        except Exception as exc:  # noqa: BLE001
            yield f"\n[stream error: {exc}]"

    return StreamingResponse(gen(), media_type="text/plain")
