#!/usr/bin/env python3
"""
AI Personal Tutor - CLI Demo

A command-line demonstration of the complete pipeline:
URL → Content Extraction → Script Generation → Audio Synthesis

Usage:
    python -m cli.demo <url>
    python -m cli.demo --help

Examples:
    python -m cli.demo https://docs.python.org/3/tutorial/introduction.html
    python -m cli.demo https://www.example.com/article --lessons 2
    python -m cli.demo https://example.com/doc --output ./my-lessons
"""

import argparse
import sys
import os
import time
import json
from pathlib import Path
from typing import Optional

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from services.tutor_session import (
    TutorSessionManager, TutorSessionData, SessionStatus,
    get_manager, create_lesson_from_url
)


# =============================================================================
# Console Output Helpers
# =============================================================================

class Colors:
    """ANSI color codes for terminal output."""
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    DIM = '\033[2m'


def print_header(text: str):
    """Print a header with formatting."""
    print(f"\n{Colors.BOLD}{Colors.CYAN}{'='*60}{Colors.ENDC}")
    print(f"{Colors.BOLD}{Colors.CYAN}  {text}{Colors.ENDC}")
    print(f"{Colors.BOLD}{Colors.CYAN}{'='*60}{Colors.ENDC}\n")


def print_step(step_num: int, text: str):
    """Print a step indicator."""
    print(f"{Colors.BLUE}[Step {step_num}]{Colors.ENDC} {text}")


def print_success(text: str):
    """Print success message."""
    print(f"{Colors.GREEN}✓{Colors.ENDC} {text}")


def print_error(text: str):
    """Print error message."""
    print(f"{Colors.RED}✗ Error:{Colors.ENDC} {text}")


def print_info(text: str):
    """Print info message."""
    print(f"{Colors.DIM}  {text}{Colors.ENDC}")


def print_progress(message: str, done: bool = False):
    """Print progress indicator."""
    if done:
        print(f"\r{Colors.GREEN}✓{Colors.ENDC} {message}                    ")
    else:
        print(f"\r{Colors.YELLOW}⟳{Colors.ENDC} {message}...", end='', flush=True)


# =============================================================================
# Demo Functions
# =============================================================================

def display_session_info(session: TutorSessionData):
    """Display session information."""
    print(f"\n{Colors.BOLD}Session Information:{Colors.ENDC}")
    print(f"  Session ID: {session.session_id}")
    print(f"  URL: {session.url}")
    print(f"  Status: {session.status.value}")
    print(f"  Created: {session.created_at}")

    if session.content_title:
        print(f"\n{Colors.BOLD}Content:{Colors.ENDC}")
        print(f"  Title: {session.content_title}")

    if session.lessons:
        print(f"\n{Colors.BOLD}Lessons ({len(session.lessons)}):{Colors.ENDC}")
        for num, lesson in sorted(session.lessons.items()):
            status = "✓ Generated" if lesson.generated else "○ Pending"
            print(f"  {num}. {lesson.title} [{status}]")
            print(f"     {Colors.DIM}{lesson.description}{Colors.ENDC}")


def display_lesson_details(lesson, transcript: Optional[str] = None):
    """Display detailed lesson information."""
    print(f"\n{Colors.BOLD}{Colors.CYAN}Lesson {lesson.lesson_number}: {lesson.title}{Colors.ENDC}")
    print(f"  Description: {lesson.description}")
    print(f"  Topics: {', '.join(lesson.topics)}")
    print(f"  Estimated Duration: {lesson.estimated_duration_minutes} minutes")

    if lesson.generated:
        print(f"  Status: {Colors.GREEN}Generated{Colors.ENDC}")
        if lesson.audio_path:
            print(f"  Audio: {lesson.audio_path}")

    if transcript:
        print(f"\n{Colors.BOLD}Transcript Preview:{Colors.ENDC}")
        # Show first 500 characters
        preview = transcript[:500] + "..." if len(transcript) > 500 else transcript
        for line in preview.split('\n'):
            if line.strip():
                print(f"  {line}")


def run_demo(
    url: str,
    num_lessons: int = 3,
    output_dir: Optional[str] = None,
    generate_audio: bool = True,
    verbose: bool = False
):
    """
    Run the complete demo pipeline.

    Args:
        url: URL to extract content from
        num_lessons: Number of lessons to generate
        output_dir: Directory to save outputs
        generate_audio: Whether to generate audio
        verbose: Enable verbose output
    """
    print_header("AI Personal Tutor Demo")

    print(f"Source URL: {Colors.CYAN}{url}{Colors.ENDC}")
    print(f"Lessons to generate: {num_lessons}")
    if output_dir:
        print(f"Output directory: {output_dir}")
    print()

    # Initialize manager
    print_step(1, "Initializing session manager...")
    try:
        manager = TutorSessionManager()
        print_success("Session manager initialized")
    except Exception as e:
        print_error(f"Failed to initialize manager: {e}")
        return 1

    # Check service health
    if verbose:
        print_info("Checking service health...")
        health = manager.check_health()
        for service, status in health.items():
            if service != 'session_count':
                icon = "✓" if status else "✗"
                color = Colors.GREEN if status else Colors.RED
                print_info(f"  {service}: {color}{icon}{Colors.ENDC}")

    # Create session (extract and process content)
    print_step(2, "Creating session and extracting content...")
    start_time = time.time()

    try:
        session = manager.create_session(url)
        elapsed = time.time() - start_time
        print_success(f"Session created in {elapsed:.1f}s")
        display_session_info(session)
    except ValueError as e:
        print_error(str(e))
        return 1
    except Exception as e:
        print_error(f"Failed to create session: {e}")
        if verbose:
            import traceback
            traceback.print_exc()
        return 1

    # Generate lessons
    print_step(3, "Generating lessons...")

    lessons_to_generate = min(num_lessons, len(session.lessons))

    for lesson_num in range(1, lessons_to_generate + 1):
        lesson = session.lessons.get(lesson_num)
        if not lesson:
            print_error(f"Lesson {lesson_num} not found")
            continue

        print(f"\n  Generating Lesson {lesson_num}: {lesson.title}")
        print_progress(f"Creating script and audio for lesson {lesson_num}")

        start_time = time.time()
        try:
            result = manager.generate_lesson(
                session.session_id,
                lesson_num,
                skip_audio=not generate_audio
            )
            elapsed = time.time() - start_time
            print_progress(f"Lesson {lesson_num} complete ({elapsed:.1f}s)", done=True)

            if verbose and result.get('script'):
                print_info(f"  Script generated with {result['script'].total_turns} turns")
            if result.get('audio'):
                print_info(f"  Audio: {result['audio'].get('audio_path', 'Generated')}")
        except Exception as e:
            print()
            print_error(f"Failed to generate lesson {lesson_num}: {e}")
            if verbose:
                import traceback
                traceback.print_exc()

    # Display final results
    print_step(4, "Processing complete!")

    # Refresh session data
    session = manager.get_session(session.session_id)

    print(f"\n{Colors.BOLD}{Colors.GREEN}Summary:{Colors.ENDC}")
    print(f"  Total lessons: {len(session.lessons)}")
    generated = sum(1 for l in session.lessons.values() if l.generated)
    print(f"  Generated: {generated}")
    print(f"  Session ID: {session.session_id}")

    # Save outputs if output_dir specified
    if output_dir:
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        # Save session info
        session_file = output_path / f"session_{session.session_id[:8]}.json"
        with open(session_file, 'w') as f:
            json.dump({
                'session_id': session.session_id,
                'url': session.url,
                'status': session.status.value,
                'lessons': [
                    {
                        'number': l.lesson_number,
                        'title': l.title,
                        'description': l.description,
                        'generated': l.generated,
                        'audio_path': l.audio_path
                    }
                    for l in sorted(session.lessons.values(), key=lambda x: x.lesson_number)
                ]
            }, f, indent=2)
        print(f"\n  Session saved to: {session_file}")

        # Save transcripts
        for lesson_num, lesson in session.lessons.items():
            if lesson.generated:
                try:
                    transcript = manager.get_transcript(session.session_id, lesson_num)
                    transcript_file = output_path / f"lesson_{lesson_num}_transcript.md"
                    with open(transcript_file, 'w') as f:
                        f.write(f"# {lesson.title}\n\n")
                        f.write(transcript)
                    print(f"  Transcript saved: {transcript_file}")
                except Exception as e:
                    print_info(f"  Could not save transcript for lesson {lesson_num}: {e}")

    # Interactive transcript viewing
    print(f"\n{Colors.BOLD}View transcripts:{Colors.ENDC}")
    for lesson_num, lesson in sorted(session.lessons.items()):
        if lesson.generated:
            print(f"  Lesson {lesson_num}: Use session ID '{session.session_id}' with API")

    print(f"\n{Colors.DIM}API Usage:{Colors.ENDC}")
    print(f"  GET /api/v2/sessions/{session.session_id}/lessons/1/transcript")
    print(f"  GET /api/v2/sessions/{session.session_id}/lessons/1/audio")

    return 0


def interactive_mode():
    """Run in interactive mode."""
    print_header("AI Personal Tutor - Interactive Mode")

    manager = TutorSessionManager()
    current_session = None

    while True:
        print(f"\n{Colors.BOLD}Commands:{Colors.ENDC}")
        print("  1. Create new session from URL")
        print("  2. List all sessions")
        print("  3. Generate lesson")
        print("  4. View transcript")
        print("  5. Check health")
        print("  0. Exit")

        try:
            choice = input(f"\n{Colors.CYAN}Enter choice: {Colors.ENDC}").strip()
        except (KeyboardInterrupt, EOFError):
            print("\n\nGoodbye!")
            break

        if choice == '0':
            print("Goodbye!")
            break

        elif choice == '1':
            url = input("Enter URL: ").strip()
            if url:
                try:
                    print_progress("Creating session")
                    current_session = manager.create_session(url)
                    print_progress("Session created", done=True)
                    display_session_info(current_session)
                except Exception as e:
                    print_error(str(e))

        elif choice == '2':
            sessions = manager.list_sessions()
            if sessions:
                print(f"\n{Colors.BOLD}Sessions:{Colors.ENDC}")
                for s in sessions:
                    print(f"  {s.session_id[:8]}... - {s.url[:50]} [{s.status.value}]")
            else:
                print("  No sessions found")

        elif choice == '3':
            if not current_session:
                session_id = input("Enter session ID: ").strip()
                current_session = manager.get_session(session_id)
                if not current_session:
                    print_error("Session not found")
                    continue

            lesson_num = input("Enter lesson number: ").strip()
            try:
                lesson_num = int(lesson_num)
                print_progress(f"Generating lesson {lesson_num}")
                result = manager.generate_lesson(current_session.session_id, lesson_num)
                print_progress("Lesson generated", done=True)
                print_success(f"Audio: {result.get('audio', {}).get('audio_path', 'Generated')}")
            except Exception as e:
                print_error(str(e))

        elif choice == '4':
            if not current_session:
                session_id = input("Enter session ID: ").strip()
                current_session = manager.get_session(session_id)
                if not current_session:
                    print_error("Session not found")
                    continue

            lesson_num = input("Enter lesson number: ").strip()
            try:
                lesson_num = int(lesson_num)
                transcript = manager.get_transcript(current_session.session_id, lesson_num)
                print(f"\n{Colors.BOLD}Transcript:{Colors.ENDC}\n")
                print(transcript)
            except Exception as e:
                print_error(str(e))

        elif choice == '5':
            health = manager.check_health()
            print(f"\n{Colors.BOLD}Health Status:{Colors.ENDC}")
            for service, status in health.items():
                if service == 'session_count':
                    print(f"  Active sessions: {status}")
                else:
                    icon = "✓" if status else "✗"
                    color = Colors.GREEN if status else Colors.RED
                    print(f"  {service}: {color}{icon}{Colors.ENDC}")


# =============================================================================
# Main Entry Point
# =============================================================================

def main():
    """Main entry point for CLI demo."""
    parser = argparse.ArgumentParser(
        description='AI Personal Tutor - CLI Demo',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s https://docs.python.org/3/tutorial/introduction.html
  %(prog)s https://example.com/article --lessons 2
  %(prog)s https://example.com/doc --output ./my-lessons --verbose
  %(prog)s --interactive
        """
    )

    parser.add_argument(
        'url',
        nargs='?',
        help='URL to extract content from'
    )

    parser.add_argument(
        '-l', '--lessons',
        type=int,
        default=3,
        help='Number of lessons to generate (default: 3)'
    )

    parser.add_argument(
        '-o', '--output',
        type=str,
        default=None,
        help='Directory to save output files'
    )

    parser.add_argument(
        '--no-audio',
        action='store_true',
        help='Skip audio generation (script only)'
    )

    parser.add_argument(
        '-v', '--verbose',
        action='store_true',
        help='Enable verbose output'
    )

    parser.add_argument(
        '-i', '--interactive',
        action='store_true',
        help='Run in interactive mode'
    )

    args = parser.parse_args()

    # Check for interactive mode
    if args.interactive:
        return interactive_mode()

    # Require URL for non-interactive mode
    if not args.url:
        parser.print_help()
        print(f"\n{Colors.RED}Error: URL is required (or use --interactive){Colors.ENDC}")
        return 1

    # Run demo
    return run_demo(
        url=args.url,
        num_lessons=args.lessons,
        output_dir=args.output,
        generate_audio=not args.no_audio,
        verbose=args.verbose
    )


if __name__ == '__main__':
    sys.exit(main() or 0)
