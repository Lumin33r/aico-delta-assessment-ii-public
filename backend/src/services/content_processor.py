"""
Content Processor Service

Processes and structures extracted content for optimal LLM consumption.
Includes chunking, summarization, topic extraction, and content enrichment.

Features:
- Smart content chunking with context preservation
- Topic and key concept extraction
- Content structure analysis
- Readability scoring
- Content deduplication
"""

import re
import logging
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from collections import Counter

logger = logging.getLogger(__name__)


@dataclass
class ContentChunk:
    """Represents a chunk of processed content."""
    text: str
    index: int
    start_char: int
    end_char: int
    word_count: int
    topics: List[str] = field(default_factory=list)
    is_code: bool = False
    heading: Optional[str] = None


@dataclass
class ProcessedContent:
    """Represents fully processed content ready for LLM."""
    title: str
    url: str
    summary: str
    chunks: List[ContentChunk]
    topics: List[str]
    key_concepts: List[str]
    total_words: int
    reading_time_minutes: int
    structure: Dict
    metadata: Dict


class ContentProcessor:
    """
    Processes extracted content for optimal LLM consumption.
    """

    # Technical terms that indicate code/programming content
    CODE_INDICATORS = [
        'function', 'class', 'def ', 'return', 'import', 'const ',
        'let ', 'var ', 'async', 'await', 'lambda', 'print(',
        '>>>',  '{', '}', '=>', '->', '==', '!='
    ]

    # Common stop words to filter from topic extraction
    STOP_WORDS = {
        'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to',
        'for', 'of', 'with', 'by', 'from', 'as', 'is', 'was', 'are',
        'were', 'been', 'be', 'have', 'has', 'had', 'do', 'does', 'did',
        'will', 'would', 'could', 'should', 'may', 'might', 'must',
        'this', 'that', 'these', 'those', 'it', 'its', 'they', 'them',
        'their', 'we', 'us', 'our', 'you', 'your', 'he', 'she', 'him',
        'her', 'his', 'hers', 'i', 'my', 'me', 'what', 'which', 'who',
        'whom', 'when', 'where', 'why', 'how', 'all', 'each', 'every',
        'both', 'few', 'more', 'most', 'other', 'some', 'such', 'no',
        'not', 'only', 'same', 'so', 'than', 'too', 'very', 'just',
        'can', 'also', 'into', 'then', 'there', 'here', 'now', 'way'
    }

    def __init__(
        self,
        chunk_size: int = 1500,
        chunk_overlap: int = 200,
        min_chunk_size: int = 100,
        max_topics: int = 10
    ):
        """
        Initialize the content processor.

        Args:
            chunk_size: Target size for content chunks (in characters)
            chunk_overlap: Overlap between chunks for context preservation
            min_chunk_size: Minimum chunk size to avoid tiny fragments
            max_topics: Maximum number of topics to extract
        """
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.min_chunk_size = min_chunk_size
        self.max_topics = max_topics

    def process(self, extracted_content: Dict) -> ProcessedContent:
        """
        Process extracted content into structured format.

        Args:
            extracted_content: Raw extracted content from ContentExtractor

        Returns:
            ProcessedContent with chunks, topics, and metadata
        """
        text = extracted_content.get('text', '')
        title = extracted_content.get('title', 'Untitled')
        url = extracted_content.get('url', '')
        metadata = extracted_content.get('metadata', {})

        logger.info(f"Processing content: {title}")

        # Analyze structure
        structure = self._analyze_structure(text)

        # Extract topics and key concepts
        topics = self._extract_topics(text, title)
        key_concepts = self._extract_key_concepts(text)

        # Generate summary
        summary = self._generate_summary(text, title)

        # Chunk content
        chunks = self._chunk_content(text, structure)

        # Enrich chunks with topics
        chunks = self._enrich_chunks(chunks, topics)

        # Calculate metrics
        total_words = len(text.split())
        reading_time = max(1, total_words // 200)  # ~200 wpm reading speed

        return ProcessedContent(
            title=title,
            url=url,
            summary=summary,
            chunks=chunks,
            topics=topics,
            key_concepts=key_concepts,
            total_words=total_words,
            reading_time_minutes=reading_time,
            structure=structure,
            metadata={
                **metadata,
                'chunk_count': len(chunks),
                'has_code': any(c.is_code for c in chunks)
            }
        )

    def _analyze_structure(self, text: str) -> Dict:
        """
        Analyze the structure of the content.

        Args:
            text: Content text

        Returns:
            Structure analysis dict
        """
        lines = text.split('\n')

        # Find headings (lines that look like titles)
        headings = []
        for i, line in enumerate(lines):
            line = line.strip()
            # Heuristics for headings
            if (
                10 < len(line) < 100 and
                not line.endswith('.') and
                not line.endswith(',') and
                line[0].isupper() and
                not any(ind in line.lower() for ind in self.CODE_INDICATORS[:5])
            ):
                headings.append({
                    'text': line,
                    'position': i,
                    'char_position': text.find(line)
                })

        # Count paragraphs
        paragraphs = [p.strip() for p in text.split('\n\n') if p.strip()]

        # Detect code blocks
        code_blocks = self._find_code_blocks(text)

        # Detect lists
        list_items = len(re.findall(r'^\s*[-•*]\s+', text, re.MULTILINE))
        list_items += len(re.findall(r'^\s*\d+\.\s+', text, re.MULTILINE))

        return {
            'headings': headings[:20],  # Limit to 20 headings
            'paragraph_count': len(paragraphs),
            'code_block_count': len(code_blocks),
            'list_item_count': list_items,
            'has_code': len(code_blocks) > 0
        }

    def _find_code_blocks(self, text: str) -> List[Tuple[int, int]]:
        """
        Find code blocks in text.

        Args:
            text: Content text

        Returns:
            List of (start, end) positions
        """
        code_blocks = []

        # Find fenced code blocks (```)
        for match in re.finditer(r'```[\s\S]*?```', text):
            code_blocks.append((match.start(), match.end()))

        # Find indented code blocks (4+ spaces at line start)
        in_code = False
        code_start = 0
        lines = text.split('\n')
        char_pos = 0

        for line in lines:
            is_code_line = line.startswith('    ') or line.startswith('\t')

            if is_code_line and not in_code:
                in_code = True
                code_start = char_pos
            elif not is_code_line and in_code and line.strip():
                in_code = False
                code_blocks.append((code_start, char_pos))

            char_pos += len(line) + 1

        return code_blocks

    def _extract_topics(self, text: str, title: str) -> List[str]:
        """
        Extract main topics from content.

        Args:
            text: Content text
            title: Content title

        Returns:
            List of topic strings
        """
        # Combine title and first portion of text
        sample_text = f"{title} {text[:5000]}".lower()

        # Extract potential topic phrases (capitalized word sequences)
        topic_pattern = r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b'
        potential_topics = re.findall(topic_pattern, f"{title} {text[:5000]}")

        # Count occurrences
        topic_counts = Counter(potential_topics)

        # Also extract important single words
        words = re.findall(r'\b[a-z]{4,}\b', sample_text)
        word_counts = Counter(words)

        # Filter stop words and get top words
        important_words = [
            word for word, count in word_counts.most_common(50)
            if word not in self.STOP_WORDS and count > 2
        ]

        # Combine multi-word topics and single words
        topics = []

        # Add multi-word topics first
        for topic, count in topic_counts.most_common(self.max_topics):
            if count > 1 and topic.lower() not in self.STOP_WORDS:
                topics.append(topic)

        # Fill with important single words
        for word in important_words:
            if len(topics) >= self.max_topics:
                break
            if word not in [t.lower() for t in topics]:
                topics.append(word.capitalize())

        return topics[:self.max_topics]

    def _extract_key_concepts(self, text: str) -> List[str]:
        """
        Extract key technical concepts and terms.

        Args:
            text: Content text

        Returns:
            List of key concepts
        """
        concepts = []

        # Find terms in quotes or emphasis
        quoted = re.findall(r'"([^"]{3,50})"', text)
        concepts.extend(quoted[:5])

        # Find technical terms (CamelCase, snake_case)
        camel_case = re.findall(r'\b[A-Z][a-z]+(?:[A-Z][a-z]+)+\b', text)
        concepts.extend(camel_case[:5])

        snake_case = re.findall(r'\b[a-z]+(?:_[a-z]+)+\b', text)
        concepts.extend(snake_case[:5])

        # Find terms followed by "is" or "are" (definitions)
        definitions = re.findall(
            r'\b([A-Z][a-z]+(?:\s+[a-z]+)?)\s+(?:is|are)\s+(?:a|an|the)',
            text
        )
        concepts.extend(definitions[:5])

        # Deduplicate while preserving order
        seen = set()
        unique_concepts = []
        for concept in concepts:
            concept_lower = concept.lower()
            if concept_lower not in seen and len(concept) > 3:
                seen.add(concept_lower)
                unique_concepts.append(concept)

        return unique_concepts[:15]

    def _generate_summary(self, text: str, title: str) -> str:
        """
        Generate a brief summary of the content.

        Args:
            text: Content text
            title: Content title

        Returns:
            Summary string
        """
        # Simple extractive summary: first meaningful sentences
        sentences = re.split(r'(?<=[.!?])\s+', text)

        summary_sentences = []
        char_count = 0
        max_chars = 500

        for sentence in sentences:
            sentence = sentence.strip()

            # Skip very short or likely non-content sentences
            if len(sentence) < 30:
                continue

            # Skip sentences that look like navigation
            if sentence.count('|') > 1 or sentence.count('>>') > 0:
                continue

            summary_sentences.append(sentence)
            char_count += len(sentence)

            if char_count >= max_chars or len(summary_sentences) >= 3:
                break

        if summary_sentences:
            return ' '.join(summary_sentences)

        # Fallback: just use first 500 chars
        return text[:500].rsplit(' ', 1)[0] + '...'

    def _chunk_content(
        self,
        text: str,
        structure: Dict
    ) -> List[ContentChunk]:
        """
        Split content into overlapping chunks.

        Args:
            text: Content text
            structure: Structure analysis

        Returns:
            List of ContentChunk objects
        """
        chunks = []

        # Try to split on paragraph boundaries first
        paragraphs = text.split('\n\n')

        current_chunk = ""
        current_start = 0
        chunk_index = 0

        for para in paragraphs:
            para = para.strip()
            if not para:
                continue

            # Check if adding this paragraph exceeds chunk size
            if len(current_chunk) + len(para) > self.chunk_size and current_chunk:
                # Save current chunk
                chunks.append(self._create_chunk(
                    text=current_chunk.strip(),
                    index=chunk_index,
                    start_char=current_start,
                    structure=structure
                ))
                chunk_index += 1

                # Start new chunk with overlap
                overlap_text = current_chunk[-self.chunk_overlap:] if len(current_chunk) > self.chunk_overlap else ""
                current_chunk = overlap_text + "\n\n" + para
                current_start = max(0, current_start + len(current_chunk) - self.chunk_overlap - len(para))
            else:
                if current_chunk:
                    current_chunk += "\n\n" + para
                else:
                    current_chunk = para

        # Don't forget the last chunk
        if current_chunk and len(current_chunk.strip()) >= self.min_chunk_size:
            chunks.append(self._create_chunk(
                text=current_chunk.strip(),
                index=chunk_index,
                start_char=current_start,
                structure=structure
            ))

        return chunks

    def _create_chunk(
        self,
        text: str,
        index: int,
        start_char: int,
        structure: Dict
    ) -> ContentChunk:
        """
        Create a ContentChunk object.

        Args:
            text: Chunk text
            index: Chunk index
            start_char: Starting character position
            structure: Content structure

        Returns:
            ContentChunk object
        """
        # Check if chunk contains code
        is_code = any(
            indicator in text.lower()
            for indicator in self.CODE_INDICATORS
        )

        # Find heading for this chunk
        heading = None
        for h in structure.get('headings', []):
            if h['char_position'] <= start_char:
                heading = h['text']

        return ContentChunk(
            text=text,
            index=index,
            start_char=start_char,
            end_char=start_char + len(text),
            word_count=len(text.split()),
            is_code=is_code,
            heading=heading
        )

    def _enrich_chunks(
        self,
        chunks: List[ContentChunk],
        topics: List[str]
    ) -> List[ContentChunk]:
        """
        Enrich chunks with relevant topics.

        Args:
            chunks: List of chunks
            topics: Extracted topics

        Returns:
            Enriched chunks
        """
        for chunk in chunks:
            chunk_lower = chunk.text.lower()
            chunk.topics = [
                topic for topic in topics
                if topic.lower() in chunk_lower
            ]

        return chunks

    def get_chunk_for_topic(
        self,
        processed: ProcessedContent,
        topic: str
    ) -> Optional[ContentChunk]:
        """
        Find the best chunk for a given topic.

        Args:
            processed: Processed content
            topic: Topic to find

        Returns:
            Best matching chunk or None
        """
        topic_lower = topic.lower()

        # First, find chunks that mention the topic
        matching_chunks = [
            chunk for chunk in processed.chunks
            if topic_lower in chunk.text.lower()
        ]

        if not matching_chunks:
            return None

        # Return the chunk with the most mentions
        return max(
            matching_chunks,
            key=lambda c: c.text.lower().count(topic_lower)
        )

    def prepare_for_llm(
        self,
        processed: ProcessedContent,
        max_tokens: int = 4000
    ) -> str:
        """
        Prepare processed content for LLM consumption.

        Args:
            processed: Processed content
            max_tokens: Approximate max tokens (chars / 4)

        Returns:
            Formatted string for LLM
        """
        max_chars = max_tokens * 4  # Rough estimate

        output = f"# {processed.title}\n\n"
        output += f"**Summary:** {processed.summary}\n\n"
        output += f"**Key Topics:** {', '.join(processed.topics)}\n\n"
        output += f"**Key Concepts:** {', '.join(processed.key_concepts)}\n\n"
        output += "---\n\n"

        # Add chunks until we hit the limit
        current_length = len(output)

        for chunk in processed.chunks:
            chunk_text = f"## Section {chunk.index + 1}"
            if chunk.heading:
                chunk_text += f": {chunk.heading}"
            chunk_text += f"\n\n{chunk.text}\n\n"

            if current_length + len(chunk_text) > max_chars:
                break

            output += chunk_text
            current_length += len(chunk_text)

        return output


# =============================================================================
# Demo/Testing
# =============================================================================

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    # Test with sample content
    sample_content = {
        'text': """
        Python Classes Tutorial

        Classes provide a means of bundling data and functionality together.
        Creating a new class creates a new type of object, allowing new instances
        of that type to be made.

        Class Definition Syntax

        The simplest form of class definition looks like this:

        class ClassName:
            <statement-1>
            .
            .
            .
            <statement-N>

        Class definitions, like function definitions (def statements) must be
        executed before they have any effect.

        Class Objects

        Class objects support two kinds of operations: attribute references
        and instantiation. Attribute references use the standard syntax used
        for all attribute references in Python: obj.name.

        Instance Objects

        Now what can we do with instance objects? The only operations understood
        by instance objects are attribute references. There are two kinds of
        valid attribute names: data attributes and methods.
        """,
        'title': 'Python Classes Tutorial',
        'url': 'https://docs.python.org/3/tutorial/classes.html',
        'metadata': {
            'extraction_method': 'test'
        }
    }

    processor = ContentProcessor(chunk_size=500)
    result = processor.process(sample_content)

    print(f"Title: {result.title}")
    print(f"Topics: {result.topics}")
    print(f"Key Concepts: {result.key_concepts}")
    print(f"Chunks: {len(result.chunks)}")
    print(f"Total Words: {result.total_words}")
    print(f"Reading Time: {result.reading_time_minutes} min")
    print("\n--- LLM Format ---\n")
    print(processor.prepare_for_llm(result, max_tokens=1000))
