#!/bin/bash

# Comedy Clipper - Automatic speaker diarization and clipping
# Usage: ./clip_comedy.sh <video_file> [options]

set -e

# Default parameters
MIN_DURATION=""   # No minimum by default - output all detected segments
MAX_GAP=120       # 2 minutes
WINDOW_SIZE=5.0   # 5 seconds
MIN_CLUSTERS=2    # Auto-detect by default
MAX_CLUSTERS=10
OUTPUT_DIR=""
TRANSCRIPT=false
WHISPER_MODEL="base"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Help message
show_help() {
    echo "Usage: $0 <video_file> [options]"
    echo ""
    echo "Options:"
    echo "  -m, --min-duration SECONDS   Minimum duration for a set (default: none, outputs all)"
    echo "  -g, --max-gap SECONDS        Maximum gap to merge segments (default: 120 = 2 min)"
    echo "  -w, --window-size SECONDS    Analysis window size (default: 5.0)"
    echo "  -s, --min-speakers NUM       Minimum number of speakers (default: 2)"
    echo "  -o, --output DIR             Output directory for clips"
    echo "  -t, --transcript             Generate transcript with speaker markers"
    echo "  --whisper-model MODEL        Whisper model (tiny/base/small/medium/large, default: base)"
    echo "  -h, --help                   Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0 video.mp4                                    # Output all detected segments"
    echo "  $0 video.mp4 -t                                 # With transcript"
    echo "  $0 video.mp4 -m 180 -g 60                       # Only 3min+ sets, 1-min gap"
    echo "  $0 video.mp4 -s 3 -o my_clips                   # Force 3 speakers"
    echo "  $0 video.mp4 -s 3 -t                            # 3 speakers with transcript"
    exit 0
}

# Parse arguments
if [ $# -eq 0 ]; then
    echo -e "${RED}Error: No video file specified${NC}"
    show_help
fi

VIDEO_FILE=""

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -h|--help)
            show_help
            ;;
        -m|--min-duration)
            MIN_DURATION="$2"
            shift 2
            ;;
        -g|--max-gap)
            MAX_GAP="$2"
            shift 2
            ;;
        -w|--window-size)
            WINDOW_SIZE="$2"
            shift 2
            ;;
        -s|--min-speakers)
            MIN_CLUSTERS="$2"
            shift 2
            ;;
        -o|--output)
            OUTPUT_DIR="$2"
            shift 2
            ;;
        -t|--transcript)
            TRANSCRIPT=true
            shift
            ;;
        --whisper-model)
            WHISPER_MODEL="$2"
            shift 2
            ;;
        *)
            if [ -z "$VIDEO_FILE" ]; then
                VIDEO_FILE="$1"
            else
                echo -e "${RED}Error: Unknown option: $1${NC}"
                show_help
            fi
            shift
            ;;
    esac
done

# Check if video file exists
if [ ! -f "$VIDEO_FILE" ]; then
    echo -e "${RED}Error: Video file not found: $VIDEO_FILE${NC}"
    exit 1
fi

# Activate virtual environment if it exists
if [ -d "venv" ]; then
    echo -e "${GREEN}Activating virtual environment...${NC}"
    source venv/bin/activate
fi

# Build command
CMD="python clipper_speaker.py \"$VIDEO_FILE\" -g $MAX_GAP -w $WINDOW_SIZE --min-clusters $MIN_CLUSTERS --max-clusters $MAX_CLUSTERS"

if [ -n "$MIN_DURATION" ]; then
    CMD="$CMD -m $MIN_DURATION"
fi

if [ -n "$OUTPUT_DIR" ]; then
    CMD="$CMD -o \"$OUTPUT_DIR\""
fi

if [ "$TRANSCRIPT" = true ]; then
    CMD="$CMD -t --whisper-model $WHISPER_MODEL"
fi

# Show configuration
echo -e "${YELLOW}===========================================${NC}"
echo -e "${GREEN}Comedy Clipper - Speaker Diarization${NC}"
echo -e "${YELLOW}===========================================${NC}"
echo "Video file:      $VIDEO_FILE"
if [ -n "$MIN_DURATION" ]; then
    echo "Min duration:    ${MIN_DURATION}s ($(echo "scale=1; $MIN_DURATION/60" | bc) min)"
else
    echo "Min duration:    All segments (no filter)"
fi
echo "Max gap:         ${MAX_GAP}s ($(echo "scale=1; $MAX_GAP/60" | bc) min)"
echo "Window size:     ${WINDOW_SIZE}s"
echo "Min speakers:    $MIN_CLUSTERS"
echo "Max speakers:    $MAX_CLUSTERS"
if [ "$TRANSCRIPT" = true ]; then
    echo "Transcript:      Enabled (model: $WHISPER_MODEL)"
fi
if [ -n "$OUTPUT_DIR" ]; then
    echo "Output dir:      $OUTPUT_DIR"
fi
echo -e "${YELLOW}===========================================${NC}"
echo ""

# Run the clipper
eval $CMD

echo -e "${GREEN}Done!${NC}"
