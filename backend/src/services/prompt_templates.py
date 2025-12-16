"""
Prompt Templates for Podcast Generation

Contains carefully crafted prompts for generating natural, engaging
two-host podcast dialogues using LLM.

Templates include:
- Lesson plan generation
- Episode script generation
- Segment-specific prompts
- Refinement prompts
"""

from typing import Dict, List, Optional


# =============================================================================
# Host Personas
# =============================================================================

ALEX_PERSONA = """ALEX (Expert Host):
- Senior software engineer with 15+ years of experience
- Patient teacher who loves making complex topics accessible
- Uses creative analogies and real-world examples
- Speaks with warm confidence, never condescending
- Naturally pauses to check understanding
- Voice: Matthew (Neural) - warm, authoritative, encouraging

Speaking patterns:
- "Let me break this down..."
- "Here's a way to think about it..."
- "The key insight here is..."
- "In my experience..."
- "What's really happening under the hood is..."
- Often uses "we" to include the listener
"""

SAM_PERSONA = """SAM (Co-Host/Learner):
- Junior developer with 2 years experience, always eager to learn
- Asks the questions that listeners are thinking
- Great at summarizing and connecting concepts
- Not afraid to say "wait, I'm confused" or "can you explain that differently?"
- Celebrates "aha moments" authentically
- Voice: Joanna (Neural) - enthusiastic, curious, relatable

Speaking patterns:
- "Oh, so it's like..."
- "Wait, so you're saying..."
- "That makes so much sense!"
- "I always wondered why..."
- "Let me see if I've got this right..."
- Often paraphrases to confirm understanding
"""


# =============================================================================
# Lesson Plan Prompt
# =============================================================================

LESSON_PLAN_PROMPT = """You are an expert curriculum designer for a technical podcast.

Analyze the following content and create a structured lesson plan that will be turned into podcast episodes.

CONTENT TITLE: {title}

SOURCE CONTENT:
{content}

REQUIREMENTS:
- Create exactly {num_lessons} lessons
- Each lesson should be self-contained but build on previous lessons
- Progress from foundational concepts to more advanced topics
- Each lesson should have 3-5 key concepts to cover
- Lessons should be 8-12 minutes when spoken

Return your response as valid JSON in this exact format:
{{
    "lessons": [
        {{
            "title": "Engaging lesson title",
            "description": "2-3 sentence description of what this lesson covers and why it matters",
            "key_concepts": ["concept1", "concept2", "concept3"],
            "learning_objectives": ["objective1", "objective2"],
            "estimated_duration": 10,
            "prerequisites": ["what learner should know first"],
            "hooks": ["interesting question or fact to grab attention"]
        }}
    ],
    "series_summary": "Brief overview of the entire learning journey"
}}

IMPORTANT: Return ONLY valid JSON, no additional text or explanation."""


# =============================================================================
# Episode Script Prompt
# =============================================================================

EPISODE_SCRIPT_PROMPT = """You are a scriptwriter for "Tech Explained", an educational podcast with two hosts.

{alex_persona}

{sam_persona}

---

EPISODE DETAILS:
- Title: {topic_title}
- Description: {topic_description}
- Key Concepts: {key_concepts}
- Target Duration: {duration} minutes
- Episode {lesson_number} of {total_lessons}

SOURCE CONTENT:
{content}

{context_notes}

---

EPISODE STRUCTURE:

1. **INTRO (60 seconds)**
   - Alex welcomes listeners warmly
   - Sam expresses genuine curiosity about the topic
   - Hook with interesting fact or relatable scenario

2. **CONCEPT FOUNDATION ({foundation_duration} minutes)**
   - Alex introduces the core concept
   - Sam asks "why does this matter?" or "when would I use this?"
   - Alex provides real-world context

3. **DEEP DIVE ({dive_duration} minutes)**
   - Explain key concepts one by one
   - Sam asks clarifying questions
   - Use analogies to explain complex parts
   - Include at least one "aha moment"

4. **PRACTICAL EXAMPLE ({example_duration} minutes)**
   - Walk through a concrete example
   - Sam connects theory to practice
   - Discuss common mistakes or gotchas

5. **RECAP (90 seconds)**
   - Sam summarizes the key takeaways
   - Alex confirms and adds any crucial points
   - Reinforce the most important concept

6. **OUTRO (30 seconds)**
   - Alex thanks listeners
   - {outro_note}

---

DIALOGUE GUIDELINES:
- Keep each speaking turn to 2-4 sentences for natural pacing
- Alex explains, Sam questions and summarizes
- Include verbal reactions: "Exactly!", "Hmm, that's interesting", "Oh wow"
- Natural transitions between topics
- Make technical content accessible without dumbing it down
- Include at least one analogy per key concept
- Sam should have genuine "lightbulb moments"

---

Return the script as valid JSON:
{{
    "script": [
        {{
            "speaker": "alex",
            "text": "Welcome to Tech Explained! Today we're exploring...",
            "segment_type": "intro",
            "emotion": "enthusiastic"
        }},
        {{
            "speaker": "sam",
            "text": "Hey everyone! Alex, I've been really curious about...",
            "segment_type": "intro",
            "emotion": "curious"
        }}
    ]
}}

Emotions: neutral, excited, curious, thoughtful, enthusiastic, surprised, encouraging, contemplative

CRITICAL: Return ONLY valid JSON. Each segment should feel like natural conversation, not a lecture."""


# =============================================================================
# Segment-Specific Prompts
# =============================================================================

ANALOGY_PROMPT = """Generate a creative analogy to explain this technical concept:

CONCEPT: {concept}
CONTEXT: {context}
TARGET AUDIENCE: Developers with some experience but new to this specific topic

Requirements:
- Use a familiar everyday scenario
- Map multiple aspects of the concept to the analogy
- Keep it memorable and shareable

Return as JSON:
{{
    "analogy": "The analogy text",
    "explanation": "How it maps to the concept",
    "potential_followup": "Question Sam might ask"
}}"""


EXAMPLE_PROMPT = """Generate a practical example for this concept:

CONCEPT: {concept}
KEY POINTS TO DEMONSTRATE: {key_points}

Requirements:
- Real-world scenario a developer would encounter
- Step-by-step walkthrough
- Common pitfall to mention
- Success outcome

Return as JSON:
{{
    "scenario": "Description of the situation",
    "walkthrough": ["step1", "step2", "step3"],
    "pitfall": "Common mistake to avoid",
    "outcome": "What success looks like"
}}"""


TRANSITION_PROMPT = """Generate a natural transition between these topics:

FROM: {from_topic}
TO: {to_topic}
SPEAKER: {speaker}

Requirements:
- Feel natural, not forced
- Connect the two concepts
- Optionally include a brief callback to what was just covered

Return as JSON:
{{
    "transition": "The transition text",
    "speaker": "{speaker}"
}}"""


# =============================================================================
# Refinement Prompts
# =============================================================================

SCRIPT_REFINEMENT_PROMPT = """Review and improve this podcast script segment:

CURRENT SCRIPT:
{current_script}

ISSUES TO ADDRESS:
{issues}

Requirements:
- Maintain the same structure and speaker order
- Make dialogue more natural and conversational
- Ensure technical accuracy
- Keep similar length

Return the improved script in the same JSON format."""


BALANCE_CHECK_PROMPT = """Analyze this podcast script for speaker balance:

SCRIPT:
{script}

Check for:
1. Alex/Sam speaking ratio (target: Alex 60%, Sam 40%)
2. Turn length variation (avoid monologues)
3. Natural back-and-forth rhythm
4. Sam has meaningful contributions, not just "yeah" or "uh-huh"

Return analysis as JSON:
{{
    "alex_percentage": 60,
    "sam_percentage": 40,
    "avg_alex_turn_words": 50,
    "avg_sam_turn_words": 30,
    "issues": ["any problems found"],
    "suggestions": ["how to improve"]
}}"""


# =============================================================================
# Helper Functions
# =============================================================================

def build_episode_prompt(
    topic: Dict,
    content: str,
    lesson_number: int,
    total_lessons: int,
    target_duration: int = 10
) -> str:
    """
    Build the complete episode script prompt with all parameters.

    Args:
        topic: Lesson topic dictionary
        content: Source content
        lesson_number: Current lesson number
        total_lessons: Total lessons in series
        target_duration: Target duration in minutes

    Returns:
        Formatted prompt string
    """
    # Calculate segment durations
    foundation_duration = max(1, target_duration // 5)
    dive_duration = max(3, (target_duration * 2) // 5)
    example_duration = max(2, target_duration // 5)

    # Build context notes
    context_notes = []
    if lesson_number == 1:
        context_notes.append("This is the FIRST episode - introduce the series concept.")
    elif lesson_number == total_lessons:
        context_notes.append("This is the FINAL episode - wrap up the series.")
    else:
        context_notes.append(f"This is episode {lesson_number} - reference previous lessons where relevant.")

    if lesson_number < total_lessons:
        context_notes.append("Tease what's coming in the next episode.")

    # Build outro note
    if lesson_number == total_lessons:
        outro_note = "Wrap up the series and encourage listeners to apply what they've learned"
    else:
        outro_note = "Preview what's coming in the next episode"

    return EPISODE_SCRIPT_PROMPT.format(
        alex_persona=ALEX_PERSONA,
        sam_persona=SAM_PERSONA,
        topic_title=topic.get('title', 'Topic'),
        topic_description=topic.get('description', ''),
        key_concepts=", ".join(topic.get('key_concepts', ['general concepts'])),
        duration=target_duration,
        lesson_number=lesson_number,
        total_lessons=total_lessons,
        content=content[:6000] + ("..." if len(content) > 6000 else ""),
        context_notes="\n".join(context_notes),
        foundation_duration=foundation_duration,
        dive_duration=dive_duration,
        example_duration=example_duration,
        outro_note=outro_note
    )


def build_lesson_plan_prompt(
    content: str,
    title: str,
    num_lessons: int = 3
) -> str:
    """
    Build the lesson plan generation prompt.

    Args:
        content: Source content
        title: Content title
        num_lessons: Number of lessons to create

    Returns:
        Formatted prompt string
    """
    # Truncate content if needed
    max_content = 8000
    if len(content) > max_content:
        content = content[:max_content] + "\n\n[Content truncated for length...]"

    return LESSON_PLAN_PROMPT.format(
        title=title,
        content=content,
        num_lessons=num_lessons
    )


def get_emotion_for_segment(segment_type: str, speaker: str) -> str:
    """
    Get appropriate emotion hint based on segment type and speaker.

    Args:
        segment_type: Type of segment
        speaker: Speaker name

    Returns:
        Emotion hint string
    """
    emotion_map = {
        ('intro', 'alex'): 'enthusiastic',
        ('intro', 'sam'): 'curious',
        ('discussion', 'alex'): 'thoughtful',
        ('discussion', 'sam'): 'curious',
        ('example', 'alex'): 'neutral',
        ('example', 'sam'): 'excited',
        ('question', 'sam'): 'curious',
        ('answer', 'alex'): 'encouraging',
        ('recap', 'sam'): 'enthusiastic',
        ('recap', 'alex'): 'encouraging',
        ('outro', 'alex'): 'enthusiastic',
        ('outro', 'sam'): 'enthusiastic',
    }

    return emotion_map.get((segment_type, speaker), 'neutral')


# =============================================================================
# Demo
# =============================================================================

if __name__ == "__main__":
    # Example usage
    topic = {
        'title': 'Understanding Python Decorators',
        'description': 'Learn how decorators work and when to use them',
        'key_concepts': ['decorators', 'higher-order functions', '@syntax']
    }

    content = """
    Python decorators are a powerful feature that allows you to modify
    the behavior of functions or classes. A decorator is essentially a
    function that takes another function as an argument and returns a
    modified version of that function.
    """

    prompt = build_episode_prompt(
        topic=topic,
        content=content,
        lesson_number=1,
        total_lessons=3,
        target_duration=10
    )

    print("Generated prompt length:", len(prompt))
    print("\n--- First 1000 chars ---")
    print(prompt[:1000])
