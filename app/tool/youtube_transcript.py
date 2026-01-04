"""
YouTube Transcript Tool

This tool fetches transcripts from YouTube videos and optionally adds them to the knowledge base.
Supports automatic language detection, multiple language fallbacks, and AI-powered summarization.

Author: Enhancement #4 Implementation
Date: 2025-10-26
"""

import re
from typing import Any, Dict, List, Optional

from pydantic import Field

from app.tool.base import BaseTool, ToolResult
from app.utils.logger import logger


class YouTubeTranscriptTool(BaseTool):
    """
    Fetch YouTube video transcripts and metadata.

    This tool provides comprehensive YouTube video analysis:
    - Transcript extraction with timestamps
    - Automatic language detection
    - Video metadata (title, channel, duration, views)
    - AI-powered summarization
    - Optional knowledge base integration

    Use cases:
    - Research from educational videos
    - Extract tutorial steps
    - Build knowledge base from video content
    - Summarize long videos
    - Create study notes from lectures

    Design rationale:
    - Uses youtube-transcript-api for reliable transcript fetching
    - Supports multiple languages with automatic fallback
    - Integrates with knowledge base for RAG
    - Returns structured data for easy processing
    - Handles errors gracefully (private videos, no captions, etc.)
    """

    name: str = "youtube_transcript"
    description: str = (
        "Fetch YouTube video transcripts and metadata. "
        "Extracts transcript with timestamps, video info (title, channel, duration), "
        "and optionally generates AI summary and adds to knowledge base. "
        "Supports automatic language detection and multiple language fallbacks."
    )
    parameters: dict = Field(
        default_factory=lambda: {
            "type": "object",
            "properties": {
                "video_url": {
                    "type": "string",
                    "description": "YouTube video URL or video ID (e.g., 'https://youtube.com/watch?v=VIDEO_ID' or just 'VIDEO_ID')",
                },
                "languages": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Preferred languages for transcript (e.g., ['en', 'es']). Defaults to ['en']",
                    "default": ["en"],
                },
                "add_to_knowledge": {
                    "type": "boolean",
                    "description": "If true, add transcript to knowledge base for RAG. Defaults to false",
                    "default": False,
                },
                "generate_summary": {
                    "type": "boolean",
                    "description": "If true, generate AI-powered summary of the transcript. Defaults to true",
                    "default": True,
                },
                "include_timestamps": {
                    "type": "boolean",
                    "description": "If true, include timestamps in transcript. Defaults to true",
                    "default": True,
                },
            },
            "required": ["video_url"],
        }
    )

    def __init__(self, **data):
        """Initialize the YouTube Transcript tool."""
        super().__init__(**data)
        self.knowledge_tool = None  # Will be set if knowledge base is available

    def _extract_video_id(self, video_url: str) -> Optional[str]:
        """
        Extract video ID from various YouTube URL formats.

        Supports:
        - https://www.youtube.com/watch?v=VIDEO_ID
        - https://youtu.be/VIDEO_ID
        - https://www.youtube.com/embed/VIDEO_ID
        - Just VIDEO_ID

        Args:
            video_url: YouTube URL or video ID

        Returns:
            Video ID or None if invalid
        """
        # If it's already just a video ID (11 characters, alphanumeric + - and _)
        if re.match(r"^[a-zA-Z0-9_-]{11}$", video_url):
            return video_url

        # Extract from various URL formats
        patterns = [
            r"(?:youtube\.com/watch\?v=|youtu\.be/|youtube\.com/embed/)([a-zA-Z0-9_-]{11})",
            r"youtube\.com/watch\?.*v=([a-zA-Z0-9_-]{11})",
        ]

        for pattern in patterns:
            match = re.search(pattern, video_url)
            if match:
                return match.group(1)

        logger.warning(f"Could not extract video ID from: {video_url}")
        return None

    async def _get_video_metadata(self, video_id: str) -> Dict[str, Any]:
        """
        Get video metadata using yt-dlp (lightweight alternative to full API).

        Args:
            video_id: YouTube video ID

        Returns:
            Dict with title, channel, duration, views, etc.
        """
        try:
            import yt_dlp

            ydl_opts = {
                "quiet": True,
                "no_warnings": True,
                "extract_flat": True,
            }

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(
                    f"https://youtube.com/watch?v={video_id}", download=False
                )

                return {
                    "title": info.get("title", "Unknown"),
                    "channel": info.get("uploader", "Unknown"),
                    "duration": info.get("duration", 0),  # in seconds
                    "duration_formatted": self._format_duration(
                        info.get("duration", 0)
                    ),
                    "views": info.get("view_count", 0),
                    "upload_date": info.get("upload_date", "Unknown"),
                    "description": info.get("description", ""),
                    "thumbnail": info.get("thumbnail", ""),
                }
        except Exception as e:
            logger.warning(f"Could not fetch metadata for {video_id}: {e}")
            return {
                "title": "Unknown",
                "channel": "Unknown",
                "duration": 0,
                "duration_formatted": "0:00",
                "views": 0,
                "upload_date": "Unknown",
                "description": "",
                "thumbnail": "",
            }

    def _format_duration(self, seconds: int) -> str:
        """Format duration in seconds to HH:MM:SS or MM:SS."""
        if seconds == 0:
            return "0:00"

        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        secs = seconds % 60

        if hours > 0:
            return f"{hours}:{minutes:02d}:{secs:02d}"
        else:
            return f"{minutes}:{secs:02d}"

    async def _get_transcript(
        self,
        video_id: str,
        languages: List[str] = ["en"],
        include_timestamps: bool = True,
    ) -> Dict[str, Any]:
        """
        Fetch transcript from YouTube video.

        Args:
            video_id: YouTube video ID
            languages: List of language codes to try (in order of preference)
            include_timestamps: Whether to include timestamps

        Returns:
            Dict with transcript text, segments, and language
        """
        try:
            from youtube_transcript_api import YouTubeTranscriptApi
            from youtube_transcript_api._errors import (
                NoTranscriptFound,
                TranscriptsDisabled,
                VideoUnavailable,
            )

            # Try to get transcript in preferred languages
            try:
                transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)

                # Try each language in order
                transcript = None
                for lang in languages:
                    try:
                        transcript = transcript_list.find_transcript([lang])
                        break
                    except NoTranscriptFound:
                        continue

                # If no preferred language found, get any available
                if transcript is None:
                    transcript = transcript_list.find_generated_transcript(["en"])

                # Fetch the actual transcript
                transcript_data = transcript.fetch()
                language = transcript.language_code

            except NoTranscriptFound:
                return {
                    "success": False,
                    "error": "No transcript available for this video",
                    "transcript": "",
                    "segments": [],
                    "language": None,
                }
            except TranscriptsDisabled:
                return {
                    "success": False,
                    "error": "Transcripts are disabled for this video",
                    "transcript": "",
                    "segments": [],
                    "language": None,
                }
            except VideoUnavailable:
                return {
                    "success": False,
                    "error": "Video is unavailable (private, deleted, or restricted)",
                    "transcript": "",
                    "segments": [],
                    "language": None,
                }

            # Format transcript
            segments = []
            full_text_parts = []

            for entry in transcript_data:
                text = entry["text"].strip()
                start = entry["start"]
                duration = entry["duration"]

                if include_timestamps:
                    timestamp = self._format_duration(int(start))
                    segments.append(
                        {
                            "start": start,
                            "duration": duration,
                            "timestamp": timestamp,
                            "text": text,
                        }
                    )
                    full_text_parts.append(f"[{timestamp}] {text}")
                else:
                    segments.append({"text": text})
                    full_text_parts.append(text)

            full_transcript = "\n".join(full_text_parts)

            return {
                "success": True,
                "transcript": full_transcript,
                "segments": segments,
                "language": language,
                "segment_count": len(segments),
            }

        except ImportError:
            return {
                "success": False,
                "error": "youtube-transcript-api not installed. Run: pip install youtube-transcript-api",
                "transcript": "",
                "segments": [],
                "language": None,
            }
        except Exception as e:
            logger.error(f"Error fetching transcript: {e}")
            return {
                "success": False,
                "error": str(e),
                "transcript": "",
                "segments": [],
                "language": None,
            }

    async def _generate_summary(self, transcript: str, metadata: Dict) -> str:
        """
        Generate AI-powered summary of the transcript.

        Args:
            transcript: Full transcript text
            metadata: Video metadata

        Returns:
            Summary text
        """
        try:
            from app.llm_router import llm_router
            from app.schema import Message

            # Use the default model for summarization
            llm = llm_router.select_model("default")

            prompt = f"""Summarize this YouTube video transcript.

Video Title: {metadata['title']}
Channel: {metadata['channel']}
Duration: {metadata['duration_formatted']}

Transcript:
{transcript[:4000]}  # Limit to avoid token limits

Please provide:
1. A concise summary (2-3 sentences)
2. Key points (3-5 bullet points)
3. Main topics covered

Format your response as:
**Summary:**
[Your summary here]

**Key Points:**
- [Point 1]
- [Point 2]
...

**Topics:**
[List of main topics]
"""

            messages = [Message.user_message(prompt)]
            summary = await llm.ask(messages, stream=False)

            return summary

        except Exception as e:
            logger.warning(f"Could not generate summary: {e}")
            return "Summary generation failed. Transcript available above."

    async def _add_to_knowledge_base(
        self, transcript: str, metadata: Dict, summary: str
    ) -> Optional[str]:
        """
        Add transcript to knowledge base for RAG.

        Args:
            transcript: Full transcript
            metadata: Video metadata
            summary: Generated summary

        Returns:
            Knowledge entry ID or None if failed
        """
        try:
            # Import knowledge base tool if available
            from app.tool.knowledge_base import KnowledgeBaseTool

            if self.knowledge_tool is None:
                self.knowledge_tool = KnowledgeBaseTool()

            # Prepare content for knowledge base
            content = f"""# {metadata['title']}

**Channel:** {metadata['channel']}
**Duration:** {metadata['duration_formatted']}
**Upload Date:** {metadata['upload_date']}

## Summary
{summary}

## Full Transcript
{transcript}
"""

            # Add to knowledge base
            result = await self.knowledge_tool.execute(
                action="add",
                content=content,
                source=f"youtube:{metadata.get('video_id', 'unknown')}",
                title=metadata["title"],
                metadata={
                    "type": "youtube_video",
                    "channel": metadata["channel"],
                    "duration": metadata["duration"],
                    "url": f"https://youtube.com/watch?v={metadata.get('video_id', '')}",
                },
            )

            if result.output and "knowledge_id" in result.output:
                return result.output["knowledge_id"]

            return None

        except ImportError:
            logger.warning("Knowledge base tool not available")
            return None
        except Exception as e:
            logger.error(f"Error adding to knowledge base: {e}")
            return None

    async def execute(
        self,
        video_url: str,
        languages: List[str] = ["en"],
        add_to_knowledge: bool = False,
        generate_summary: bool = True,
        include_timestamps: bool = True,
    ) -> ToolResult:
        """
        Execute the YouTube transcript tool.

        Args:
            video_url: YouTube video URL or ID
            languages: Preferred languages for transcript
            add_to_knowledge: Whether to add to knowledge base
            generate_summary: Whether to generate AI summary
            include_timestamps: Whether to include timestamps

        Returns:
            ToolResult with transcript, metadata, and optional summary/knowledge_id
        """
        try:
            # Extract video ID
            video_id = self._extract_video_id(video_url)
            if not video_id:
                return self.error_response("Invalid YouTube URL or video ID")

            logger.info(f"Fetching transcript for video: {video_id}")

            # Get video metadata
            metadata = await self._get_video_metadata(video_id)
            metadata["video_id"] = video_id
            metadata["url"] = f"https://youtube.com/watch?v={video_id}"

            # Get transcript
            transcript_result = await self._get_transcript(
                video_id, languages, include_timestamps
            )

            if not transcript_result["success"]:
                return self.error_response(transcript_result["error"])

            # Prepare result
            result = {
                "video_id": video_id,
                "url": metadata["url"],
                "title": metadata["title"],
                "channel": metadata["channel"],
                "duration": metadata["duration_formatted"],
                "views": metadata["views"],
                "upload_date": metadata["upload_date"],
                "language": transcript_result["language"],
                "transcript": transcript_result["transcript"],
                "segment_count": transcript_result["segment_count"],
                "segments": transcript_result["segments"][
                    :10
                ],  # First 10 segments as sample
            }

            # Generate summary if requested
            if generate_summary:
                logger.info("Generating summary...")
                summary = await self._generate_summary(
                    transcript_result["transcript"], metadata
                )
                result["summary"] = summary
            else:
                summary = None

            # Add to knowledge base if requested
            if add_to_knowledge:
                logger.info("Adding to knowledge base...")
                knowledge_id = await self._add_to_knowledge_base(
                    transcript_result["transcript"],
                    metadata,
                    summary or "No summary generated",
                )
                if knowledge_id:
                    result["knowledge_id"] = knowledge_id
                    result["knowledge_status"] = "added"
                else:
                    result["knowledge_status"] = "failed"

            logger.info(f"Successfully processed video: {metadata['title']}")
            return self.success_response(result)

        except Exception as e:
            logger.error(f"Error in YouTube transcript tool: {e}")
            return self.error_response(f"Failed to process YouTube video: {str(e)}")
