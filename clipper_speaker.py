#!/usr/bin/env python3
"""
Comedy Clipper - True speaker diarization using voice embeddings
Identifies different comedians by analyzing voice characteristics (not pauses)
"""

import os
import sys
import argparse
from pathlib import Path
from typing import List, Tuple, Dict
import subprocess
import numpy as np
from resemblyzer import preprocess_wav, VoiceEncoder
from spectralcluster import SpectralClusterer
import librosa
import whisper


class SpeakerDiarizationClipper:
    """Clipper using voice embeddings for true speaker identification"""

    def __init__(self):
        print("Loading voice encoder model...")
        self.encoder = VoiceEncoder()
        print("Model loaded!")

    def extract_audio_wav(self, video_path: str) -> str:
        """Extract audio as WAV file for processing."""
        audio_path = str(Path(video_path).with_suffix('.wav'))

        if not os.path.exists(audio_path):
            print(f"Extracting audio from {video_path}...")
            cmd = [
                'ffmpeg', '-y',
                '-i', video_path,
                '-ac', '1',  # Mono
                '-ar', '16000',  # 16kHz
                audio_path
            ]
            subprocess.run(cmd, capture_output=True)

        return audio_path

    def diarize_speakers(self, audio_path: str, window_size: float = 1.5,
                         min_clusters: int = 2, max_clusters: int = 10) -> List[Tuple[float, float, int]]:
        """
        Perform speaker diarization on audio.

        Args:
            audio_path: Path to WAV audio file
            window_size: Size of analysis window in seconds
            min_clusters: Minimum number of speakers to detect
            max_clusters: Maximum number of speakers to detect

        Returns:
            List of (start, end, speaker_id) tuples
        """
        print(f"Analyzing audio for speaker diarization...")
        print("This may take a few minutes for long videos...")

        # Load and preprocess audio
        wav = preprocess_wav(audio_path)

        # Generate embeddings for windows
        print("Generating voice embeddings...")
        segment_duration = int(window_size * 16000)  # Convert to samples

        embeddings = []
        timestamps = []

        for i in range(0, len(wav) - segment_duration, segment_duration):
            segment = wav[i:i + segment_duration]
            if len(segment) == segment_duration:
                embedding = self.encoder.embed_utterance(segment)
                embeddings.append(embedding)
                timestamps.append(i / 16000)  # Convert to seconds

        embeddings = np.array(embeddings)
        print(f"Generated {len(embeddings)} embeddings")

        # Cluster embeddings to identify speakers
        print("Clustering speakers...")
        clusterer = SpectralClusterer(
            min_clusters=min_clusters,
            max_clusters=max_clusters
        )

        labels = clusterer.predict(embeddings)

        # Convert to segments
        segments = []
        current_speaker = labels[0]
        current_start = timestamps[0]

        for i in range(1, len(labels)):
            if labels[i] != current_speaker:
                # Speaker changed
                segments.append((current_start, timestamps[i], int(current_speaker)))
                current_speaker = labels[i]
                current_start = timestamps[i]

        # Add final segment
        segments.append((current_start, timestamps[-1] + window_size, int(current_speaker)))

        num_speakers = len(set(labels))
        print(f"Detected {num_speakers} unique speakers")
        print(f"Created {len(segments)} initial segments")

        return segments

    def merge_speaker_segments(self, segments: List[Tuple[float, float, int]],
                               min_duration: float = 0.0,
                               max_gap: float = 10.0) -> List[Tuple[float, float, int]]:
        """
        Merge consecutive segments from the same speaker.

        Args:
            segments: List of (start, end, speaker_id) tuples
            min_duration: Minimum duration for a set in seconds (default 0 = no filter)
            max_gap: Maximum gap to merge segments (default 10s)

        Returns:
            List of merged (start, end, speaker_id) tuples
        """
        if not segments:
            return []

        merged = []
        current_start, current_end, current_speaker = segments[0]

        for start, end, speaker in segments[1:]:
            gap = start - current_end

            if speaker == current_speaker and gap <= max_gap:
                # Same speaker, merge
                current_end = end
            else:
                # Different speaker or too long gap
                duration = current_end - current_start
                if min_duration == 0 or duration >= min_duration:
                    merged.append((current_start, current_end, current_speaker))

                current_start = start
                current_end = end
                current_speaker = speaker

        # Don't forget last segment
        duration = current_end - current_start
        if min_duration == 0 or duration >= min_duration:
            merged.append((current_start, current_end, current_speaker))

        return merged

    def clip_video_ffmpeg(self, video_path: str, start: float, end: float, output_path: str):
        """Clip video using ffmpeg."""
        duration = end - start

        cmd = [
            'ffmpeg', '-y',
            '-ss', str(start),
            '-i', video_path,
            '-t', str(duration),
            '-c:v', 'libx264',
            '-c:a', 'aac',
            '-preset', 'fast',
            output_path
        ]

        subprocess.run(cmd, capture_output=True)

    def clip_video(self, video_path: str, speaker_segments: List[Tuple[float, float, int]],
                   output_dir: str = None):
        """Clip video based on speaker segments."""
        if output_dir is None:
            output_dir = Path(video_path).parent
        else:
            output_dir = Path(output_dir)
            output_dir.mkdir(parents=True, exist_ok=True)

        video_name = Path(video_path).stem

        print(f"\nClipping {len(speaker_segments)} comedian sets...")

        for i, (start, end, speaker_id) in enumerate(speaker_segments, 1):
            duration = end - start
            minutes = int(duration / 60)
            seconds = int(duration % 60)

            output_path = output_dir / f"{video_name}_comedian{speaker_id+1}_set{i:02d}_{minutes}m{seconds}s.mp4"

            print(f"  [{i}/{len(speaker_segments)}] Speaker {speaker_id}: {start:.1f}s - {end:.1f}s ({minutes}m {seconds}s) -> {output_path.name}")

            self.clip_video_ffmpeg(video_path, start, end, str(output_path))

        print(f"\nDone! {len(speaker_segments)} clips saved to: {output_dir}")

    def generate_transcript(self, audio_path: str, segments: List[Tuple[float, float, int]],
                           output_path: str = None, model_name: str = "base"):
        """
        Generate a transcript with speaker change markers.

        Args:
            audio_path: Path to audio file
            segments: List of (start, end, speaker_id) tuples from diarization
            output_path: Path to save transcript (optional)
            model_name: Whisper model to use (tiny, base, small, medium, large)

        Returns:
            Formatted transcript string
        """
        print(f"\nGenerating transcript with speaker markers...")
        print(f"Loading Whisper model '{model_name}'...")

        # Load Whisper model
        model = whisper.load_model(model_name)

        # Transcribe audio with word-level timestamps
        print("Transcribing audio...")
        result = model.transcribe(audio_path, word_timestamps=True)

        # Create speaker timeline
        speaker_timeline = []
        for start, end, speaker_id in segments:
            speaker_timeline.append((start, end, speaker_id))

        # Sort segments by start time
        speaker_timeline.sort(key=lambda x: x[0])

        # Build transcript with speaker markers
        transcript_lines = []
        transcript_lines.append("=" * 60)
        transcript_lines.append("TRANSCRIPT WITH SPEAKER MARKERS")
        transcript_lines.append("=" * 60)
        transcript_lines.append("")

        current_speaker = None
        current_text = []

        # Process each word with timestamp
        for segment in result['segments']:
            if 'words' in segment:
                for word_info in segment['words']:
                    word_start = word_info.get('start', segment['start'])
                    word_text = word_info.get('word', '')

                    # Find which speaker is active at this timestamp
                    active_speaker = None
                    for start, end, speaker_id in speaker_timeline:
                        if start <= word_start <= end:
                            active_speaker = speaker_id
                            break

                    # If speaker changed, output previous speaker's text
                    if active_speaker != current_speaker and current_speaker is not None:
                        timestamp = self._format_timestamp(word_start)
                        speaker_text = ''.join(current_text).strip()
                        transcript_lines.append(f"[{timestamp}] [Speaker {current_speaker + 1}]")
                        transcript_lines.append(f"{speaker_text}")
                        transcript_lines.append("")
                        current_text = []

                    current_speaker = active_speaker
                    if active_speaker is not None:
                        current_text.append(word_text)
            else:
                # Fallback for segments without word timestamps
                seg_start = segment['start']
                seg_text = segment['text']

                active_speaker = None
                for start, end, speaker_id in speaker_timeline:
                    if start <= seg_start <= end:
                        active_speaker = speaker_id
                        break

                if active_speaker != current_speaker and current_speaker is not None:
                    timestamp = self._format_timestamp(seg_start)
                    speaker_text = ''.join(current_text).strip()
                    transcript_lines.append(f"[{timestamp}] [Speaker {current_speaker + 1}]")
                    transcript_lines.append(f"{speaker_text}")
                    transcript_lines.append("")
                    current_text = []

                current_speaker = active_speaker
                if active_speaker is not None:
                    current_text.append(seg_text)

        # Output final speaker's text
        if current_text and current_speaker is not None:
            transcript_lines.append(f"[Speaker {current_speaker + 1}]")
            transcript_lines.append(''.join(current_text).strip())
            transcript_lines.append("")

        transcript_lines.append("=" * 60)
        transcript_lines.append(f"Total speakers detected: {len(set(s[2] for s in speaker_timeline))}")
        transcript_lines.append("=" * 60)

        transcript = '\n'.join(transcript_lines)

        # Save to file if output path provided
        if output_path:
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(transcript)
            print(f"Transcript saved to: {output_path}")

        return transcript

    def _format_timestamp(self, seconds: float) -> str:
        """Format seconds as MM:SS timestamp"""
        minutes = int(seconds // 60)
        secs = int(seconds % 60)
        return f"{minutes:02d}:{secs:02d}"

    def process_video(self, video_path: str, output_dir: str = None,
                     min_duration: float = 0.0, max_gap: float = 10.0,
                     window_size: float = 1.5, min_clusters: int = 2,
                     max_clusters: int = 10, generate_transcript: bool = False,
                     whisper_model: str = "base"):
        """
        Complete pipeline: diarize speakers and clip sets.

        Args:
            video_path: Path to input video
            output_dir: Directory to save clips
            min_duration: Minimum duration for a set in seconds (default 0 = no filter, output all)
            max_gap: Maximum gap to merge segments (default 10s)
            window_size: Analysis window size (default 1.5s)
            min_clusters: Minimum number of speakers to detect (default 2)
            max_clusters: Maximum number of speakers to detect (default 10)
            generate_transcript: Generate transcript with speaker markers (default False)
            whisper_model: Whisper model for transcription (default "base")
        """
        # Extract audio
        audio_path = self.extract_audio_wav(video_path)

        # Perform speaker diarization
        segments = self.diarize_speakers(audio_path, window_size, min_clusters, max_clusters)

        if not segments:
            print("No speech segments detected")
            return

        # Generate transcript if requested
        if generate_transcript:
            video_name = Path(video_path).stem
            if output_dir:
                # Create output directory if it doesn't exist
                Path(output_dir).mkdir(parents=True, exist_ok=True)
                transcript_path = Path(output_dir) / f"{video_name}_transcript.txt"
            else:
                transcript_path = f"{video_name}_transcript.txt"

            self.generate_transcript(audio_path, segments, str(transcript_path), whisper_model)

        # Merge segments by speaker
        merged = self.merge_speaker_segments(segments, min_duration, max_gap)

        if not merged:
            if min_duration > 0:
                print(f"\nNo comedian sets found with minimum duration of {min_duration/60:.1f} minutes")
                print(f"Try lowering --min-duration (currently {min_duration}s = {min_duration/60:.1f}min)")
            else:
                print("\nNo segments detected after merging")
            return

        print(f"\nDetected {len(merged)} comedian sets:")
        for i, (start, end, speaker) in enumerate(merged, 1):
            duration_min = (end - start) / 60
            print(f"  {i}. Comedian {speaker}: {start:.1f}s - {end:.1f}s ({duration_min:.1f} minutes)")

        # Clip video
        self.clip_video(video_path, merged, output_dir)


def main():
    parser = argparse.ArgumentParser(
        description="Comedy clipper using true speaker diarization (identifies comedians by voice)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Basic usage (5 min minimum sets)
  python3 clipper_speaker.py standup_show.mp4

  # 3 minute minimum sets
  python3 clipper_speaker.py show.mp4 -m 180

  # 10 minute minimum sets (full sets only)
  python3 clipper_speaker.py show.mp4 -m 600

  # Save to specific directory
  python3 clipper_speaker.py show.mp4 -o comedian_sets/

How it works:
  - Analyzes voice characteristics using neural embeddings
  - Clusters similar voices to identify different speakers
  - Merges consecutive segments from same comedian
  - Outputs all detected speaker segments (optionally filter by duration)
        """
    )

    parser.add_argument('video', help='Input video file')
    parser.add_argument('-o', '--output', help='Output directory for clips')
    parser.add_argument('-m', '--min-duration', type=float, default=0.0,
                       help='Minimum duration for a set in seconds (default: 0 = output all)')
    parser.add_argument('-g', '--max-gap', type=float, default=10.0,
                       help='Maximum gap to merge segments in seconds (default: 10)')
    parser.add_argument('-w', '--window-size', type=float, default=1.5,
                       help='Analysis window size in seconds (default: 1.5)')
    parser.add_argument('--min-clusters', type=int, default=2,
                       help='Minimum number of speakers to detect (default: 2)')
    parser.add_argument('--max-clusters', type=int, default=10,
                       help='Maximum number of speakers to detect (default: 10)')
    parser.add_argument('-t', '--transcript', action='store_true',
                       help='Generate transcript with speaker markers')
    parser.add_argument('--whisper-model', type=str, default='base',
                       choices=['tiny', 'base', 'small', 'medium', 'large'],
                       help='Whisper model for transcription (default: base)')

    args = parser.parse_args()

    if not os.path.exists(args.video):
        print(f"Error: Video file not found: {args.video}")
        sys.exit(1)

    try:
        clipper = SpeakerDiarizationClipper()
        clipper.process_video(
            args.video,
            output_dir=args.output,
            min_duration=args.min_duration,
            max_gap=args.max_gap,
            window_size=args.window_size,
            min_clusters=args.min_clusters,
            max_clusters=args.max_clusters,
            generate_transcript=args.transcript,
            whisper_model=args.whisper_model
        )
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
