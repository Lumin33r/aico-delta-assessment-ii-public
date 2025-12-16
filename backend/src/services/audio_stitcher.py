"""
Audio Stitcher

Handles audio segment concatenation and processing for podcast episodes.

Features:
- Concatenates multiple audio segments with crossfades
- Adds silence/pauses between speakers
- Normalizes audio levels
- Supports MP3 and WAV formats
- Fallback to simple concatenation if pydub unavailable
"""

import io
import os
import logging
import tempfile
from typing import List, Dict, Optional, Tuple, BinaryIO
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

# Try to import pydub for advanced audio processing
try:
    from pydub import AudioSegment
    from pydub.effects import normalize
    PYDUB_AVAILABLE = True
except ImportError:
    PYDUB_AVAILABLE = False
    logger.warning("pydub not available - using simple concatenation")


@dataclass
class AudioChunk:
    """
    Represents a single audio chunk for processing.
    """
    audio_bytes: bytes
    speaker: str
    voice_id: str
    duration_ms: int
    segment_index: int
    text: str = ""
    format: str = "mp3"


@dataclass
class StitchConfig:
    """
    Configuration for audio stitching.
    """
    # Pause durations (ms)
    pause_between_speakers: int = 600
    pause_same_speaker: int = 250
    pause_segment_transition: int = 800

    # Audio processing
    crossfade_ms: int = 50  # Smooth transitions
    normalize_audio: bool = True
    target_dbfs: float = -16.0  # Target loudness

    # Output settings
    output_format: str = "mp3"
    output_bitrate: str = "192k"
    sample_rate: int = 24000
    channels: int = 1  # Mono for speech


class AudioStitcher:
    """
    Stitches multiple audio segments into a complete podcast episode.
    """

    def __init__(self, config: Optional[StitchConfig] = None):
        """
        Initialize the audio stitcher.

        Args:
            config: Stitching configuration options
        """
        self.config = config or StitchConfig()
        self._pydub_available = PYDUB_AVAILABLE

    def stitch(
        self,
        chunks: List[AudioChunk],
        include_segment_pauses: bool = True
    ) -> Tuple[bytes, int]:
        """
        Stitch audio chunks into a single audio file.

        Args:
            chunks: List of AudioChunk objects to combine
            include_segment_pauses: Whether to add pauses between segments

        Returns:
            Tuple of (combined_audio_bytes, total_duration_ms)
        """
        if not chunks:
            return b'', 0

        if self._pydub_available:
            return self._stitch_with_pydub(chunks, include_segment_pauses)
        else:
            return self._stitch_simple(chunks)

    def _stitch_with_pydub(
        self,
        chunks: List[AudioChunk],
        include_segment_pauses: bool
    ) -> Tuple[bytes, int]:
        """
        Stitch audio using pydub for professional-quality output.

        Args:
            chunks: Audio chunks to combine
            include_segment_pauses: Add pauses between segments

        Returns:
            Tuple of (combined_bytes, duration_ms)
        """
        combined = AudioSegment.empty()
        last_speaker = None
        last_segment_idx = -1

        for chunk in chunks:
            try:
                # Load audio chunk
                audio = AudioSegment.from_mp3(io.BytesIO(chunk.audio_bytes))

                # Add pause based on context
                if combined.duration_seconds > 0:
                    pause_ms = self._calculate_pause(
                        current_speaker=chunk.speaker,
                        last_speaker=last_speaker,
                        segment_changed=(chunk.segment_index != last_segment_idx),
                        include_segment_pauses=include_segment_pauses
                    )

                    if pause_ms > 0:
                        silence = AudioSegment.silent(duration=pause_ms)
                        combined += silence

                # Add crossfade for smooth transition
                if combined.duration_seconds > 0 and self.config.crossfade_ms > 0:
                    combined = combined.append(audio, crossfade=self.config.crossfade_ms)
                else:
                    combined += audio

                last_speaker = chunk.speaker
                last_segment_idx = chunk.segment_index

            except Exception as e:
                logger.error(f"Failed to process chunk: {e}")
                # Try simple append on error
                try:
                    audio = AudioSegment.from_mp3(io.BytesIO(chunk.audio_bytes))
                    combined += audio
                except Exception:
                    continue

        # Normalize audio levels
        if self.config.normalize_audio and len(combined) > 0:
            combined = normalize(combined)
            # Adjust to target loudness
            change_in_dbfs = self.config.target_dbfs - combined.dBFS
            combined = combined.apply_gain(change_in_dbfs)

        # Export to bytes
        output_buffer = io.BytesIO()
        combined.export(
            output_buffer,
            format=self.config.output_format,
            bitrate=self.config.output_bitrate,
            parameters=["-ar", str(self.config.sample_rate), "-ac", str(self.config.channels)]
        )

        return output_buffer.getvalue(), int(combined.duration_seconds * 1000)

    def _stitch_simple(self, chunks: List[AudioChunk]) -> Tuple[bytes, int]:
        """
        Simple concatenation fallback when pydub is unavailable.

        Note: This may cause minor audio glitches at boundaries.

        Args:
            chunks: Audio chunks to combine

        Returns:
            Tuple of (combined_bytes, duration_ms)
        """
        combined = b''.join(chunk.audio_bytes for chunk in chunks if chunk.audio_bytes)
        total_duration = sum(chunk.duration_ms for chunk in chunks)

        return combined, total_duration

    def _calculate_pause(
        self,
        current_speaker: str,
        last_speaker: Optional[str],
        segment_changed: bool,
        include_segment_pauses: bool
    ) -> int:
        """
        Calculate appropriate pause duration based on context.

        Args:
            current_speaker: Current speaker ID
            last_speaker: Previous speaker ID
            segment_changed: Whether we're in a new segment
            include_segment_pauses: Include longer segment pauses

        Returns:
            Pause duration in milliseconds
        """
        if segment_changed and include_segment_pauses:
            return self.config.pause_segment_transition
        elif current_speaker != last_speaker:
            return self.config.pause_between_speakers
        else:
            return self.config.pause_same_speaker

    def add_intro_music(
        self,
        audio: bytes,
        music_bytes: bytes,
        fade_duration_ms: int = 2000
    ) -> bytes:
        """
        Add intro music with fade under speech.

        Args:
            audio: Main audio content
            music_bytes: Intro music audio
            fade_duration_ms: Duration of music fade

        Returns:
            Combined audio with intro music
        """
        if not self._pydub_available:
            return audio

        try:
            main_audio = AudioSegment.from_mp3(io.BytesIO(audio))
            music = AudioSegment.from_mp3(io.BytesIO(music_bytes))

            # Fade out music
            music = music.fade_out(fade_duration_ms)

            # Lower music volume
            music = music - 12  # -12dB

            # Overlay music under speech start
            if len(music) > len(main_audio):
                music = music[:len(main_audio)]

            combined = main_audio.overlay(music, position=0)

            output = io.BytesIO()
            combined.export(output, format="mp3")
            return output.getvalue()

        except Exception as e:
            logger.error(f"Failed to add intro music: {e}")
            return audio

    def add_outro_music(
        self,
        audio: bytes,
        music_bytes: bytes,
        fade_duration_ms: int = 3000
    ) -> bytes:
        """
        Add outro music with fade in.

        Args:
            audio: Main audio content
            music_bytes: Outro music audio
            fade_duration_ms: Duration of music fade

        Returns:
            Combined audio with outro music
        """
        if not self._pydub_available:
            return audio

        try:
            main_audio = AudioSegment.from_mp3(io.BytesIO(audio))
            music = AudioSegment.from_mp3(io.BytesIO(music_bytes))

            # Fade in music
            music = music.fade_in(fade_duration_ms)

            # Lower music volume
            music = music - 10  # -10dB

            # Position music at end
            outro_start = max(0, len(main_audio) - len(music))

            combined = main_audio.overlay(music, position=outro_start)

            output = io.BytesIO()
            combined.export(output, format="mp3")
            return output.getvalue()

        except Exception as e:
            logger.error(f"Failed to add outro music: {e}")
            return audio

    def get_audio_info(self, audio_bytes: bytes) -> Dict:
        """
        Get information about an audio file.

        Args:
            audio_bytes: Audio data

        Returns:
            Dict with duration, format info, etc.
        """
        if not self._pydub_available:
            return {
                'duration_ms': len(audio_bytes) // 3,  # Rough estimate
                'format': 'unknown',
                'pydub_available': False
            }

        try:
            audio = AudioSegment.from_mp3(io.BytesIO(audio_bytes))
            return {
                'duration_ms': len(audio),
                'duration_seconds': audio.duration_seconds,
                'channels': audio.channels,
                'sample_width': audio.sample_width,
                'frame_rate': audio.frame_rate,
                'dbfs': audio.dBFS,
                'pydub_available': True
            }
        except Exception as e:
            logger.error(f"Failed to get audio info: {e}")
            return {'error': str(e), 'pydub_available': True}

    def split_audio(
        self,
        audio_bytes: bytes,
        timestamps: List[int]
    ) -> List[bytes]:
        """
        Split audio at specified timestamps.

        Args:
            audio_bytes: Audio to split
            timestamps: List of timestamps in ms to split at

        Returns:
            List of audio segment bytes
        """
        if not self._pydub_available:
            return [audio_bytes]

        try:
            audio = AudioSegment.from_mp3(io.BytesIO(audio_bytes))
            segments = []

            start = 0
            for timestamp in sorted(timestamps):
                if timestamp > start and timestamp < len(audio):
                    segment = audio[start:timestamp]
                    output = io.BytesIO()
                    segment.export(output, format="mp3")
                    segments.append(output.getvalue())
                    start = timestamp

            # Add final segment
            if start < len(audio):
                segment = audio[start:]
                output = io.BytesIO()
                segment.export(output, format="mp3")
                segments.append(output.getvalue())

            return segments

        except Exception as e:
            logger.error(f"Failed to split audio: {e}")
            return [audio_bytes]


# =============================================================================
# Utility Functions
# =============================================================================

def create_silence(duration_ms: int, format: str = "mp3") -> bytes:
    """
    Create silent audio of specified duration.

    Args:
        duration_ms: Duration in milliseconds
        format: Output format

    Returns:
        Silent audio bytes
    """
    if not PYDUB_AVAILABLE:
        return b''

    try:
        silence = AudioSegment.silent(duration=duration_ms)
        output = io.BytesIO()
        silence.export(output, format=format)
        return output.getvalue()
    except Exception:
        return b''


def calculate_duration(audio_bytes: bytes) -> int:
    """
    Calculate duration of audio in milliseconds.

    Args:
        audio_bytes: Audio data

    Returns:
        Duration in milliseconds
    """
    if not PYDUB_AVAILABLE:
        # Rough estimate: MP3 at ~24kbps is about 3KB per second
        return len(audio_bytes) // 3

    try:
        audio = AudioSegment.from_mp3(io.BytesIO(audio_bytes))
        return len(audio)
    except Exception:
        return len(audio_bytes) // 3


# =============================================================================
# Demo/Testing
# =============================================================================

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    print("Audio Stitcher Configuration")
    print("=" * 40)
    print(f"pydub available: {PYDUB_AVAILABLE}")

    stitcher = AudioStitcher()
    config = stitcher.config

    print(f"\nDefault Configuration:")
    print(f"  Pause between speakers: {config.pause_between_speakers}ms")
    print(f"  Pause same speaker: {config.pause_same_speaker}ms")
    print(f"  Segment transition: {config.pause_segment_transition}ms")
    print(f"  Crossfade: {config.crossfade_ms}ms")
    print(f"  Normalize: {config.normalize_audio}")
    print(f"  Target dBFS: {config.target_dbfs}")

    if PYDUB_AVAILABLE:
        print("\n✓ Advanced audio processing available")

        # Test silence generation
        silence = create_silence(1000)
        print(f"✓ Generated 1s silence: {len(silence)} bytes")
    else:
        print("\n✗ Install pydub for advanced audio processing:")
        print("  pip install pydub")
        print("  (Also requires ffmpeg)")
