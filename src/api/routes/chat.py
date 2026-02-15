from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import uuid4

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from langchain_core.messages import HumanMessage
from pydantic import BaseModel, Field

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator

router = APIRouter()


class MessageRequest(BaseModel):
    message: str = Field(..., description="User message to the agent")
    thread_id: str | None = Field(None, description="Thread ID for conversation continuity")
    user_id: str = Field(default="default", description="User identifier")
    stream: bool = Field(default=False, description="Whether to stream the response")


class MessageResponse(BaseModel):
    content: str
    thread_id: str


@router.post("/message", response_model=MessageResponse)
async def send_message(request: MessageRequest) -> MessageResponse:
    """Send a message to Ken and get a response.

    Ken is a deep agent with:
    - Web tools (search, scrape, crawl, map)
    - Filesystem access (/user/, /shared/)
    - Subagents (coder, researcher, planner)
    - Todo list for planning
    - Persistent memory via Postgres checkpoints
    """
    from src.agent import create_ken_agent
    from src.config.settings import get_settings

    settings = get_settings()
    thread_id = request.thread_id or f"{request.user_id}-default"

    async with create_ken_agent(settings, user_id=request.user_id) as agent:
        result = await agent.ainvoke(
            {"messages": [HumanMessage(content=request.message)]},
            config={"configurable": {"thread_id": thread_id}},
        )

    last_message = result["messages"][-1]
    content = last_message.content if hasattr(last_message, "content") else str(last_message)

    return MessageResponse(
        content=content,
        thread_id=thread_id,
    )


@router.post("/message/stream")
async def send_message_stream(request: MessageRequest) -> StreamingResponse:
    """Send a message to Ken and stream the response.

    Returns Server-Sent Events with:
    - Content chunks as they're generated
    - [THREAD:id] marker for thread ID
    - [DONE] marker when complete
    """
    from src.agent import create_ken_agent
    from src.config.settings import get_settings

    settings = get_settings()
    thread_id = request.thread_id or f"{request.user_id}-default"

    async def generate() -> AsyncGenerator[str]:
        async with create_ken_agent(settings, user_id=request.user_id) as agent:
            async for chunk in agent.astream(
                {"messages": [HumanMessage(content=request.message)]},
                config={"configurable": {"thread_id": thread_id}},
                stream_mode="values",
            ):
                if "messages" in chunk and chunk["messages"]:
                    last_msg = chunk["messages"][-1]
                    if hasattr(last_msg, "content") and last_msg.content:
                        yield f"data: {last_msg.content}\n\n"
        yield f"data: [THREAD:{thread_id}]\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        },
    )


class SummarizeRequest(BaseModel):
    text: str = Field(..., description="Text to summarize")
    max_length: int = Field(200, description="Maximum summary length in characters")


class SummarizeResponse(BaseModel):
    summary: str


@router.post("/summarize", response_model=SummarizeResponse)
async def summarize(request: SummarizeRequest) -> SummarizeResponse:
    """Summarize text using the configured summarization model.

    This is a utility endpoint that bypasses the agent for fast summarization.
    """
    from langchain_core.messages import HumanMessage, SystemMessage

    from src.config.settings import get_settings
    from src.llm import get_summarization_llm

    settings = get_settings()
    llm = get_summarization_llm()

    messages = [
        SystemMessage(
            content=f"Summarize the following text in no more than {request.max_length} characters. "
            "Be concise and capture the key points."
        ),
        HumanMessage(content=request.text),
    ]

    response = await llm.ainvoke(messages)

    return SummarizeResponse(
        summary=response.content,
    )
