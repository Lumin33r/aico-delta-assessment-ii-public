"""
Audio Synthesizer Service

Synthesizes podcast-style audio using AWS Polly with multiple neural voices.

Voices:
- Alex: Matthew (Neural) - Male, American English, warm and professional
- Sam: Joanna (Neural) - Female, American English, friendly and engaging

Features:
- Multi-voice synthesis with natural transitions
- SSML support for improved prosody
- Audio concatenation for full episodes
- S3 upload with presigned URLs
"""

import io
import os
import time
import logging
import hashlib
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from contextlib import contextmanager

import boto3
from botocore.exceptions import ClientError, NoCredentialsError

logger = logging.getLogger(__name__)


# Voice configuration for podcast hosts
VOICE_CONFIG = {
    'alex': {
        'voice_id': 'Matthew',
        'engine': 'neural',
        'language_code': 'en-US',
        'description': 'Senior engineer, warm and professional'
    },
    'sam': {
        'voice_id': 'Joanna',
        'engine': 'neural',
        'language_code': 'en-US',
        'description': 'Junior developer, friendly and curious'
    }
}

# SSML templates for natural speech
SSML_TEMPLATES = {
    'intro': '<speak><prosody rate="medium" pitch="medium">{text}</prosody></speak>',
    'discussion': '<speak><prosody rate="medium">{text}</prosody></speak>',
    'example': '<speak><prosody rate="95%">{text}</prosody></speak>',
    'recap': '<speak><prosody rate="medium" pitch="+5%">{text}</prosody></speak>',
    'outro': '<speak><prosody rate="medium" pitch="medium">{text}</prosody></speak>',
}

# Pause durations between speakers (in milliseconds)
PAUSE_BETWEEN_SPEAKERS = 500
PAUSE_SAME_SPEAKER = 200


class AudioSynthesizer:
    """
    Synthesizes multi-voice podcast audio using AWS Polly.
    """

    def __init__(
        self,
        region: str = 'us-west-2',
        bucket: str = 'ai-tutor-audio',
        local_storage: str = '/tmp/audio'
    ):
        """
        Initialize the audio synthesizer.

        Args:
            region: AWS region for Polly and S3
            bucket: S3 bucket for audio storage
            local_storage: Local directory for temporary files
        """
        self.region = region
        self.bucket = bucket
        self.local_storage = local_storage

        # Initialize AWS clients
        try:
            self.polly = boto3.client('polly', region_name=region)
            self.s3 = boto3.client('s3', region_name=region)
            self._aws_available = True
        except NoCredentialsError:
            logger.warning("AWS credentials not found - audio synthesis disabled")
            self._aws_available = False
            self.polly = None
            self.s3 = None

        # Ensure local storage exists
        os.makedirs(local_storage, exist_ok=True)

    def check_health(self) -> bool:
        """Check if Polly is available."""
        if not self._aws_available:
            return False

        try:
            self.polly.describe_voices(LanguageCode='en-US')
            return True
        except Exception as e:
            logger.warning(f"Polly health check failed: {e}")
            return False

    def _escape_ssml(self, text: str) -> str:
        """
        Escape special characters for SSML.

        Args:
            text: Raw text to escape

        Returns:
            SSML-safe text
        """
        # XML special characters
        text = text.replace('&', '&amp;')
        text = text.replace('<', '&lt;')
        text = text.replace('>', '&gt;')
        text = text.replace('"', '&quot;')
        text = text.replace("'", '&apos;')

        return text

    def _create_ssml(self, text: str, segment_type: str = 'discussion') -> str:
        """
        Wrap text in SSML for natural speech.

        Args:
            text: Text to speak
            segment_type: Type of segment for prosody selection

        Returns:
            SSML-wrapped text
        """
        escaped_text = self._escape_ssml(text)
        template = SSML_TEMPLATES.get(segment_type, SSML_TEMPLATES['discussion'])
        return template.format(text=escaped_text)

    def synthesize_segment(
        self,
        text: str,
        speaker: str,
        segment_type: str = 'discussion'
    ) -> Tuple[bytes, int]:
        """
        Synthesize a single dialogue segment.

        Args:
            text: Text to synthesize
            speaker: 'alex' or 'sam'
            segment_type: Type of segment for SSML

        Returns:
            Tuple of (audio_bytes, duration_ms)
        """
        if not self._aws_available:
            raise RuntimeError("AWS credentials not configured")

        voice_config = VOICE_CONFIG.get(speaker, VOICE_CONFIG['alex'])
        ssml = self._create_ssml(text, segment_type)

        try:
            response = self.polly.synthesize_speech(
                Engine=voice_config['engine'],
                LanguageCode=voice_config['language_code'],
                OutputFormat='mp3',
                SampleRate='24000',
                Text=ssml,
                TextType='ssml',
                VoiceId=voice_config['voice_id']
            )

            audio_stream = response['AudioStream']
            audio_bytes = audio_stream.read()

            # Estimate duration based on audio size
            # MP3 at 24kHz ~ 3KB per second
            duration_ms = int((len(audio_bytes) / 3000) * 1000)

            return audio_bytes, duration_ms

        except ClientError as e:
            logger.error(f"Polly synthesis failed: {e}")
            raise

    def synthesize_podcast(
        self,
        script: List[Dict],
        session_id: str,
        lesson_num: int
    ) -> Dict:
        """
        Synthesize full podcast episode from script.

        Args:
            script: List of dialogue segments [{speaker, text, segment_type}]
            session_id: Session identifier
            lesson_num: Lesson number

        Returns:
            Dict with url, duration_seconds, segment_count
        """
        if not self._aws_available:
            # Return mock data for local development
            return self._mock_synthesis(session_id, lesson_num, script)

        logger.info(f"Synthesizing podcast: {len(script)} segments")

        # Generate audio for each segment
        audio_segments = []
        total_duration_ms = 0
        last_speaker = None

        for i, segment in enumerate(script):
            speaker = segment.get('speaker', 'alex')
            text = segment.get('text', '')
            segment_type = segment.get('segment_type', 'discussion')

            if not text:
                continue

            # Add pause between segments
            if last_speaker is not None:
                pause_ms = PAUSE_BETWEEN_SPEAKERS if speaker != last_speaker else PAUSE_SAME_SPEAKER
                silence = self._generate_silence(pause_ms)
                audio_segments.append(silence)
                total_duration_ms += pause_ms

            # Synthesize segment
            try:
                audio_bytes, duration_ms = self.synthesize_segment(
                    text=text,
                    speaker=speaker,
                    segment_type=segment_type
                )
                audio_segments.append(audio_bytes)
                total_duration_ms += duration_ms
                last_speaker = speaker

                logger.debug(f"Segment {i+1}/{len(script)}: {speaker}, {duration_ms}ms")

            except Exception as e:
                logger.error(f"Failed to synthesize segment {i}: {e}")
                # Continue with remaining segments

        # Concatenate audio
        combined_audio = self._concatenate_mp3(audio_segments)

        # Upload to S3
        s3_key = f"lessons/{session_id}/lesson_{lesson_num}.mp3"

        try:
            self.s3.put_object(
                Bucket=self.bucket,
                Key=s3_key,
                Body=combined_audio,
                ContentType='audio/mpeg',
                Metadata={
                    'session_id': session_id,
                    'lesson_num': str(lesson_num),
                    'segments': str(len(script)),
                    'duration_ms': str(total_duration_ms)
                }
            )
            logger.info(f"Uploaded audio to s3://{self.bucket}/{s3_key}")

        except ClientError as e:
            logger.error(f"S3 upload failed: {e}")
            # Fall back to local storage
            local_path = os.path.join(
                self.local_storage,
                f"{session_id}_lesson_{lesson_num}.mp3"
            )
            with open(local_path, 'wb') as f:
                f.write(combined_audio)
            logger.info(f"Saved audio locally: {local_path}")

            return {
                'url': f'file://{local_path}',
                'duration_seconds': total_duration_ms // 1000,
                'segment_count': len(script),
                'storage': 'local'
            }

        # Generate presigned URL
        presigned_url = self.get_presigned_url(session_id, lesson_num)

        return {
            'url': presigned_url,
            'duration_seconds': total_duration_ms // 1000,
            'segment_count': len(script),
            's3_key': s3_key,
            'storage': 's3'
        }

    def get_presigned_url(
        self,
        session_id: str,
        lesson_num: int,
        expiration: int = 3600
    ) -> str:
        """
        Generate a presigned URL for audio access.

        Args:
            session_id: Session identifier
            lesson_num: Lesson number
            expiration: URL expiration in seconds

        Returns:
            Presigned URL string
        """
        if not self._aws_available:
            return f"http://localhost:8000/mock-audio/{session_id}/{lesson_num}"

        s3_key = f"lessons/{session_id}/lesson_{lesson_num}.mp3"

        try:
            url = self.s3.generate_presigned_url(
                'get_object',
                Params={
                    'Bucket': self.bucket,
                    'Key': s3_key
                },
                ExpiresIn=expiration
            )
            return url
        except ClientError as e:
            logger.error(f"Failed to generate presigned URL: {e}")
            raise

    def _generate_silence(self, duration_ms: int) -> bytes:
        """
        Generate silent MP3 audio.

        For simplicity, we use Polly with an empty SSML break.

        Args:
            duration_ms: Duration in milliseconds

        Returns:
            Silent audio bytes
        """
        if not self._aws_available or duration_ms < 100:
            return b''

        try:
            ssml = f'<speak><break time="{duration_ms}ms"/></speak>'
            response = self.polly.synthesize_speech(
                Engine='neural',
                LanguageCode='en-US',
                OutputFormat='mp3',
                SampleRate='24000',
                Text=ssml,
                TextType='ssml',
                VoiceId='Matthew'
            )
            return response['AudioStream'].read()
        except Exception:
            # Return empty bytes on failure
            return b''

    def _concatenate_mp3(self, audio_segments: List[bytes]) -> bytes:
        """
        Concatenate multiple MP3 segments.

        Note: Simple concatenation works for MP3 but may cause
        minor glitches. For production, use ffmpeg.

        Args:
            audio_segments: List of MP3 byte arrays

        Returns:
            Combined MP3 bytes
        """
        # Simple concatenation (works for most cases)
        combined = b''.join(segment for segment in audio_segments if segment)
        return combined

    def _mock_synthesis(
        self,
        session_id: str,
        lesson_num: int,
        script: List[Dict]
    ) -> Dict:
        """
        Generate mock response for local development without AWS.

        Args:
            session_id: Session identifier
            lesson_num: Lesson number
            script: Dialogue script

        Returns:
            Mock synthesis result
        """
        # Estimate duration based on word count
        total_words = sum(len(s.get('text', '').split()) for s in script)
        duration_seconds = max(60, int(total_words / 2.5))

        return {
            'url': f'http://localhost:8000/mock-audio/{session_id}/{lesson_num}',
            'duration_seconds': duration_seconds,
            'segment_count': len(script),
            'storage': 'mock',
            'note': 'AWS credentials not configured - returning mock data'
        }

    def list_available_voices(self) -> List[Dict]:
        """
        List available neural voices for reference.

        Returns:
            List of voice info dicts
        """
        if not self._aws_available:
            return []

        try:
            response = self.polly.describe_voices(
                Engine='neural',
                LanguageCode='en-US'
            )

            return [
                {
                    'id': voice['Id'],
                    'name': voice['Name'],
                    'gender': voice['Gender'],
                    'language': voice['LanguageName']
                }
                for voice in response.get('Voices', [])
            ]
        except ClientError as e:
            logger.error(f"Failed to list voices: {e}")
            return []


# =============================================================================
# Demo/Testing
# =============================================================================

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    synthesizer = AudioSynthesizer()

    if synthesizer.check_health():
        print("✓ AWS Polly is available")

        # List available voices
        voices = synthesizer.list_available_voices()
        print(f"\nAvailable neural voices: {len(voices)}")
        for voice in voices[:5]:
            print(f"  - {voice['id']}: {voice['name']} ({voice['gender']})")

        # Test single segment
        print("\nTesting segment synthesis...")
        audio, duration = synthesizer.synthesize_segment(
            text="Welcome to Tech Explained! I'm Alex, and today we're diving into something really cool.",
            speaker='alex',
            segment_type='intro'
        )
        print(f"✓ Generated {len(audio)} bytes, ~{duration}ms")

    else:
        print("✗ AWS Polly is not available")
        print("  Configure AWS credentials to enable audio synthesis")
