"""
Podcast Generator Service

Generates two-host dialogue scripts for podcast-style lessons using Ollama.

Hosts:
- Alex (voiced by Matthew): Senior engineer, patient and knowledgeable
- Sam (voiced by Joanna): Curious learner, asks clarifying questions

Episode Structure:
1. Intro - Alex welcomes listeners, introduces topic
2. Discussion - Back-and-forth explaining concepts
3. Examples - Real-world applications and code examples
4. Recap - Sam summarizes key points
5. Outro - Alex wraps up, previews next lesson
"""

import json
import logging
import requests
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict

from .dialogue_models import (
    DialogueTurn, EpisodeScript, EpisodeSegment, LessonPlan,
    Speaker, SegmentType, EmotionHint,
    validate_script
)
from .prompt_templates import (
    build_episode_prompt, build_lesson_plan_prompt,
    ALEX_PERSONA, SAM_PERSONA
)
from .script_formatter import ScriptFormatter, format_for_polly

logger = logging.getLogger(__name__)


@dataclass
class DialogueSegment:
    """A single segment of dialogue in the podcast."""
    speaker: str  # 'alex' or 'sam'
    text: str
    segment_type: str  # 'intro', 'discussion', 'example', 'recap', 'outro'

    def to_dict(self):
        return asdict(self)


@dataclass
class LessonTopic:
    """A topic for a lesson in the plan."""
    title: str
    description: str
    key_concepts: List[str]
    estimated_duration: int  # in minutes

    def to_dict(self):
        return asdict(self)


class PodcastGenerator:
    """
    Generates podcast-style dialogue scripts using Ollama LLM.
    """

    # Prompt templates for different generation tasks
    LESSON_PLAN_PROMPT = """You are an educational curriculum designer. Analyze the following content and create a lesson plan.

CONTENT TITLE: {title}

CONTENT:
{content}

Create exactly {num_lessons} lessons that progressively teach the key concepts. Each lesson should build on the previous one.

Return your response as valid JSON in this exact format:
{{
    "lessons": [
        {{
            "title": "Lesson title here",
            "description": "Brief description of what this lesson covers",
            "key_concepts": ["concept1", "concept2", "concept3"],
            "estimated_duration": 10
        }}
    ]
}}

IMPORTANT: Return ONLY the JSON, no other text."""

    EPISODE_SCRIPT_PROMPT = """You are a scriptwriter for an educational podcast called "Tech Explained".
Write a dialogue script for a {duration}-minute episode.

HOSTS:
- Alex (he/him): Senior software engineer with 15 years experience. Patient, uses great analogies, explains complex topics simply. Voice: warm, confident, encouraging.
- Sam (she/her): Junior developer, 2 years experience. Curious, asks the questions listeners would ask, great at summarizing. Voice: enthusiastic, relatable.

TOPIC: {topic_title}
DESCRIPTION: {topic_description}
KEY CONCEPTS TO COVER: {key_concepts}

SOURCE CONTENT:
{content}

EPISODE STRUCTURE:
1. **Intro (1 min)**: Alex welcomes listeners, introduces today's topic
2. **Main Discussion (6-8 min)**: Back-and-forth explaining concepts, Sam asks clarifying questions
3. **Practical Examples (2-3 min)**: Real-world applications or code examples
4. **Recap (1-2 min)**: Sam summarizes the key takeaways
5. **Outro (30 sec)**: Alex thanks listeners, previews what's next

LESSON CONTEXT: This is lesson {lesson_number} of {total_lessons}.
{prev_lesson_context}
{next_lesson_context}

GUIDELINES:
- Make it conversational and engaging, not lecture-style
- Alex explains, Sam asks follow-up questions and summarizes
- Use analogies to explain complex concepts
- Include at least one "aha moment" where Sam connects the dots
- Keep technical accuracy while being accessible
- Avoid jargon without explanation

Return the script as valid JSON in this exact format:
{{
    "script": [
        {{"speaker": "alex", "text": "Welcome to Tech Explained...", "segment_type": "intro"}},
        {{"speaker": "sam", "text": "Hey Alex! I'm excited about today's topic...", "segment_type": "intro"}},
        {{"speaker": "alex", "text": "...", "segment_type": "discussion"}},
        {{"speaker": "sam", "text": "...", "segment_type": "discussion"}}
    ]
}}

IMPORTANT: Return ONLY the JSON, no other text. Each text segment should be 2-4 sentences max for natural speech."""

    def __init__(
        self,
        ollama_host: str = "http://localhost:11434",
        model: str = "llama3.2",
        timeout: int = 120
    ):
        """
        Initialize the podcast generator.

        Args:
            ollama_host: Ollama server URL
            model: Model name to use for generation
            timeout: Request timeout in seconds
        """
        self.ollama_host = ollama_host.rstrip('/')
        self.model = model
        self.timeout = timeout
        self.api_url = f"{self.ollama_host}/api/generate"
        self.formatter = ScriptFormatter()

    def check_health(self) -> bool:
        """Check if Ollama is available."""
        try:
            response = requests.get(f"{self.ollama_host}/api/tags", timeout=5)
            return response.status_code == 200
        except Exception as e:
            logger.warning(f"Ollama health check failed: {e}")
            return False

    def _call_ollama(self, prompt: str, temperature: float = 0.7) -> str:
        """
        Call Ollama API with the given prompt.

        Args:
            prompt: The prompt to send
            temperature: Creativity level (0-1)

        Returns:
            Generated text response
        """
        try:
            response = requests.post(
                self.api_url,
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "temperature": temperature,
                        "num_predict": 4096
                    }
                },
                timeout=300  # 5 minutes for script generation
            )
            response.raise_for_status()

            result = response.json()
            return result.get('response', '')

        except requests.exceptions.Timeout:
            logger.error("Ollama request timed out")
            raise TimeoutError("Ollama request timed out after 300 seconds")
        except requests.exceptions.RequestException as e:
            logger.error(f"Ollama request failed: {e}")
            raise ConnectionError(f"Failed to connect to Ollama: {e}")

    def _parse_json_response(self, response: str) -> dict:
        """
        Parse JSON from Ollama response, handling common issues.

        Args:
            response: Raw response text

        Returns:
            Parsed JSON as dict
        """
        # Try to find JSON in the response
        text = response.strip()

        # Try direct parse first
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass

        # Look for JSON between code blocks
        if "```json" in text:
            start = text.find("```json") + 7
            end = text.find("```", start)
            if end > start:
                text = text[start:end].strip()
        elif "```" in text:
            start = text.find("```") + 3
            end = text.find("```", start)
            if end > start:
                text = text[start:end].strip()

        # Look for JSON object
        start = text.find('{')
        end = text.rfind('}') + 1
        if start >= 0 and end > start:
            text = text[start:end]

        try:
            return json.loads(text)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON: {e}")
            logger.error(f"Response was: {response[:500]}...")
            raise ValueError(f"Invalid JSON in response: {e}")

    def create_lesson_plan(
        self,
        content: str,
        title: str,
        num_lessons: int = 3
    ) -> List[Dict]:
        """
        Create a lesson plan from content.

        Args:
            content: Extracted text content from URL
            title: Title of the source material
            num_lessons: Number of lessons to create

        Returns:
            List of lesson topic dictionaries
        """
        logger.info(f"Creating lesson plan for '{title}' with {num_lessons} lessons")

        # Truncate content if too long
        max_content = 8000  # Leave room for prompt
        if len(content) > max_content:
            content = content[:max_content] + "\n\n[Content truncated...]"

        prompt = self.LESSON_PLAN_PROMPT.format(
            title=title,
            content=content,
            num_lessons=num_lessons
        )

        response = self._call_ollama(prompt, temperature=0.5)
        result = self._parse_json_response(response)

        lessons = result.get('lessons', [])

        # Validate and normalize lessons
        normalized = []
        for i, lesson in enumerate(lessons[:num_lessons]):
            normalized.append({
                'title': lesson.get('title', f'Lesson {i + 1}'),
                'description': lesson.get('description', ''),
                'key_concepts': lesson.get('key_concepts', [])[:5],
                'estimated_duration': lesson.get('estimated_duration', 10)
            })

        logger.info(f"Created {len(normalized)} lesson topics")
        return normalized

    def generate_episode_script(
        self,
        topic: Dict,
        content: str,
        lesson_number: int,
        total_lessons: int,
        target_duration: int = 10
    ) -> List[Dict]:
        """
        Generate a podcast episode script for a lesson.

        Args:
            topic: Lesson topic dictionary with title, description, key_concepts
            content: Source content for context
            lesson_number: Current lesson number
            total_lessons: Total lessons in the series
            target_duration: Target episode duration in minutes

        Returns:
            List of DialogueSegment dictionaries
        """
        logger.info(f"Generating script for '{topic.get('title', 'Unknown')}'")

        # Build context about previous/next lessons
        prev_context = ""
        if lesson_number > 1:
            prev_context = "Reference concepts from earlier lessons when relevant."

        next_context = ""
        if lesson_number < total_lessons:
            next_context = "Tease what's coming in the next lesson."
        elif lesson_number == total_lessons:
            next_context = "This is the final lesson - wrap up the series."

        # Truncate content
        max_content = 6000
        if len(content) > max_content:
            content = content[:max_content] + "\n\n[Content truncated...]"

        prompt = self.EPISODE_SCRIPT_PROMPT.format(
            duration=target_duration,
            topic_title=topic.get('title', 'Topic'),
            topic_description=topic.get('description', ''),
            key_concepts=", ".join(topic.get('key_concepts', ['general concepts'])),
            content=content,
            lesson_number=lesson_number,
            total_lessons=total_lessons,
            prev_lesson_context=prev_context,
            next_lesson_context=next_context
        )

        response = self._call_ollama(prompt, temperature=0.8)
        result = self._parse_json_response(response)

        script = result.get('script', [])

        # Validate and normalize script
        normalized = []
        for segment in script:
            speaker = segment.get('speaker', '').lower()
            if speaker not in ('alex', 'sam'):
                speaker = 'alex'  # Default to Alex

            text = segment.get('text', '').strip()
            if not text:
                continue

            segment_type = segment.get('segment_type', 'discussion')
            if segment_type not in ('intro', 'discussion', 'example', 'recap', 'outro'):
                segment_type = 'discussion'

            normalized.append({
                'speaker': speaker,
                'text': text,
                'segment_type': segment_type
            })

        logger.info(f"Generated script with {len(normalized)} dialogue segments")
        return normalized

    def generate_episode(
        self,
        topic: Dict,
        content: str,
        lesson_number: int,
        total_lessons: int,
        target_duration: int = 10,
        source_url: Optional[str] = None
    ) -> EpisodeScript:
        """
        Generate a complete episode script with structured models.

        This is the enhanced version that returns EpisodeScript objects
        instead of raw dictionaries.

        Args:
            topic: Lesson topic dictionary
            content: Source content
            lesson_number: Current lesson number
            total_lessons: Total lessons in series
            target_duration: Target duration in minutes
            source_url: Optional source URL for metadata

        Returns:
            EpisodeScript with all dialogue structured
        """
        logger.info(f"Generating enhanced episode for '{topic.get('title', 'Unknown')}'")

        # Use the enhanced prompt template
        prompt = build_episode_prompt(
            topic=topic,
            content=content,
            lesson_number=lesson_number,
            total_lessons=total_lessons,
            target_duration=target_duration
        )

        response = self._call_ollama(prompt, temperature=0.8)
        result = self._parse_json_response(response)

        raw_script = result.get('script', [])

        # Convert to structured models
        segments = self._organize_into_segments(raw_script)

        # Build EpisodeScript
        episode = EpisodeScript(
            title=topic.get('title', f'Lesson {lesson_number}'),
            lesson_number=lesson_number,
            total_lessons=total_lessons,
            topic_description=topic.get('description', ''),
            key_concepts=topic.get('key_concepts', []),
            segments=segments,
            source_url=source_url
        )

        # Validate the script
        validation = validate_script(episode)
        if not validation['valid']:
            logger.warning(f"Script validation issues: {validation['issues']}")
        if validation['warnings']:
            logger.info(f"Script warnings: {validation['warnings']}")

        logger.info(
            f"Generated episode: {episode.turn_count} turns, "
            f"{int(episode.total_duration_seconds)}s estimated duration"
        )

        return episode

    def _organize_into_segments(
        self,
        raw_script: List[Dict]
    ) -> List[EpisodeSegment]:
        """
        Organize raw script turns into structured segments.

        Args:
            raw_script: List of raw turn dictionaries

        Returns:
            List of EpisodeSegment objects
        """
        # Map segment type strings to enums
        type_map = {
            'intro': SegmentType.INTRO,
            'discussion': SegmentType.DISCUSSION,
            'example': SegmentType.EXAMPLE,
            'question': SegmentType.QUESTION,
            'answer': SegmentType.ANSWER,
            'recap': SegmentType.RECAP,
            'outro': SegmentType.OUTRO,
            'transition': SegmentType.TRANSITION
        }

        emotion_map = {
            'neutral': EmotionHint.NEUTRAL,
            'excited': EmotionHint.EXCITED,
            'curious': EmotionHint.CURIOUS,
            'thoughtful': EmotionHint.THOUGHTFUL,
            'enthusiastic': EmotionHint.ENTHUSIASTIC,
            'surprised': EmotionHint.SURPRISED,
            'encouraging': EmotionHint.ENCOURAGING,
            'contemplative': EmotionHint.CONTEMPLATIVE
        }

        # Group turns by segment type
        current_segment_type = None
        segments = []
        current_turns = []

        for turn_data in raw_script:
            # Parse speaker
            speaker_str = turn_data.get('speaker', '').lower()
            speaker = Speaker.ALEX if speaker_str == 'alex' else Speaker.SAM

            # Parse segment type
            seg_type_str = turn_data.get('segment_type', 'discussion').lower()
            seg_type = type_map.get(seg_type_str, SegmentType.DISCUSSION)

            # Parse emotion
            emotion_str = turn_data.get('emotion', 'neutral').lower()
            emotion = emotion_map.get(emotion_str, EmotionHint.NEUTRAL)

            # Get text
            text = turn_data.get('text', '').strip()
            if not text:
                continue

            # Create DialogueTurn
            turn = DialogueTurn(
                speaker=speaker,
                text=text,
                segment_type=seg_type,
                emotion=emotion
            )

            # Check if we need to start a new segment
            if seg_type != current_segment_type:
                # Save previous segment
                if current_turns:
                    segment_name = self._get_segment_name(current_segment_type)
                    segments.append(EpisodeSegment(
                        name=segment_name,
                        segment_type=current_segment_type,
                        turns=current_turns
                    ))

                # Start new segment
                current_segment_type = seg_type
                current_turns = [turn]
            else:
                current_turns.append(turn)

        # Don't forget last segment
        if current_turns:
            segment_name = self._get_segment_name(current_segment_type)
            segments.append(EpisodeSegment(
                name=segment_name,
                segment_type=current_segment_type,
                turns=current_turns
            ))

        return segments

    def _get_segment_name(self, segment_type: SegmentType) -> str:
        """Get human-readable segment name."""
        names = {
            SegmentType.INTRO: "Introduction",
            SegmentType.DISCUSSION: "Main Discussion",
            SegmentType.EXAMPLE: "Practical Example",
            SegmentType.QUESTION: "Q&A",
            SegmentType.ANSWER: "Explanation",
            SegmentType.RECAP: "Key Takeaways",
            SegmentType.OUTRO: "Wrap Up",
            SegmentType.TRANSITION: "Transition"
        }
        return names.get(segment_type, "Discussion")

    def format_for_synthesis(
        self,
        episode: EpisodeScript
    ) -> List[Dict]:
        """
        Format episode for audio synthesis.

        Args:
            episode: EpisodeScript to format

        Returns:
            List of synthesis-ready chunks with SSML
        """
        return self.formatter.format_for_synthesis(episode)

    def get_transcript(
        self,
        episode: EpisodeScript,
        format: str = "markdown"
    ) -> str:
        """
        Generate transcript from episode.

        Args:
            episode: EpisodeScript
            format: "markdown", "plain", or "srt"

        Returns:
            Formatted transcript
        """
        return self.formatter.generate_transcript(episode, format)

    def estimate_audio_duration(self, script: List[Dict]) -> int:
        """
        Estimate audio duration in seconds based on script.

        Average speaking rate: ~150 words per minute (2.5 words/second)

        Args:
            script: List of dialogue segments

        Returns:
            Estimated duration in seconds
        """
        total_words = sum(len(segment['text'].split()) for segment in script)
        duration_seconds = int(total_words / 2.5)
        return max(60, duration_seconds)  # Minimum 1 minute


# =============================================================================
# Demo/Testing
# =============================================================================

if __name__ == "__main__":
    # Quick test
    logging.basicConfig(level=logging.INFO)

    generator = PodcastGenerator()

    if generator.check_health():
        print("✓ Ollama is available")

        # Test lesson plan generation
        test_content = """
        Python decorators are a powerful feature that allows you to modify the behavior
        of functions or classes. A decorator is essentially a function that takes another
        function as an argument and returns a modified version of that function.

        The @decorator syntax is just syntactic sugar for calling the decorator function
        with the decorated function as an argument.

        Common use cases include logging, authentication, caching, and validation.
        """

        topics = generator.create_lesson_plan(
            content=test_content,
            title="Python Decorators",
            num_lessons=2
        )

        print(f"\n✓ Generated {len(topics)} topics:")
        for i, topic in enumerate(topics, 1):
            print(f"  {i}. {topic['title']}")

        # Test enhanced episode generation
        if topics:
            print("\n--- Testing Enhanced Episode Generation ---")
            episode = generator.generate_episode(
                topic=topics[0],
                content=test_content,
                lesson_number=1,
                total_lessons=len(topics),
                target_duration=5
            )

            print(f"\nEpisode: {episode.title}")
            print(f"Turns: {episode.turn_count}")
            print(f"Duration: {int(episode.total_duration_seconds)}s")
            print(f"Speaker balance: {episode.speaker_balance:.2f}")

            print("\n--- Transcript ---")
            print(generator.get_transcript(episode, "markdown")[:1000])

    else:
        print("✗ Ollama is not available")
