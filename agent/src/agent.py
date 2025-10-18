import logging
from dataclasses import dataclass
from typing import Any

from dotenv import load_dotenv
from livekit.agents import (
    Agent,
    AgentSession,
    JobContext,
    JobProcess,
    WorkerOptions,
    cli,
)

# Compatibility shim for older livekit-agents versions that lack newer LLM helpers.
try:
    from livekit.agents import llm as _lk_llm

    if not hasattr(_lk_llm, "LLMCapabilities"):
        @dataclass
        class _LLMCapabilities:  # minimal stub used by latest openai plugin
            supports_choices_on_int: bool = False
            requires_persistent_functions: bool = False

        _lk_llm.LLMCapabilities = _LLMCapabilities

    if not hasattr(_lk_llm, "ToolChoice"):
        _lk_llm.ToolChoice = Any  # type: ignore[attr-defined]

    if not hasattr(_lk_llm.ChatContext, "_metadata"):
        def _compat_metadata(self) -> dict[str, Any]:
            if not hasattr(self, "__compat_metadata"):
                self.__compat_metadata = {}
            return self.__compat_metadata

        _lk_llm.ChatContext._metadata = property(_compat_metadata)  # type: ignore[attr-defined]
except Exception:
    pass

from livekit.plugins import openai, silero

logger = logging.getLogger("agent")
logger.setLevel(logging.DEBUG)

load_dotenv(".env.local")


class Assistant(Agent):
    def __init__(self) -> None:
        super().__init__(
            instructions="""You are a helpful and enthusiastic AI assistant.
            The user is interacting with you via voice.
            Keep your responses concise, clear, and conversational.
            Be friendly and speak naturally.""",
        )


def prewarm(proc: JobProcess):
    proc.userdata["vad"] = silero.VAD.load()


async def entrypoint(ctx: JobContext):
    logger.info(f"🎯 Entrypoint called for room: {ctx.room.name}")
    ctx.log_context_fields = {"room": ctx.room.name}

    try:
        logger.info("🤖 Creating OpenAI Realtime model...")
        # Initialize OpenAI Realtime model (handles STT, LLM, and TTS)
        session = AgentSession(
            llm=openai.realtime.RealtimeModel(
                voice="alloy",  # Available: alloy, echo, fable, onyx, nova, shimmer
                temperature=0.8,
            )
        )

        logger.info("🚀 Starting agent session...")
        # Start the session and connect to the room
        await session.start(agent=Assistant(), room=ctx.room)
        
        logger.info("🔌 Connecting to room...")
        await ctx.connect()
        
        logger.info(f"✅ Agent successfully connected to room: {ctx.room.name}")
    except Exception as e:
        logger.error(f"❌ Error in entrypoint: {e}", exc_info=True)
        raise


if __name__ == "__main__":
    cli.run_app(WorkerOptions(entrypoint_fnc=entrypoint, prewarm_fnc=prewarm))
