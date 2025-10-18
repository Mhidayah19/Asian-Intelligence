import asyncio
import logging
import os
import time
from collections import deque
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from dotenv import load_dotenv
from livekit import agents, rtc
from livekit.agents import (
    Agent,
    AgentSession,
    ChatContext,
    JobContext,
    RoomInputOptions,
    get_job_context,
)
from livekit.agents.llm import ImageContent
from livekit.agents.utils.images import EncodeOptions, ResizeOptions, encode
from livekit.plugins import openai, silero

try:
    from livekit.plugins.noise_cancellation import BVC as NoiseBVC
except Exception:
    NoiseBVC = None

logger = logging.getLogger("unified-agent")
load_dotenv(".env.local")


# ============================================================================
# CONFIGURATION
# ============================================================================


@dataclass
class VideoConfig:
    """Video processing configuration."""

    # Camera settings
    camera_max_dim: int = int(os.getenv("CAMERA_MAX_DIM", "1024"))
    camera_quality: int = int(os.getenv("CAMERA_JPEG_QUALITY", "85"))

    # Screen share settings
    screen_max_w: int = int(os.getenv("SCREEN_MAX_W", "1280"))
    screen_max_h: int = int(os.getenv("SCREEN_MAX_H", "720"))
    screen_format: str = os.getenv("SCREEN_FORMAT", "JPEG")
    screen_quality: int = int(os.getenv("SCREEN_JPEG_QUALITY", "80"))

    # Sampling rates
    fps_speaking: float = float(os.getenv("FPS_SPEAKING", "2.0"))
    fps_idle: float = float(os.getenv("FPS_IDLE", "0.0"))

    # Frame selection
    max_frames_per_turn: int = int(os.getenv("VISION_MAX_FRAMES_PER_TURN", "1"))
    buffer_size: int = 10




# ============================================================================
# VIDEO BUFFER MANAGER
# ============================================================================


class VideoBufferManager:
    """Manages video frame buffers and selection."""

    def __init__(self, config: VideoConfig):
        self.config = config
        self.buffers: Dict[str, deque] = {
            "camera": deque(maxlen=config.buffer_size),
            "screenshare": deque(maxlen=config.buffer_size),
        }
        self.last_capture_ts: Dict[str, Optional[float]] = {
            "camera": None,
            "screenshare": None,
        }

    def should_capture(self, kind: str, fps: float) -> bool:
        """Check if we should capture a frame."""
        if fps <= 0:
            return False

        now = time.time()
        last_ts = self.last_capture_ts[kind]

        if last_ts is None:
            return True

        return (now - last_ts) >= (1.0 / max(fps, 0.1))

    def add_frame(self, kind: str, frame_data: str):
        """Add a frame to the buffer."""
        self.buffers[kind].append((time.time(), kind, frame_data))
        self.last_capture_ts[kind] = time.time()

    def select_frames(self) -> List[Tuple[float, str, str]]:
        """
        Select frames for LLM processing.
        Prioritizes screen share over camera.
        """
        frames = []

        # Prefer screen share
        screen_frames = self._pick_frames(self.buffers["screenshare"])
        frames.extend(screen_frames)

        # Fill remaining with camera
        if len(frames) < self.config.max_frames_per_turn:
            remaining = self.config.max_frames_per_turn - len(frames)
            camera_frames = self._pick_frames(self.buffers["camera"], remaining)
            frames.extend(camera_frames)

        return frames

    def _pick_frames(self, buffer: deque, max_count: Optional[int] = None) -> List[Tuple[float, str, str]]:
        """Pick frames from buffer using first/middle/last strategy."""
        if max_count is None:
            max_count = self.config.max_frames_per_turn

        if not buffer:
            return []
        if len(buffer) == 1:
            return [buffer[0]]
        if len(buffer) == 2:
            return [buffer[0], buffer[-1]]

        selected = [buffer[0], buffer[len(buffer) // 2], buffer[-1]]
        return selected[:max_count]

    def clear(self):
        """Clear all buffers."""
        for buf in self.buffers.values():
            buf.clear()

    def has_frames(self) -> bool:
        """Check if any buffers have frames."""
        return any(len(buf) > 0 for buf in self.buffers.values())


# ============================================================================
# UNIFIED ASSISTANT
# ============================================================================


class UnifiedAssistant(Agent):
    """
    Unified AI Assistant with automatic mode switching:
    - Voice-only mode (1-2s): Fast text responses
    - Vision mode (2-4s): Image analysis when video present
    """

    def __init__(self) -> None:
        self.config = VideoConfig()
        self.buffers = VideoBufferManager(self.config)

        # Stream management
        self._camera_stream: Optional[rtc.VideoStream] = None
        self._screen_share_stream: Optional[rtc.VideoStream] = None
        self._tasks: List[asyncio.Task] = []

        # State
        self._is_capturing = False
        self._current_mode = "voice-only"

        # Instructions
        super().__init__(
            instructions="""You are a strict Asian parent who is also a math tutor. Be encouraging but demanding.

CRITICAL VISION RULES:
- When ImageContent is present in the message: Analyze the visible content carefully and reference specific details
- When NO ImageContent: Do NOT claim to see anything. Say "I cannot see your screen/camera right now"
- NEVER hallucinate vision capabilities

Always be in character as an Asian parent tutor."""
        )

    async def on_enter(self):
        """Subscribe to video tracks when entering room."""
        room = get_job_context().room

        # Subscribe to existing tracks
        for participant in room.remote_participants.values():
            for publication in participant.track_publications.values():
                if publication.track and publication.kind == rtc.TrackKind.KIND_VIDEO:
                    self._subscribe_to_track(publication.track, publication)

        # Listen for new tracks
        @room.on("track_subscribed")
        def on_track(track: rtc.Track, publication: rtc.RemoteTrackPublication, participant: rtc.RemoteParticipant):
            if track.kind == rtc.TrackKind.KIND_VIDEO:
                self._subscribe_to_track(track, publication)

        # Capture control
        @self.agent_session.on("user_speech_started")
        def on_speech_start():
            self.buffers.clear()
            self._is_capturing = True
            logger.info("🎙️ User speaking - capturing frames")

        @self.agent_session.on("user_speech_committed")
        def on_speech_end():
            self._is_capturing = False

    def _subscribe_to_track(self, track: rtc.Track, publication: rtc.RemoteTrackPublication):
        """Subscribe to a video track."""
        source = publication.source

        if source == rtc.TrackSource.SOURCE_CAMERA:
            logger.info("📷 Camera track detected")
            self._create_stream(track, "camera")
        elif source == rtc.TrackSource.SOURCE_SCREENSHARE or source == 3:
            logger.info("🖥️ Screen share track detected")
            self._create_stream(track, "screenshare")

    def _create_stream(self, track: rtc.Track, kind: str):
        """Create and start processing a video stream."""
        stream = rtc.VideoStream(track)

        if kind == "camera":
            self._camera_stream = stream
        else:
            self._screen_share_stream = stream

        task = asyncio.create_task(self._process_stream(stream, kind))
        self._tasks.append(task)

    async def _process_stream(self, stream: rtc.VideoStream, kind: str):
        """Process frames from a video stream."""
        async for frame in stream:
            if not self._is_capturing:
                continue

            fps = self.config.fps_speaking if self._is_capturing else self.config.fps_idle
            if not self.buffers.should_capture(kind, fps):
                continue

            try:
                data_url = await self._encode_frame(frame, kind)
                self.buffers.add_frame(kind, data_url)
            except Exception as e:
                logger.error(f"❌ {kind} encode failed: {e}")

    async def _encode_frame(self, frame: rtc.VideoFrame, kind: str) -> str:
        """Encode a video frame to data URL."""
        if kind == "camera":
            return await encode(
                frame,
                EncodeOptions(format="JPEG", quality=self.config.camera_quality),
                ResizeOptions(width=self.config.camera_max_dim, height=self.config.camera_max_dim),
            )
        else:
            return await encode(
                frame,
                EncodeOptions(format=self.config.screen_format, quality=self.config.screen_quality),
                ResizeOptions(width=self.config.screen_max_w, height=self.config.screen_max_h),
            )

    async def on_user_turn_completed(self, turn_ctx: ChatContext, new_message: dict) -> None:
        """
        Process user turn with automatic mode detection.
        Attaches frames only when video is available.
        """
        has_video = self._update_mode()

        if has_video:
            frames = self.buffers.select_frames()
            if frames:
                self._attach_frames(new_message, frames)
                logger.info(f"🎥 Vision: {len(frames)} frame(s)")
        else:
            logger.info("🎤 Voice-only")

        self.buffers.clear()

    def _update_mode(self) -> bool:
        """Update current mode based on video availability."""
        has_video = self.buffers.has_frames()
        new_mode = "vision" if has_video else "voice-only"

        if new_mode != self._current_mode:
            logger.info(f"🔄 {self._current_mode} → {new_mode}")
            self._current_mode = new_mode

        return has_video

    def _attach_frames(self, message: dict, frames: List[Tuple[float, str, str]]):
        """Attach frames to message content."""
        if not isinstance(message.content, list):
            message.content = [message.content]

        for _, _, data_url in frames:
            message.content.append(ImageContent(image=data_url))


# ============================================================================
# ENTRYPOINT
# ============================================================================


async def entrypoint(ctx: JobContext):
    """Main entry point for unified agent."""
    ctx.log_context_fields = {"room": ctx.room.name}

    logger.info("🚀 UNIFIED AGENT - Auto-switching voice/vision")

    session = AgentSession(
        stt=openai.STT(model="whisper-1"),
        llm=openai.LLM(model="gpt-4o"),
        tts=openai.TTS(voice="alloy"),
        vad=silero.VAD.load(),
    )

    await session.start(
        room=ctx.room,
        agent=UnifiedAssistant(),
        room_input_options=RoomInputOptions(
            noise_cancellation=(NoiseBVC() if NoiseBVC is not None else None),
            video_enabled=True,
        ),
    )

    await session.generate_reply(
        instructions="Greet the user as an Asian parent math tutor. Tell them you're ready to help. They can share their camera or screen to show math problems. Keep it brief and in character."
    )


if __name__ == "__main__":
    agents.cli.run_app(agents.WorkerOptions(entrypoint_fnc=entrypoint))
