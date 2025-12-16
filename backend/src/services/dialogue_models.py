"""
Dialogue Models

Data structures for podcast dialogue generation including
turns, segments, episodes, and complete scripts.

These models support:
- Structured dialogue with speaker metadata
- SSML formatting hints for audio synthesis
- Script validation and metrics
- Serialization for storage and API responses
"""

from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Literal
from enum import Enum
from datetime import datetime
import json


class Speaker(Enum):
    """Podcast host identifiers."""
    ALEX = "alex"
    SAM = "sam"

    @property
    def display_name(self) -> str:
        return self.value.capitalize()

    @property
    def voice_id(self) -> str:
        """AWS Polly voice ID for this speaker."""
        return "Matthew" if self == Speaker.ALEX else "Joanna"

    @property
    def role(self) -> str:
        return "Expert Host" if self == Speaker.ALEX else "Co-Host"


class SegmentType(Enum):
    """Types of dialogue segments in a podcast episode."""
    INTRO = "intro"
    HOOK = "hook"
    DISCUSSION = "discussion"
    EXAMPLE = "example"
    QUESTION = "question"
    ANSWER = "answer"
    ANALOGY = "analogy"
    RECAP = "recap"
    OUTRO = "outro"
    TRANSITION = "transition"


class EmotionHint(Enum):
    """Emotional tone hints for voice synthesis."""
    NEUTRAL = "neutral"
    EXCITED = "excited"
    CURIOUS = "curious"
    THOUGHTFUL = "thoughtful"
    ENTHUSIASTIC = "enthusiastic"
    SURPRISED = "surprised"
    ENCOURAGING = "encouraging"
    CONTEMPLATIVE = "contemplative"


@dataclass
class DialogueTurn:
    """
    A single turn of dialogue in the podcast.

    Represents one speaker's contribution with metadata
    for synthesis and validation.
    """
    speaker: Speaker
    text: str
    segment_type: SegmentType = SegmentType.DISCUSSION
    emotion: EmotionHint = EmotionHint.NEUTRAL
    emphasis_words: List[str] = field(default_factory=list)
    pause_before_ms: int = 500
    pause_after_ms: int = 300

    @property
    def word_count(self) -> int:
        """Count words in the text."""
        return len(self.text.split())

    @property
    def estimated_duration_seconds(self) -> float:
        """Estimate speaking duration at ~150 WPM."""
        words = self.word_count
        pauses = (self.pause_before_ms + self.pause_after_ms) / 1000
        return (words / 2.5) + pauses

    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization."""
        return {
            'speaker': self.speaker.value,
            'text': self.text,
            'segment_type': self.segment_type.value,
            'emotion': self.emotion.value,
            'emphasis_words': self.emphasis_words,
            'word_count': self.word_count
        }

    @classmethod
    def from_dict(cls, data: Dict) -> 'DialogueTurn':
        """Create from dictionary."""
        return cls(
            speaker=Speaker(data['speaker']),
            text=data['text'],
            segment_type=SegmentType(data.get('segment_type', 'discussion')),
            emotion=EmotionHint(data.get('emotion', 'neutral')),
            emphasis_words=data.get('emphasis_words', []),
            pause_before_ms=data.get('pause_before_ms', 500),
            pause_after_ms=data.get('pause_after_ms', 300)
        )


@dataclass
class EpisodeSegment:
    """
    A segment of the episode containing related dialogue turns.

    Groups turns by topic or purpose (intro, main discussion, etc.)
    """
    name: str
    segment_type: SegmentType
    turns: List[DialogueTurn] = field(default_factory=list)
    topic: Optional[str] = None

    @property
    def duration_seconds(self) -> float:
        """Total duration of this segment."""
        return sum(turn.estimated_duration_seconds for turn in self.turns)

    @property
    def word_count(self) -> int:
        """Total words in this segment."""
        return sum(turn.word_count for turn in self.turns)

    def to_dict(self) -> Dict:
        return {
            'name': self.name,
            'segment_type': self.segment_type.value,
            'topic': self.topic,
            'turns': [turn.to_dict() for turn in self.turns],
            'duration_seconds': round(self.duration_seconds, 1),
            'word_count': self.word_count
        }


@dataclass
class EpisodeScript:
    """
    Complete script for a podcast episode.

    Contains all dialogue turns, metadata, and metrics.
    """
    title: str
    lesson_number: int
    total_lessons: int
    topic_description: str
    key_concepts: List[str]
    segments: List[EpisodeSegment] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.utcnow)
    source_url: Optional[str] = None

    @property
    def all_turns(self) -> List[DialogueTurn]:
        """Flatten all turns from all segments."""
        turns = []
        for segment in self.segments:
            turns.extend(segment.turns)
        return turns

    @property
    def total_duration_seconds(self) -> float:
        """Total estimated duration of the episode."""
        return sum(segment.duration_seconds for segment in self.segments)

    @property
    def estimated_duration_minutes(self) -> float:
        """Estimated duration in minutes."""
        return self.total_duration_seconds / 60.0

    @property
    def total_words(self) -> int:
        """Total word count."""
        return sum(segment.word_count for segment in self.segments)

    @property
    def alex_words(self) -> int:
        """Words spoken by Alex."""
        return sum(
            turn.word_count for turn in self.all_turns
            if turn.speaker == Speaker.ALEX
        )

    @property
    def sam_words(self) -> int:
        """Words spoken by Sam."""
        return sum(
            turn.word_count for turn in self.all_turns
            if turn.speaker == Speaker.SAM
        )

    @property
    def speaker_balance(self) -> float:
        """
        Ratio of Alex to Sam speaking time.

        Ideal is ~1.5-2.0 (Alex speaks ~60-65% of the time)
        """
        if self.sam_words == 0:
            return float('inf')
        return self.alex_words / self.sam_words

    @property
    def turn_count(self) -> int:
        """Total number of dialogue turns."""
        return len(self.all_turns)

    def get_transcript(self) -> str:
        """Generate a readable transcript."""
        lines = [f"# {self.title}\n"]
        lines.append(f"Episode {self.lesson_number} of {self.total_lessons}\n")
        lines.append("-" * 50 + "\n")

        for segment in self.segments:
            lines.append(f"\n## {segment.name}\n")
            for turn in segment.turns:
                speaker = turn.speaker.display_name
                lines.append(f"**{speaker}:** {turn.text}\n")

        return "\n".join(lines)

    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization."""
        return {
            'title': self.title,
            'lesson_number': self.lesson_number,
            'total_lessons': self.total_lessons,
            'topic_description': self.topic_description,
            'key_concepts': self.key_concepts,
            'segments': [seg.to_dict() for seg in self.segments],
            'created_at': self.created_at.isoformat(),
            'source_url': self.source_url,
            'metrics': {
                'total_duration_seconds': round(self.total_duration_seconds, 1),
                'total_words': self.total_words,
                'turn_count': self.turn_count,
                'alex_words': self.alex_words,
                'sam_words': self.sam_words,
                'speaker_balance': round(self.speaker_balance, 2)
            }
        }

    def to_json(self) -> str:
        """Serialize to JSON string."""
        return json.dumps(self.to_dict(), indent=2)

    @classmethod
    def from_dict(cls, data: Dict) -> 'EpisodeScript':
        """Create from dictionary."""
        segments = []
        for seg_data in data.get('segments', []):
            turns = [DialogueTurn.from_dict(t) for t in seg_data.get('turns', [])]
            segments.append(EpisodeSegment(
                name=seg_data['name'],
                segment_type=SegmentType(seg_data['segment_type']),
                turns=turns,
                topic=seg_data.get('topic')
            ))

        return cls(
            title=data['title'],
            lesson_number=data['lesson_number'],
            total_lessons=data['total_lessons'],
            topic_description=data['topic_description'],
            key_concepts=data['key_concepts'],
            segments=segments,
            created_at=datetime.fromisoformat(data.get('created_at', datetime.utcnow().isoformat())),
            source_url=data.get('source_url')
        )


@dataclass
class LessonPlan:
    """
    Complete lesson plan generated from source content.
    """
    title: str
    source_url: str
    total_lessons: int
    lessons: List[Dict]
    created_at: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> Dict:
        return {
            'title': self.title,
            'source_url': self.source_url,
            'total_lessons': self.total_lessons,
            'lessons': self.lessons,
            'created_at': self.created_at.isoformat()
        }


@dataclass
class ConversationPattern:
    """
    Defines a conversational pattern for dialogue generation.

    Used to create natural back-and-forth exchanges.
    """
    name: str
    description: str
    turns: List[Dict]  # Template turns with speaker and type hints

    @classmethod
    def explain_concept(cls) -> 'ConversationPattern':
        """Pattern for explaining a concept."""
        return cls(
            name="explain_concept",
            description="Alex explains, Sam asks for clarification",
            turns=[
                {"speaker": "alex", "type": "explanation", "emotion": "encouraging"},
                {"speaker": "sam", "type": "question", "emotion": "curious"},
                {"speaker": "alex", "type": "clarification", "emotion": "thoughtful"},
                {"speaker": "sam", "type": "understanding", "emotion": "excited"},
            ]
        )

    @classmethod
    def analogy(cls) -> 'ConversationPattern':
        """Pattern for using an analogy."""
        return cls(
            name="analogy",
            description="Alex uses analogy, Sam connects the dots",
            turns=[
                {"speaker": "alex", "type": "analogy", "emotion": "enthusiastic"},
                {"speaker": "sam", "type": "connection", "emotion": "surprised"},
                {"speaker": "alex", "type": "confirmation", "emotion": "encouraging"},
            ]
        )

    @classmethod
    def example(cls) -> 'ConversationPattern':
        """Pattern for walking through an example."""
        return cls(
            name="example",
            description="Step-by-step example walkthrough",
            turns=[
                {"speaker": "alex", "type": "setup", "emotion": "neutral"},
                {"speaker": "sam", "type": "question", "emotion": "curious"},
                {"speaker": "alex", "type": "walkthrough", "emotion": "thoughtful"},
                {"speaker": "sam", "type": "insight", "emotion": "excited"},
            ]
        )

    @classmethod
    def recap(cls) -> 'ConversationPattern':
        """Pattern for recap/summary."""
        return cls(
            name="recap",
            description="Sam summarizes, Alex confirms",
            turns=[
                {"speaker": "sam", "type": "summary", "emotion": "thoughtful"},
                {"speaker": "alex", "type": "confirmation", "emotion": "encouraging"},
                {"speaker": "sam", "type": "takeaway", "emotion": "enthusiastic"},
            ]
        )


# =============================================================================
# Validation Functions
# =============================================================================

def validate_script(script: EpisodeScript) -> Dict[str, any]:
    """
    Validate an episode script for quality and completeness.

    Returns:
        Dict with 'valid' bool and 'issues' list
    """
    issues = []
    warnings = []

    # Check minimum turns
    if script.turn_count < 10:
        issues.append(f"Script has only {script.turn_count} turns (minimum 10)")

    # Check duration
    if script.total_duration_seconds < 180:  # 3 minutes
        issues.append(f"Script is too short: {script.total_duration_seconds:.0f}s (minimum 180s)")
    elif script.total_duration_seconds > 900:  # 15 minutes
        warnings.append(f"Script is quite long: {script.total_duration_seconds:.0f}s")

    # Check speaker balance
    balance = script.speaker_balance
    if balance < 1.2:
        warnings.append(f"Sam speaks too much relative to Alex (balance: {balance:.2f})")
    elif balance > 3.0:
        warnings.append(f"Alex dominates conversation (balance: {balance:.2f})")

    # Check for intro and outro
    segment_types = [seg.segment_type for seg in script.segments]
    if SegmentType.INTRO not in segment_types:
        issues.append("Missing intro segment")
    if SegmentType.OUTRO not in segment_types:
        issues.append("Missing outro segment")

    # Check turn length variation
    turn_lengths = [turn.word_count for turn in script.all_turns]
    if turn_lengths:
        avg_length = sum(turn_lengths) / len(turn_lengths)
        if avg_length > 100:
            warnings.append(f"Average turn is too long ({avg_length:.0f} words)")
        elif avg_length < 10:
            warnings.append(f"Average turn is too short ({avg_length:.0f} words)")

    # Check for concept coverage
    if not script.key_concepts:
        warnings.append("No key concepts defined")

    return {
        'valid': len(issues) == 0,
        'issues': issues,
        'warnings': warnings,
        'metrics': {
            'turn_count': script.turn_count,
            'duration_seconds': round(script.total_duration_seconds, 1),
            'speaker_balance': round(balance, 2),
            'avg_turn_words': round(sum(turn_lengths) / len(turn_lengths), 1) if turn_lengths else 0
        }
    }


# =============================================================================
# Demo
# =============================================================================

if __name__ == "__main__":
    # Create sample script
    intro_segment = EpisodeSegment(
        name="Introduction",
        segment_type=SegmentType.INTRO,
        turns=[
            DialogueTurn(
                speaker=Speaker.ALEX,
                text="Welcome to Tech Explained! I'm Alex, and today we're diving into Python decorators.",
                segment_type=SegmentType.INTRO,
                emotion=EmotionHint.ENTHUSIASTIC
            ),
            DialogueTurn(
                speaker=Speaker.SAM,
                text="Hey Alex! I've seen decorators in code but they always looked like magic to me.",
                segment_type=SegmentType.INTRO,
                emotion=EmotionHint.CURIOUS
            )
        ]
    )

    script = EpisodeScript(
        title="Understanding Python Decorators",
        lesson_number=1,
        total_lessons=3,
        topic_description="Introduction to Python decorators and their use cases",
        key_concepts=["decorators", "functions as arguments", "@syntax"],
        segments=[intro_segment]
    )

    print(script.to_json())
    print("\nValidation:", validate_script(script))
