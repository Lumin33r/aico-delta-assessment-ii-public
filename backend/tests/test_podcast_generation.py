"""
Tests for Podcast Generation Pipeline

Unit tests for:
- DialogueTurn, EpisodeScript models
- PodcastGenerator
- ScriptFormatter
- Prompt templates
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

# Import modules under test
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from services.dialogue_models import (
    DialogueTurn, EpisodeScript, EpisodeSegment, LessonPlan,
    Speaker, SegmentType, EmotionHint,
    validate_script, ConversationPattern
)
from services.podcast_generator import PodcastGenerator
from services.script_formatter import ScriptFormatter, SSMLConfig
from services.prompt_templates import (
    build_episode_prompt, build_lesson_plan_prompt,
    get_emotion_for_segment
)


# =============================================================================
# Dialogue Models Tests
# =============================================================================

class TestSpeaker:
    """Tests for Speaker enum."""

    def test_speaker_values(self):
        assert Speaker.ALEX.value == "alex"
        assert Speaker.SAM.value == "sam"

    def test_speaker_display_name(self):
        assert Speaker.ALEX.display_name == "Alex"
        assert Speaker.SAM.display_name == "Sam"

    def test_speaker_voice_id(self):
        assert Speaker.ALEX.voice_id == "Matthew"
        assert Speaker.SAM.voice_id == "Joanna"

    def test_speaker_role(self):
        assert Speaker.ALEX.role == "Expert Host"
        assert Speaker.SAM.role == "Co-Host"


class TestDialogueTurn:
    """Tests for DialogueTurn dataclass."""

    @pytest.fixture
    def sample_turn(self):
        return DialogueTurn(
            speaker=Speaker.ALEX,
            text="Welcome to Tech Explained! Today we're diving into Python decorators.",
            segment_type=SegmentType.INTRO,
            emotion=EmotionHint.ENTHUSIASTIC
        )

    def test_word_count(self, sample_turn):
        assert sample_turn.word_count == 10

    def test_estimated_duration(self, sample_turn):
        # 9 words / 2.5 wps + pauses (0.8s) ≈ 4.4 seconds
        assert 3 < sample_turn.estimated_duration_seconds < 6

    def test_to_dict(self, sample_turn):
        d = sample_turn.to_dict()

        assert d['speaker'] == 'alex'
        assert d['segment_type'] == 'intro'
        assert d['emotion'] == 'enthusiastic'
        assert 'word_count' in d

    def test_from_dict(self, sample_turn):
        d = sample_turn.to_dict()
        restored = DialogueTurn.from_dict(d)

        assert restored.speaker == sample_turn.speaker
        assert restored.text == sample_turn.text
        assert restored.segment_type == sample_turn.segment_type


class TestEpisodeScript:
    """Tests for EpisodeScript dataclass."""

    @pytest.fixture
    def sample_episode(self):
        intro_segment = EpisodeSegment(
            name="Introduction",
            segment_type=SegmentType.INTRO,
            turns=[
                DialogueTurn(
                    speaker=Speaker.ALEX,
                    text="Welcome to the show! Today we discuss Python.",
                    segment_type=SegmentType.INTRO,
                    emotion=EmotionHint.ENTHUSIASTIC
                ),
                DialogueTurn(
                    speaker=Speaker.SAM,
                    text="I'm excited to learn about this topic!",
                    segment_type=SegmentType.INTRO,
                    emotion=EmotionHint.CURIOUS
                )
            ]
        )

        discussion_segment = EpisodeSegment(
            name="Main Discussion",
            segment_type=SegmentType.DISCUSSION,
            turns=[
                DialogueTurn(
                    speaker=Speaker.ALEX,
                    text="Let me explain the core concept. Python decorators wrap functions.",
                    segment_type=SegmentType.DISCUSSION,
                    emotion=EmotionHint.THOUGHTFUL
                ),
                DialogueTurn(
                    speaker=Speaker.SAM,
                    text="So they modify behavior without changing the original code?",
                    segment_type=SegmentType.DISCUSSION,
                    emotion=EmotionHint.CURIOUS
                )
            ]
        )

        outro_segment = EpisodeSegment(
            name="Wrap Up",
            segment_type=SegmentType.OUTRO,
            turns=[
                DialogueTurn(
                    speaker=Speaker.ALEX,
                    text="Thanks for listening! See you next time.",
                    segment_type=SegmentType.OUTRO,
                    emotion=EmotionHint.ENTHUSIASTIC
                )
            ]
        )

        return EpisodeScript(
            title="Understanding Python Decorators",
            lesson_number=1,
            total_lessons=3,
            topic_description="Introduction to Python decorators",
            key_concepts=["decorators", "functions", "wrappers"],
            segments=[intro_segment, discussion_segment, outro_segment]
        )

    def test_all_turns(self, sample_episode):
        turns = sample_episode.all_turns
        assert len(turns) == 5

    def test_total_words(self, sample_episode):
        assert sample_episode.total_words > 0

    def test_alex_words(self, sample_episode):
        assert sample_episode.alex_words > sample_episode.sam_words

    def test_speaker_balance(self, sample_episode):
        balance = sample_episode.speaker_balance
        # Alex should speak more
        assert balance > 1.0

    def test_get_transcript(self, sample_episode):
        transcript = sample_episode.get_transcript()

        assert "Understanding Python Decorators" in transcript
        assert "Alex:" in transcript or "**Alex:**" in transcript
        assert "Sam:" in transcript or "**Sam:**" in transcript

    def test_to_json(self, sample_episode):
        json_str = sample_episode.to_json()

        assert "Understanding Python Decorators" in json_str
        assert "metrics" in json_str


class TestValidateScript:
    """Tests for script validation."""

    def test_validate_minimal_script(self):
        """Test validation catches too few turns."""
        script = EpisodeScript(
            title="Test",
            lesson_number=1,
            total_lessons=1,
            topic_description="Test",
            key_concepts=["test"],
            segments=[]
        )

        result = validate_script(script)

        assert not result['valid']
        assert any('turns' in issue.lower() for issue in result['issues'])

    def test_validate_missing_segments(self):
        """Test validation catches missing intro/outro."""
        discussion = EpisodeSegment(
            name="Discussion",
            segment_type=SegmentType.DISCUSSION,
            turns=[
                DialogueTurn(speaker=Speaker.ALEX, text="Hello " * 20)
                for _ in range(15)
            ]
        )

        script = EpisodeScript(
            title="Test",
            lesson_number=1,
            total_lessons=1,
            topic_description="Test",
            key_concepts=["test"],
            segments=[discussion]
        )

        result = validate_script(script)

        assert any('intro' in issue.lower() for issue in result['issues'])
        assert any('outro' in issue.lower() for issue in result['issues'])


class TestConversationPattern:
    """Tests for conversation patterns."""

    def test_explain_concept_pattern(self):
        pattern = ConversationPattern.explain_concept()

        assert pattern.name == "explain_concept"
        assert len(pattern.turns) == 4
        assert pattern.turns[0]['speaker'] == 'alex'
        assert pattern.turns[1]['speaker'] == 'sam'

    def test_analogy_pattern(self):
        pattern = ConversationPattern.analogy()

        assert pattern.name == "analogy"
        assert len(pattern.turns) == 3


# =============================================================================
# Script Formatter Tests
# =============================================================================

class TestScriptFormatter:
    """Tests for ScriptFormatter class."""

    @pytest.fixture
    def formatter(self):
        return ScriptFormatter()

    @pytest.fixture
    def sample_turn(self):
        return DialogueTurn(
            speaker=Speaker.ALEX,
            text="This is a key concept. Remember this important point!",
            segment_type=SegmentType.DISCUSSION,
            emotion=EmotionHint.THOUGHTFUL,
            emphasis_words=["key", "important"]
        )

    def test_format_turn_ssml(self, formatter, sample_turn):
        ssml = formatter._format_turn_ssml(sample_turn)

        assert '<speak>' in ssml
        assert '</speak>' in ssml
        assert '<prosody' in ssml
        assert 'rate=' in ssml

    def test_add_emphasis(self, formatter):
        text = "This is important and key to understanding."
        result = formatter._add_emphasis(text, ["important"])

        assert '<emphasis' in result
        assert 'important' in result

    def test_add_natural_pauses(self, formatter):
        text = "First sentence. Second sentence! Question?"
        result = formatter._add_natural_pauses(text)

        assert '<break' in result

    def test_generate_transcript_markdown(self, formatter):
        intro = EpisodeSegment(
            name="Intro",
            segment_type=SegmentType.INTRO,
            turns=[
                DialogueTurn(speaker=Speaker.ALEX, text="Welcome!"),
                DialogueTurn(speaker=Speaker.SAM, text="Hello!")
            ]
        )

        script = EpisodeScript(
            title="Test Episode",
            lesson_number=1,
            total_lessons=1,
            topic_description="Test",
            key_concepts=["test"],
            segments=[intro]
        )

        transcript = formatter.generate_transcript(script, "markdown")

        assert "# Test Episode" in transcript
        assert "**Alex:**" in transcript
        assert "**Sam:**" in transcript

    def test_generate_transcript_srt(self, formatter):
        intro = EpisodeSegment(
            name="Intro",
            segment_type=SegmentType.INTRO,
            turns=[
                DialogueTurn(speaker=Speaker.ALEX, text="Welcome to the show!"),
            ]
        )

        script = EpisodeScript(
            title="Test",
            lesson_number=1,
            total_lessons=1,
            topic_description="Test",
            key_concepts=[],
            segments=[intro]
        )

        srt = formatter.generate_transcript(script, "srt")

        assert "00:00:00" in srt
        assert "-->" in srt


# =============================================================================
# Prompt Templates Tests
# =============================================================================

class TestPromptTemplates:
    """Tests for prompt template functions."""

    def test_build_lesson_plan_prompt(self):
        prompt = build_lesson_plan_prompt(
            content="Python is a programming language.",
            title="Python Basics",
            num_lessons=3
        )

        assert "Python Basics" in prompt
        assert "3" in prompt
        assert "JSON" in prompt

    def test_build_episode_prompt(self):
        topic = {
            'title': 'Introduction to Python',
            'description': 'Learn Python basics',
            'key_concepts': ['variables', 'functions']
        }

        prompt = build_episode_prompt(
            topic=topic,
            content="Python is versatile.",
            lesson_number=1,
            total_lessons=3,
            target_duration=10
        )

        assert "Introduction to Python" in prompt
        assert "ALEX" in prompt or "Alex" in prompt
        assert "SAM" in prompt or "Sam" in prompt
        assert "variables" in prompt

    def test_build_episode_prompt_first_episode(self):
        topic = {'title': 'Test', 'description': 'Test', 'key_concepts': []}

        prompt = build_episode_prompt(
            topic=topic,
            content="Test content",
            lesson_number=1,
            total_lessons=3,
            target_duration=10
        )

        assert "FIRST" in prompt or "first" in prompt

    def test_build_episode_prompt_last_episode(self):
        topic = {'title': 'Test', 'description': 'Test', 'key_concepts': []}

        prompt = build_episode_prompt(
            topic=topic,
            content="Test content",
            lesson_number=3,
            total_lessons=3,
            target_duration=10
        )

        assert "FINAL" in prompt or "final" in prompt

    def test_get_emotion_for_segment(self):
        assert get_emotion_for_segment('intro', 'alex') == 'enthusiastic'
        assert get_emotion_for_segment('intro', 'sam') == 'curious'
        assert get_emotion_for_segment('discussion', 'alex') == 'thoughtful'
        assert get_emotion_for_segment('recap', 'sam') == 'enthusiastic'


# =============================================================================
# PodcastGenerator Tests
# =============================================================================

class TestPodcastGenerator:
    """Tests for PodcastGenerator class."""

    @pytest.fixture
    def generator(self):
        return PodcastGenerator()

    def test_init(self, generator):
        assert generator.ollama_host == "http://localhost:11434"
        assert generator.model == "llama3.2"
        assert generator.formatter is not None

    @patch('services.podcast_generator.requests.get')
    def test_check_health_success(self, mock_get, generator):
        mock_get.return_value.status_code = 200

        assert generator.check_health() is True

    @patch('services.podcast_generator.requests.get')
    def test_check_health_failure(self, mock_get, generator):
        mock_get.side_effect = Exception("Connection failed")

        assert generator.check_health() is False

    def test_parse_json_response_clean(self, generator):
        response = '{"key": "value"}'
        result = generator._parse_json_response(response)

        assert result == {"key": "value"}

    def test_parse_json_response_with_markdown(self, generator):
        response = '''```json
{"key": "value"}
```'''
        result = generator._parse_json_response(response)

        assert result == {"key": "value"}

    def test_parse_json_response_with_text(self, generator):
        response = '''Here is the result:
{"key": "value"}
That's all!'''
        result = generator._parse_json_response(response)

        assert result == {"key": "value"}

    def test_estimate_audio_duration(self, generator):
        script = [
            {'text': 'Hello world'},  # 2 words
            {'text': 'This is a test sentence'}  # 5 words
        ]

        duration = generator.estimate_audio_duration(script)

        # 7 words / 2.5 wps = 2.8s, but min is 60
        assert duration >= 60

    def test_get_segment_name(self, generator):
        assert generator._get_segment_name(SegmentType.INTRO) == "Introduction"
        assert generator._get_segment_name(SegmentType.OUTRO) == "Wrap Up"
        assert generator._get_segment_name(SegmentType.DISCUSSION) == "Main Discussion"

    def test_organize_into_segments(self, generator):
        raw_script = [
            {'speaker': 'alex', 'text': 'Welcome!', 'segment_type': 'intro', 'emotion': 'enthusiastic'},
            {'speaker': 'sam', 'text': 'Hello!', 'segment_type': 'intro', 'emotion': 'curious'},
            {'speaker': 'alex', 'text': 'Let me explain.', 'segment_type': 'discussion', 'emotion': 'thoughtful'},
        ]

        segments = generator._organize_into_segments(raw_script)

        assert len(segments) == 2  # intro and discussion
        assert segments[0].segment_type == SegmentType.INTRO
        assert segments[1].segment_type == SegmentType.DISCUSSION


# =============================================================================
# Integration Tests
# =============================================================================

class TestIntegration:
    """Integration tests for podcast generation pipeline."""

    def test_full_formatting_pipeline(self):
        """Test complete script formatting."""
        # Create a realistic script
        intro = EpisodeSegment(
            name="Introduction",
            segment_type=SegmentType.INTRO,
            turns=[
                DialogueTurn(
                    speaker=Speaker.ALEX,
                    text="Welcome to Tech Explained! I'm Alex, and today we're exploring Python decorators.",
                    segment_type=SegmentType.INTRO,
                    emotion=EmotionHint.ENTHUSIASTIC
                ),
                DialogueTurn(
                    speaker=Speaker.SAM,
                    text="Hey everyone! Alex, I've seen those @ symbols in code. What are they?",
                    segment_type=SegmentType.INTRO,
                    emotion=EmotionHint.CURIOUS
                )
            ]
        )

        discussion = EpisodeSegment(
            name="Main Discussion",
            segment_type=SegmentType.DISCUSSION,
            turns=[
                DialogueTurn(
                    speaker=Speaker.ALEX,
                    text="Great question! Decorators are a way to modify functions. Think of them like wrappers.",
                    segment_type=SegmentType.DISCUSSION,
                    emotion=EmotionHint.ENCOURAGING
                ),
                DialogueTurn(
                    speaker=Speaker.SAM,
                    text="Oh, so it's like gift wrapping a present? The gift stays the same but gets extra decoration?",
                    segment_type=SegmentType.DISCUSSION,
                    emotion=EmotionHint.EXCITED
                ),
                DialogueTurn(
                    speaker=Speaker.ALEX,
                    text="Exactly! That's a perfect analogy. The original function stays intact.",
                    segment_type=SegmentType.DISCUSSION,
                    emotion=EmotionHint.ENTHUSIASTIC
                )
            ]
        )

        outro = EpisodeSegment(
            name="Wrap Up",
            segment_type=SegmentType.OUTRO,
            turns=[
                DialogueTurn(
                    speaker=Speaker.ALEX,
                    text="Thanks for listening! Next time we'll dive into advanced decorator patterns.",
                    segment_type=SegmentType.OUTRO,
                    emotion=EmotionHint.ENTHUSIASTIC
                )
            ]
        )

        script = EpisodeScript(
            title="Python Decorators 101",
            lesson_number=1,
            total_lessons=3,
            topic_description="Introduction to Python decorators",
            key_concepts=["decorators", "functions", "wrappers"],
            segments=[intro, discussion, outro]
        )

        # Test validation
        validation = validate_script(script)
        # May have warnings but should structurally be valid
        assert 'metrics' in validation

        # Test formatting
        formatter = ScriptFormatter()

        # Format for synthesis
        synthesis_chunks = formatter.format_for_synthesis(script)
        assert len(synthesis_chunks) > 0

        # Each chunk should have required fields
        for chunk in synthesis_chunks:
            assert 'voice_id' in chunk
            assert 'ssml' in chunk
            assert '<speak>' in chunk['ssml']

        # Generate transcripts
        md_transcript = formatter.generate_transcript(script, "markdown")
        assert "Python Decorators 101" in md_transcript

        srt_transcript = formatter.generate_transcript(script, "srt")
        assert "-->" in srt_transcript


# =============================================================================
# Run Tests
# =============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
