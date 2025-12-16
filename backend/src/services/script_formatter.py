"""
Script Formatter

Formats podcast scripts for audio synthesis with SSML markup,
timing controls, and multi-voice coordination.

Features:
- SSML generation for Amazon Polly
- Emphasis and prosody markers
- Pause insertion
- Voice switching
- Transcript generation
"""

import re
import logging
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass

from .dialogue_models import (
    DialogueTurn, EpisodeScript, EpisodeSegment,
    Speaker, SegmentType, EmotionHint
)

logger = logging.getLogger(__name__)


@dataclass
class SSMLConfig:
    """Configuration for SSML generation."""
    # Pause durations (ms)
    sentence_pause: int = 400
    paragraph_pause: int = 800
    speaker_switch_pause: int = 600
    emphasis_pause: int = 200

    # Prosody settings
    default_rate: str = "medium"  # x-slow, slow, medium, fast, x-fast
    alex_rate: str = "medium"
    sam_rate: str = "medium"

    # Volume
    default_volume: str = "medium"  # silent, x-soft, soft, medium, loud, x-loud

    # Pitch adjustments for emotions
    emotion_pitch: Dict[str, str] = None

    def __post_init__(self):
        if self.emotion_pitch is None:
            self.emotion_pitch = {
                'neutral': 'medium',
                'excited': '+10%',
                'curious': '+5%',
                'thoughtful': '-5%',
                'enthusiastic': '+15%',
                'surprised': '+20%',
                'encouraging': '+5%',
                'contemplative': '-10%'
            }


class ScriptFormatter:
    """
    Formats podcast scripts for synthesis.
    """

    # Words that should typically be emphasized (with capture groups)
    EMPHASIS_PATTERNS = [
        r'\b(key|important|crucial|essential|main|primary)\b',
        r'\b(always|never|must|should)\b',
        r'\b(first|second|third|finally)\b',
        r'\b(exactly)\b',
        r'\b(remember|note|notice)\b',
    ]

    # Patterns for adding pauses
    PAUSE_AFTER_PATTERNS = [
        (r'[.!?]', 'sentence'),
        (r'[,;:]', 'clause'),
        (r'\.\.\.', 'ellipsis'),
        (r'—', 'dash'),
    ]

    def __init__(self, config: Optional[SSMLConfig] = None):
        """
        Initialize the formatter.

        Args:
            config: SSML configuration options
        """
        self.config = config or SSMLConfig()

    def format_script(
        self,
        script: EpisodeScript,
        output_format: str = "ssml"
    ) -> List[Dict]:
        """
        Format entire script for synthesis.

        Args:
            script: EpisodeScript to format
            output_format: "ssml" or "plain"

        Returns:
            List of formatted segments with voice assignments
        """
        formatted_segments = []

        for i, segment in enumerate(script.segments):
            for j, turn in enumerate(segment.turns):
                # Add speaker switch pause if needed
                pause_before = self.config.speaker_switch_pause
                if j == 0 and i > 0:
                    pause_before = self.config.paragraph_pause

                if output_format == "ssml":
                    text = self._format_turn_ssml(turn, pause_before)
                else:
                    text = turn.text

                formatted_segments.append({
                    'speaker': turn.speaker.value,
                    'voice_id': turn.speaker.voice_id,
                    'text': text,
                    'segment_type': segment.segment_type.value,
                    'emotion': turn.emotion.value,
                    'word_count': turn.word_count,
                    'original_text': turn.text
                })

        return formatted_segments

    def _format_turn_ssml(
        self,
        turn: DialogueTurn,
        pause_before_ms: int = 0
    ) -> str:
        """
        Format a single turn with SSML.

        Args:
            turn: DialogueTurn to format
            pause_before_ms: Pause before this turn

        Returns:
            SSML-formatted text
        """
        text = turn.text

        # Apply emphasis
        text = self._add_emphasis(text, turn.emphasis_words)

        # Apply prosody based on emotion
        pitch = self.config.emotion_pitch.get(turn.emotion.value, 'medium')
        rate = self.config.alex_rate if turn.speaker == Speaker.ALEX else self.config.sam_rate

        # Build SSML
        ssml_parts = ['<speak>']

        # Add leading pause
        if pause_before_ms > 0:
            ssml_parts.append(f'<break time="{pause_before_ms}ms"/>')

        # Apply prosody
        ssml_parts.append(f'<prosody rate="{rate}" pitch="{pitch}">')

        # Add the text with internal pauses
        text = self._add_natural_pauses(text)
        ssml_parts.append(text)

        ssml_parts.append('</prosody>')
        ssml_parts.append('</speak>')

        return ''.join(ssml_parts)

    def _add_emphasis(self, text: str, emphasis_words: List[str]) -> str:
        """
        Add SSML emphasis to specific words.

        Args:
            text: Original text
            emphasis_words: Words to emphasize

        Returns:
            Text with emphasis tags
        """
        # Emphasize specified words
        for word in emphasis_words:
            pattern = rf'\b({re.escape(word)})\b'
            text = re.sub(
                pattern,
                r'<emphasis level="moderate">\1</emphasis>',
                text,
                flags=re.IGNORECASE
            )

        # Auto-detect words that should be emphasized
        for pattern in self.EMPHASIS_PATTERNS:
            text = re.sub(
                pattern,
                r'<emphasis level="moderate">\1</emphasis>',
                text,
                flags=re.IGNORECASE
            )

        return text

    def _add_natural_pauses(self, text: str) -> str:
        """
        Add natural pauses at punctuation.

        Args:
            text: Text to process

        Returns:
            Text with pause markers
        """
        # Add pauses after sentences
        text = re.sub(
            r'([.!?])\s+',
            rf'\1<break time="{self.config.sentence_pause}ms"/> ',
            text
        )

        # Add shorter pauses after clauses
        text = re.sub(
            r'([,;:])\s+',
            rf'\1<break time="200ms"/> ',
            text
        )

        # Handle ellipsis
        text = re.sub(
            r'\.{3}',
            f'<break time="{self.config.paragraph_pause}ms"/>',
            text
        )

        return text

    def format_for_synthesis(
        self,
        script: EpisodeScript
    ) -> List[Dict]:
        """
        Format script for AWS Polly synthesis.

        Splits into chunks that respect Polly's limits and
        groups by speaker for efficient synthesis.

        Args:
            script: EpisodeScript to format

        Returns:
            List of synthesis-ready chunks
        """
        MAX_CHARS = 2900  # Polly limit is 3000, leave buffer

        formatted = self.format_script(script, output_format="ssml")
        synthesis_chunks = []

        current_speaker = None
        current_chunk = []
        current_length = 0

        for segment in formatted:
            text = segment['text']
            speaker = segment['speaker']
            voice_id = segment['voice_id']

            # Speaker change or chunk too long
            if speaker != current_speaker or current_length + len(text) > MAX_CHARS:
                # Save current chunk
                if current_chunk:
                    synthesis_chunks.append({
                        'voice_id': current_speaker_voice,
                        'speaker': current_speaker,
                        'ssml': self._combine_ssml_chunks(current_chunk),
                        'original_texts': [c['original_text'] for c in current_chunk]
                    })

                # Start new chunk
                current_speaker = speaker
                current_speaker_voice = voice_id
                current_chunk = [segment]
                current_length = len(text)
            else:
                current_chunk.append(segment)
                current_length += len(text)

        # Don't forget last chunk
        if current_chunk:
            synthesis_chunks.append({
                'voice_id': current_speaker_voice,
                'speaker': current_speaker,
                'ssml': self._combine_ssml_chunks(current_chunk),
                'original_texts': [c['original_text'] for c in current_chunk]
            })

        return synthesis_chunks

    def _combine_ssml_chunks(self, chunks: List[Dict]) -> str:
        """
        Combine multiple SSML chunks into one.

        Args:
            chunks: List of chunk dicts with 'text' key

        Returns:
            Combined SSML string
        """
        if not chunks:
            return ""

        # Extract content from each chunk (remove outer <speak> tags)
        contents = []
        for chunk in chunks:
            text = chunk['text']
            # Remove outer speak tags
            text = re.sub(r'^<speak>', '', text)
            text = re.sub(r'</speak>$', '', text)
            contents.append(text)

        # Combine with pauses
        combined = f'<break time="{self.config.speaker_switch_pause}ms"/>'.join(contents)

        return f'<speak>{combined}</speak>'

    def generate_transcript(
        self,
        script: EpisodeScript,
        format: str = "markdown"
    ) -> str:
        """
        Generate a human-readable transcript.

        Args:
            script: EpisodeScript to transcribe
            format: "markdown", "plain", or "srt"

        Returns:
            Formatted transcript string
        """
        if format == "markdown":
            return self._transcript_markdown(script)
        elif format == "srt":
            return self._transcript_srt(script)
        else:
            return self._transcript_plain(script)

    def _transcript_markdown(self, script: EpisodeScript) -> str:
        """Generate markdown transcript."""
        lines = [
            f"# {script.title}",
            f"",
            f"*Episode {script.lesson_number} of {script.total_lessons}*",
            f"",
            f"**Topics covered:** {', '.join(script.key_concepts)}",
            f"",
            f"---",
            f""
        ]

        for segment in script.segments:
            lines.append(f"## {segment.name}")
            lines.append("")

            for turn in segment.turns:
                speaker = turn.speaker.display_name
                lines.append(f"**{speaker}:** {turn.text}")
                lines.append("")

        # Add footer
        lines.append("---")
        lines.append(f"*Duration: ~{int(script.total_duration_seconds // 60)} minutes*")

        return "\n".join(lines)

    def _transcript_plain(self, script: EpisodeScript) -> str:
        """Generate plain text transcript."""
        lines = [
            script.title,
            "=" * len(script.title),
            f"Episode {script.lesson_number} of {script.total_lessons}",
            ""
        ]

        for segment in script.segments:
            lines.append(f"\n[{segment.name.upper()}]")
            for turn in segment.turns:
                lines.append(f"{turn.speaker.display_name}: {turn.text}")

        return "\n".join(lines)

    def _transcript_srt(self, script: EpisodeScript) -> str:
        """Generate SRT subtitle format."""
        lines = []
        counter = 1
        current_time = 0.0

        for segment in script.segments:
            for turn in segment.turns:
                duration = turn.estimated_duration_seconds
                start_time = self._format_srt_time(current_time)
                end_time = self._format_srt_time(current_time + duration)

                lines.append(str(counter))
                lines.append(f"{start_time} --> {end_time}")
                lines.append(f"[{turn.speaker.display_name}] {turn.text}")
                lines.append("")

                current_time += duration
                counter += 1

        return "\n".join(lines)

    def _format_srt_time(self, seconds: float) -> str:
        """Format seconds as SRT timestamp (HH:MM:SS,mmm)."""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        millis = int((seconds % 1) * 1000)

        return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"

    def extract_audio_segments(
        self,
        script: EpisodeScript
    ) -> List[Dict]:
        """
        Extract audio segment information for synthesis pipeline.

        Args:
            script: EpisodeScript

        Returns:
            List of segment info dicts
        """
        segments = []
        cumulative_time = 0.0

        for seg in script.segments:
            for turn in seg.turns:
                duration = turn.estimated_duration_seconds

                segments.append({
                    'speaker': turn.speaker.value,
                    'voice_id': turn.speaker.voice_id,
                    'text': turn.text,
                    'start_time': cumulative_time,
                    'duration': duration,
                    'segment_type': seg.segment_type.value,
                    'emotion': turn.emotion.value
                })

                cumulative_time += duration

        return segments


# =============================================================================
# Convenience Functions
# =============================================================================

def format_for_polly(script: EpisodeScript) -> List[Dict]:
    """
    Quick helper to format script for Polly synthesis.

    Args:
        script: EpisodeScript to format

    Returns:
        List of synthesis-ready chunks
    """
    formatter = ScriptFormatter()
    return formatter.format_for_synthesis(script)


def generate_transcript(
    script: EpisodeScript,
    format: str = "markdown"
) -> str:
    """
    Quick helper to generate transcript.

    Args:
        script: EpisodeScript
        format: Output format

    Returns:
        Transcript string
    """
    formatter = ScriptFormatter()
    return formatter.generate_transcript(script, format)


# =============================================================================
# Demo
# =============================================================================

if __name__ == "__main__":
    from dialogue_models import DialogueTurn, EpisodeSegment, EpisodeScript, Speaker, SegmentType, EmotionHint

    # Create sample script
    intro = EpisodeSegment(
        name="Introduction",
        segment_type=SegmentType.INTRO,
        turns=[
            DialogueTurn(
                speaker=Speaker.ALEX,
                text="Welcome to Tech Explained! I'm Alex, and today we're diving into Python decorators.",
                segment_type=SegmentType.INTRO,
                emotion=EmotionHint.ENTHUSIASTIC,
                emphasis_words=["decorators"]
            ),
            DialogueTurn(
                speaker=Speaker.SAM,
                text="Hey everyone! I've always found decorators confusing. They look like magic to me.",
                segment_type=SegmentType.INTRO,
                emotion=EmotionHint.CURIOUS
            )
        ]
    )

    script = EpisodeScript(
        title="Understanding Python Decorators",
        lesson_number=1,
        total_lessons=3,
        topic_description="Introduction to decorators",
        key_concepts=["decorators", "functions"],
        segments=[intro]
    )

    formatter = ScriptFormatter()

    # Format for synthesis
    synthesis_chunks = formatter.format_for_synthesis(script)
    print("Synthesis chunks:", len(synthesis_chunks))
    for chunk in synthesis_chunks:
        print(f"  {chunk['speaker']}: {chunk['ssml'][:100]}...")

    # Generate transcript
    print("\n--- Markdown Transcript ---")
    print(formatter.generate_transcript(script, "markdown"))
