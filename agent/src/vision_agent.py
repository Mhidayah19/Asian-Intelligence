import asyncio
import base64
import logging
import os
import time
from collections import deque
from typing import List, Optional, Tuple

from dotenv import load_dotenv
from livekit import agents, rtc
from livekit.agents import Agent, AgentSession, ChatContext, JobContext, RoomInputOptions, get_job_context
from livekit.agents.llm import ImageContent
from livekit.agents.utils.images import EncodeOptions, ResizeOptions, encode
from livekit.plugins import openai, silero
try:
    # Prefer direct import; plugin may not always be installed
    from livekit.plugins.noise_cancellation import BVC as NoiseBVC
except Exception:
    NoiseBVC = None

logger = logging.getLogger("vision-agent")

load_dotenv(".env.local")


# ============================================================================
# CONFIGURATION - Environment Variables with Defaults
# ============================================================================

# Camera encoding settings (INCREASED FOR BETTER QUALITY)
CAMERA_MAX_DIM = int(os.getenv("CAMERA_MAX_DIM", "1024"))
CAMERA_JPEG_QUALITY = int(os.getenv("CAMERA_JPEG_QUALITY", "85"))  # Increased from 82

# Screen share encoding settings (BALANCED: Good quality, faster processing)
SCREEN_MAX_W = int(os.getenv("SCREEN_MAX_W", "1280"))  # Reduced from 1920 for faster processing
SCREEN_MAX_H = int(os.getenv("SCREEN_MAX_H", "720"))   # Reduced from 1080 for faster processing
SCREEN_FORMAT = os.getenv("SCREEN_FORMAT", "JPEG")     # JPEG for speed
SCREEN_JPEG_QUALITY = int(os.getenv("SCREEN_JPEG_QUALITY", "80"))  # Balanced quality/speed

# Adaptive sampling rates (frames per second)
FPS_SPEAKING = float(os.getenv("FPS_SPEAKING", "2.0"))  # Increased from 1.0 for better coverage
FPS_IDLE = float(os.getenv("FPS_IDLE", "0.0"))  # Changed to 0 - don't capture when idle

# Multi-frame bundling
VISION_MAX_FRAMES_PER_TURN = int(os.getenv("VISION_MAX_FRAMES_PER_TURN", "1"))  # Single frame for fastest processing
BUFFER_MAX_SIZE = 10  # Keep last N frames per stream

# Metrics logging interval (seconds)
METRICS_LOG_INTERVAL = 30.0


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def _should_capture(now: float, last_ts: Optional[float], fps: float) -> bool:
    """
    Determine if we should capture a frame based on sampling rate.
    
    Args:
        now: Current timestamp
        last_ts: Last capture timestamp (None if first capture)
        fps: Target frames per second
    
    Returns:
        True if enough time has passed to capture next frame
    """
    if fps <= 0:
        return False  # Don't capture if fps is 0
    if last_ts is None:
        return True
    return (now - last_ts) >= (1.0 / max(fps, 0.1))


def _pick_frames(buffer: deque, max_count: int) -> List[Tuple[float, str, str]]:
    """
    Select up to max_count frames from buffer using first/middle/last strategy.
    
    Args:
        buffer: deque of (timestamp, kind, data_url) tuples
        max_count: Maximum number of frames to select
    
    Returns:
        List of selected frame tuples
    """
    if not buffer:
        return []
    if len(buffer) == 1:
        return [buffer[0]]
    if len(buffer) == 2:
        return [buffer[0], buffer[-1]]
    
    # Pick first, middle, last
    selected = [
        buffer[0],
        buffer[len(buffer) // 2],
        buffer[-1]
    ]
    return selected[:max_count]


class VisionAssistant(Agent):
    """
    AI Assistant with vision capabilities for camera and screen-sharing.
    CRITICAL FIX: Only captures frames DURING user speech to ensure relevance.
    """

    def __init__(self) -> None:
        # Multi-frame buffers (circular, fixed size)
        self._buf = {
            "camera": deque(maxlen=BUFFER_MAX_SIZE),
            "screenshare": deque(maxlen=BUFFER_MAX_SIZE)
        }
        
        self._camera_stream = None
        self._screen_share_stream = None
        self._tasks = []  # Prevent garbage collection of running tasks
        
        # CRITICAL: Speech-triggered capture state
        self._is_capturing = False
        self._speech_started_ts: Optional[float] = None
        self._turn_in_progress = False
        
        # Sampling tracking
        self._last_capture_ts = {
            "camera": None,
            "screenshare": None
        }
        
        # Metrics tracking
        self._metrics = {
            "camera": {
                "attempted": 0,
                "skipped": 0,
                "encoded": 0,
                "encode_times": [],
                "payload_sizes": []
            },
            "screenshare": {
                "attempted": 0,
                "skipped": 0,
                "encoded": 0,
                "encode_times": [],
                "payload_sizes": []
            }
        }
        self._frames_per_turn_history = []
        self._frame_ages_history = []
        self._last_metrics_log_ts: Optional[float] = None
        self._current_fps_mode = "idle"  # "speaking" or "idle"
        
        super().__init__(
            instructions="""You are an enthusiastic AI math tutor in the style of an Asian tiger parent.
            
            CRITICAL VISION RULES:
            1. You can ONLY see images that are EXPLICITLY in the current message content as ImageContent objects.
            2. If NO image in message: Say "I cannot see anything. Turn on your camera or share your screen first."
            3. NEVER claim to see things without an image present.
            4. NEVER make assumptions, guesses, or hallucinate visual content.
            
            WHEN YOU SEE AN IMAGE:
            - ANALYZE CAREFULLY: Look at ALL details - read any text, numbers, equations, diagrams, handwriting
            - BE SPECIFIC: Describe exactly what you see - "I see equation x² + 5x + 6 = 0" not just "I see math"
            - READ TEXT: If there's written text, read it word-for-word. If there are math problems, state them precisely.
            - IDENTIFY CLEARLY: Note if it's handwritten homework, printed worksheet, digital document, whiteboard, etc.
            - THEN HELP: After identifying the specific problem, provide tutoring in Asian parent style
            
            Asian Parent Personality:
            - Use intensity: "Aiyo! Why you need help with this? So simple!"
            - Be demanding: "This quadratic equation? You should know factoring already!"
            - Show disappointment: "Only 85%? What happened to the other 15%?"
            - But still help: Explain step-by-step while maintaining the energy
            
            Keep responses conversational and concise but be PRECISE about what you see."""
        )

    def _start_capturing(self):
        """Start capturing frames - called when user begins speaking."""
        if not self._is_capturing:
            old_cam = len(self._buf["camera"])
            old_screen = len(self._buf["screenshare"])
            logger.info(
                f"🎤 User started speaking - CLEARING OLD FRAMES "
                f"(camera:{old_cam}, screenshare:{old_screen}), starting FRESH capture"
            )
            # CRITICAL: Clear old irrelevant frames from idle period
            self._buf["camera"].clear()
            self._buf["screenshare"].clear()
            self._is_capturing = True
            self._turn_in_progress = True
            self._speech_started_ts = time.time()

    def _stop_capturing(self):
        """Stop capturing frames - called when user stops speaking."""
        if self._is_capturing:
            capture_duration = time.time() - self._speech_started_ts if self._speech_started_ts else 0
            frame_count = len(self._buf["camera"]) + len(self._buf["screenshare"])
            logger.info(
                f"🛑 User stopped speaking - captured {frame_count} FRESH frames "
                f"over {capture_duration:.1f}s"
            )
            self._is_capturing = False

    def _current_fps(self) -> float:
        """
        Get current target FPS based on user speaking state.
        
        Returns:
            Target FPS (FPS_SPEAKING if speaking, FPS_IDLE if idle, 0.5 as fallback)
        """
        try:
            # Try to access session user_state
            if hasattr(self, 'session') and hasattr(self.session, 'user_state'):
                is_speaking = self.session.user_state == "speaking"
                new_mode = "speaking" if is_speaking else "idle"
                
                # Handle state transitions
                if new_mode == "speaking" and self._current_fps_mode != "speaking":
                    self._start_capturing()
                elif new_mode == "idle" and self._current_fps_mode == "speaking":
                    self._stop_capturing()
                
                # Log sampling state transitions
                if new_mode != self._current_fps_mode:
                    self._current_fps_mode = new_mode
                    fps = FPS_SPEAKING if is_speaking else FPS_IDLE
                    logger.info(f"🎯 Sampling mode: {new_mode} ({fps} fps)")
                
                return FPS_SPEAKING if is_speaking else FPS_IDLE
        except Exception as e:
            logger.debug(f"Could not access user_state: {e}")
        
        # Fallback to moderate sampling rate
        return 0.5

    def _log_metrics(self):
        """Log encoding and bundling metrics every METRICS_LOG_INTERVAL seconds."""
        now = time.time()
        
        if self._last_metrics_log_ts is None:
            self._last_metrics_log_ts = now
            return
        
        if (now - self._last_metrics_log_ts) < METRICS_LOG_INTERVAL:
            return
        
        self._last_metrics_log_ts = now
        
        # Camera metrics
        cam_metrics = self._metrics["camera"]
        if cam_metrics["encoded"] > 0:
            avg_encode_ms = (sum(cam_metrics["encode_times"]) / len(cam_metrics["encode_times"])) * 1000
            avg_payload_kb = sum(cam_metrics["payload_sizes"]) / len(cam_metrics["payload_sizes"]) / 1024
            skip_rate = cam_metrics["skipped"] / max(cam_metrics["attempted"], 1) * 100
            logger.info(
                f"📊 Camera ({METRICS_LOG_INTERVAL}s): "
                f"encoded={cam_metrics['encoded']}, skipped={cam_metrics['skipped']} ({skip_rate:.0f}%), "
                f"avg encode={avg_encode_ms:.1f}ms, avg size={avg_payload_kb:.1f}KB"
            )
            cam_metrics["encode_times"].clear()
            cam_metrics["payload_sizes"].clear()
            cam_metrics["attempted"] = 0
            cam_metrics["skipped"] = 0
            cam_metrics["encoded"] = 0
        
        # Screen share metrics
        screen_metrics = self._metrics["screenshare"]
        if screen_metrics["encoded"] > 0:
            avg_encode_ms = (sum(screen_metrics["encode_times"]) / len(screen_metrics["encode_times"])) * 1000
            avg_payload_kb = sum(screen_metrics["payload_sizes"]) / len(screen_metrics["payload_sizes"]) / 1024
            skip_rate = screen_metrics["skipped"] / max(screen_metrics["attempted"], 1) * 100
            logger.info(
                f"📊 Screen share ({METRICS_LOG_INTERVAL}s): "
                f"encoded={screen_metrics['encoded']}, skipped={screen_metrics['skipped']} ({skip_rate:.0f}%), "
                f"avg encode={avg_encode_ms:.1f}ms, avg size={avg_payload_kb:.1f}KB"
            )
            screen_metrics["encode_times"].clear()
            screen_metrics["payload_sizes"].clear()
            screen_metrics["attempted"] = 0
            screen_metrics["skipped"] = 0
            screen_metrics["encoded"] = 0
        
        # Multi-frame bundling stats
        if self._frames_per_turn_history:
            avg_frames = sum(self._frames_per_turn_history) / len(self._frames_per_turn_history)
            logger.info(
                f"📊 Multi-frame bundling: avg {avg_frames:.1f} frames/turn "
                f"(last {len(self._frames_per_turn_history)} turns)"
            )
            self._frames_per_turn_history.clear()
        
        # Frame age tracking
        if self._frame_ages_history:
            avg_age = sum(self._frame_ages_history) / len(self._frame_ages_history)
            max_age = max(self._frame_ages_history)
            logger.info(
                f"📊 Frame freshness: avg age={avg_age:.1f}s, max age={max_age:.1f}s "
                f"(last {len(self._frame_ages_history)} turns)"
            )
            self._frame_ages_history.clear()

    async def on_enter(self):
        """Set up video track subscriptions when agent enters the room."""
        room = get_job_context().room

        # Look for existing video tracks from remote participants
        for participant in room.remote_participants.values():
            self._subscribe_to_participant_video(participant)

        # Watch for new video tracks
        @room.on("track_subscribed")
        def on_track_subscribed(
            track: rtc.Track,
            publication: rtc.RemoteTrackPublication,
            participant: rtc.RemoteParticipant,
        ):
            if track.kind == rtc.TrackKind.KIND_VIDEO:
                self._subscribe_to_video_track(track, publication, participant)

    def _subscribe_to_participant_video(self, participant: rtc.RemoteParticipant):
        """Subscribe to all video tracks from a participant."""
        for publication in participant.track_publications.values():
            if (
                publication.track
                and publication.track.kind == rtc.TrackKind.KIND_VIDEO
            ):
                self._subscribe_to_video_track(publication.track, publication, participant)

    def _subscribe_to_video_track(
        self, track: rtc.Track, publication: rtc.RemoteTrackPublication, participant: rtc.RemoteParticipant
    ):
        """Subscribe to a specific video track (camera or screen share)."""
        source = getattr(publication, "source", None)
        try:
            src_name = str(source)
        except Exception:
            src_name = "unknown"
        logger.info(f"📹 Video track detected from {participant.identity} - publication.source={src_name}")

        # Determine if this is camera or screen share based on publication source
        # Note: SDK uses SOURCE_SCREENSHARE (no underscore) not SOURCE_SCREEN_SHARE
        if source == rtc.TrackSource.SOURCE_CAMERA:
            logger.info("📷 Setting up CAMERA stream (speech-triggered capture)")
            self._create_camera_stream(track)
        elif source == rtc.TrackSource.SOURCE_SCREENSHARE or source == 3:
            logger.info("🖥️  Setting up SCREEN SHARE stream (speech-triggered capture)")
            self._create_screen_share_stream(track)
        else:
            # Fallback: if we cannot determine, default to camera for safety
            logger.warning(f"⚠️ Unknown video track source on publication: {source}; defaulting to CAMERA")
            self._create_camera_stream(track)

    def _create_camera_stream(self, track: rtc.Track):
        """Create video stream for camera feed."""
        if self._camera_stream is not None:
            self._camera_stream.close()

        self._camera_stream = rtc.VideoStream(track)
        task = asyncio.create_task(self._read_camera_stream())
        self._tasks.append(task)
        task.add_done_callback(lambda t: self._tasks.remove(t) if t in self._tasks else None)

    def _create_screen_share_stream(self, track: rtc.Track):
        """Create video stream for screen share feed."""
        if self._screen_share_stream is not None:
            self._screen_share_stream.close()

        self._screen_share_stream = rtc.VideoStream(track)
        task = asyncio.create_task(self._read_screen_share_stream())
        self._tasks.append(task)
        task.add_done_callback(lambda t: self._tasks.remove(t) if t in self._tasks else None)

    async def _read_camera_stream(self):
        """Read frames from camera stream with speech-triggered capture."""
        if self._camera_stream is None:
            return

        logger.info(
            f"📷 Camera stream active - SPEECH-TRIGGERED capture "
            f"({FPS_SPEAKING} fps speaking, {FPS_IDLE} fps idle)"
        )
        
        frame_count = 0
        async for event in self._camera_stream:
            # Ensure we evaluate speaking state to trigger start/stop capture
            _ = self._current_fps()
            self._metrics["camera"]["attempted"] += 1
            
            # CRITICAL FIX: Only capture during speech
            if not self._is_capturing:
                self._metrics["camera"]["skipped"] += 1
                continue  # Skip - user not speaking
            
            # Check adaptive sampling rate
            fps = self._current_fps()
            now = asyncio.get_event_loop().time()
            
            if not _should_capture(now, self._last_capture_ts["camera"], fps):
                self._metrics["camera"]["skipped"] += 1
                continue  # Skip this frame
            
            # Capture and encode frame
            encode_start = time.time()
            image_bytes = encode(
                event.frame,
                EncodeOptions(
                    format="JPEG",
                    quality=CAMERA_JPEG_QUALITY,
                    resize_options=ResizeOptions(
                        width=CAMERA_MAX_DIM,
                        height=CAMERA_MAX_DIM,
                        strategy="scale_aspect_fit"
                    ),
                ),
            )
            encode_time = time.time() - encode_start
            
            data_url = f"data:image/jpeg;base64,{base64.b64encode(image_bytes).decode('utf-8')}"
            
            # Append to buffer (timestamp, kind, data_url)
            self._buf["camera"].append((now, "camera", data_url))
            self._last_capture_ts["camera"] = now
            
            # Track metrics
            self._metrics["camera"]["encoded"] += 1
            self._metrics["camera"]["encode_times"].append(encode_time)
            self._metrics["camera"]["payload_sizes"].append(len(image_bytes))
            
            frame_count += 1
            if frame_count == 1:
                logger.info(
                    f"📷 First camera frame captured during speech "
                    f"({CAMERA_MAX_DIM}px, quality:{CAMERA_JPEG_QUALITY}, "
                    f"{len(image_bytes)/1024:.1f}KB, {encode_time*1000:.1f}ms)"
                )
            
            # Log metrics periodically
            self._log_metrics()

    async def _read_screen_share_stream(self):
        """Read frames from screen share stream with speech-triggered capture."""
        if self._screen_share_stream is None:
            return

        logger.info(
            f"🖥️  Screen share stream active - SPEECH-TRIGGERED capture "
            f"({FPS_SPEAKING} fps speaking, {FPS_IDLE} fps idle)"
        )
        
        frame_count = 0
        async for event in self._screen_share_stream:
            # Ensure we evaluate speaking state to trigger start/stop capture
            _ = self._current_fps()
            self._metrics["screenshare"]["attempted"] += 1
            
            # CRITICAL FIX: Only capture during speech
            if not self._is_capturing:
                self._metrics["screenshare"]["skipped"] += 1
                continue  # Skip - user not speaking
            
            # Check adaptive sampling rate
            fps = self._current_fps()
            now = asyncio.get_event_loop().time()
            
            if not _should_capture(now, self._last_capture_ts["screenshare"], fps):
                self._metrics["screenshare"]["skipped"] += 1
                continue  # Skip this frame
            
            # Capture and encode frame
            encode_start = time.time()
            
            if SCREEN_FORMAT == "PNG":
                image_bytes = encode(
                    event.frame,
                    EncodeOptions(
                        format="PNG",
                        resize_options=ResizeOptions(
                            width=SCREEN_MAX_W,
                            height=SCREEN_MAX_H,
                            strategy="scale_aspect_fit"
                        ),
                    ),
                )
                mime_type = "image/png"
            else:  # JPEG
                image_bytes = encode(
                    event.frame,
                    EncodeOptions(
                        format="JPEG",
                        quality=SCREEN_JPEG_QUALITY,
                        resize_options=ResizeOptions(
                            width=SCREEN_MAX_W,
                            height=SCREEN_MAX_H,
                            strategy="scale_aspect_fit"
                        ),
                    ),
                )
                mime_type = "image/jpeg"
            
            encode_time = time.time() - encode_start
            
            data_url = f"data:{mime_type};base64,{base64.b64encode(image_bytes).decode('utf-8')}"
            
            # Append to buffer (timestamp, kind, data_url)
            self._buf["screenshare"].append((now, "screenshare", data_url))
            self._last_capture_ts["screenshare"] = now
            
            # DIAGNOSTIC: Log screen share capture details
            logger.info(
                f"🖼️  SCREEN SHARE frame buffered: "
                f"format={SCREEN_FORMAT}, size={len(image_bytes)}B ({len(image_bytes)/1024:.1f}KB), "
                f"data_url_length={len(data_url)}, "
                f"buffer_size={len(self._buf['screenshare'])}"
            )
            
            # Track metrics
            self._metrics["screenshare"]["encoded"] += 1
            self._metrics["screenshare"]["encode_times"].append(encode_time)
            self._metrics["screenshare"]["payload_sizes"].append(len(image_bytes))
            
            frame_count += 1
            if frame_count == 1:
                logger.info(
                    f"🖥️  First screen share frame captured during speech "
                    f"({SCREEN_MAX_W}×{SCREEN_MAX_H}, {SCREEN_FORMAT}, "
                    f"{len(image_bytes)/1024:.1f}KB, {encode_time*1000:.1f}ms)"
                )
            
            # DIAGNOSTIC: Log every 5th frame to track capture rate
            if frame_count % 5 == 0:
                logger.info(f"🖥️  Screen share: captured {frame_count} frames so far")
            
            # Log metrics periodically
            self._log_metrics()

    async def on_user_turn_completed(self, turn_ctx: ChatContext, new_message: dict) -> None:
        """
        Add up to VISION_MAX_FRAMES_PER_TURN images to user message.
        Only sends FRESH frames captured during this speech turn.
        """
        # Stop capturing for this turn
        if self._is_capturing:
            self._stop_capturing()
        
        # DIAGNOSTIC: Log buffer state before selection
        logger.info(
            f"🔍 BUFFER STATE: camera={len(self._buf['camera'])} frames, "
            f"screenshare={len(self._buf['screenshare'])} frames"
        )
        
        frames = []
        
        # Prefer screen share frames (more informative for math tutoring)
        screen_frames = _pick_frames(self._buf["screenshare"], VISION_MAX_FRAMES_PER_TURN)
        frames.extend(screen_frames)
        
        logger.info(f"🎬 SELECTED {len(screen_frames)} screen share frames for LLM")
        
        # Fill remaining slots with camera frames
        if len(frames) < VISION_MAX_FRAMES_PER_TURN:
            remaining = VISION_MAX_FRAMES_PER_TURN - len(frames)
            camera_frames = _pick_frames(self._buf["camera"], remaining)
            frames.extend(camera_frames)
            logger.info(f"🎬 SELECTED {len(camera_frames)} camera frames for LLM")
        
        # Attach frames to message and track freshness
        if frames:
            if not isinstance(new_message.content, list):
                new_message.content = [new_message.content]
            
            now = time.time()
            oldest_age = max(now - f[0] for f in frames)
            newest_age = min(now - f[0] for f in frames)
            
            # DIAGNOSTIC: Log each frame being attached
            for idx, (timestamp, kind, data_url) in enumerate(frames):
                age = now - timestamp
                data_preview = data_url[:80] + "..." if len(data_url) > 80 else data_url
                size_kb = len(data_url) / 1024
                logger.info(
                    f"📤 FRAME {idx+1}/{len(frames)}: kind={kind}, age={age:.2f}s, "
                    f"size={size_kb:.1f}KB, preview={data_preview}"
                )
                new_message.content.append(ImageContent(image=data_url))
            
            # DIAGNOSTIC: Log final message structure
            logger.info(
                f"📨 MESSAGE TO LLM: "
                f"text_parts={sum(1 for c in new_message.content if isinstance(c, str))}, "
                f"image_parts={sum(1 for c in new_message.content if isinstance(c, ImageContent))}, "
                f"total_content_items={len(new_message.content)}"
            )
            
            logger.info(
                f"✅ {len(frames)} FRESH frame(s) attached "
                f"(screen:{len(screen_frames)}, camera:{len(frames)-len(screen_frames)}) "
                f"- age: {newest_age:.1f}s to {oldest_age:.1f}s old"
            )
            
            # Track metrics
            self._frames_per_turn_history.append(len(frames))
            self._frame_ages_history.append(oldest_age)
        else:
            logger.warning("⚠️  NO FRAMES TO SEND - buffer was empty!")
            logger.info("ℹ️  No video frames available (vision disabled or not capturing)")
        
        # Clear buffers for next turn (ensures fresh start)
        self._buf["camera"].clear()
        self._buf["screenshare"].clear()
        self._turn_in_progress = False


async def entrypoint(ctx: JobContext):
    """Main entry point for the vision-enabled agent."""
    ctx.log_context_fields = {"room": ctx.room.name}

    # Vision assistant using OpenAI for everything (STT, LLM, TTS)
    session = AgentSession(
        stt=openai.STT(model="whisper-1"),  # OpenAI Whisper for speech-to-text
        llm=openai.LLM(model="gpt-4o"),  # GPT-4o with vision capabilities
        tts=openai.TTS(voice="alloy"),  # OpenAI TTS (voices: alloy, echo, fable, onyx, nova, shimmer)
        vad=silero.VAD.load(),
    )

    await session.start(
        room=ctx.room,
        agent=VisionAssistant(),
        room_input_options=RoomInputOptions(
            noise_cancellation=(NoiseBVC() if NoiseBVC is not None else None),
            video_enabled=True,  # Enable video input from users
        ),
    )

    await session.generate_reply(
        instructions="Greet the user as an Asian parent math tutor. Tell them you're ready to help, and they can turn on your camera or share your screen if you want to show math problems or homework. Keep it brief and in character. Do NOT claim you can already see them."
    )


if __name__ == "__main__":
    agents.cli.run_app(agents.WorkerOptions(entrypoint_fnc=entrypoint))
