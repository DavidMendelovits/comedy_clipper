#!/usr/bin/env python3
"""
Cache CLI - Command-line interface for cache management
"""

import sys
import json
from pathlib import Path

# Add parent directory to path to import cache_manager
sys.path.insert(0, str(Path(__file__).parent.parent))

from python_backend.core.cache_manager import CacheManager


def main():
    if len(sys.argv) < 2:
        print("Usage: cache_cli.py <command>")
        print("Commands: stats, clear, list")
        sys.exit(1)

    command = sys.argv[1]
    cache_manager = CacheManager()

    if command == "stats":
        stats = cache_manager.get_cache_stats()
        print(json.dumps(stats))

    elif command == "clear":
        success = cache_manager.clear_all()
        if success:
            print(json.dumps({"success": True}))
        else:
            print(json.dumps({"success": False, "error": "Failed to clear cache"}))
            sys.exit(1)

    elif command == "list":
        videos = cache_manager.get_cached_videos()
        print(json.dumps(videos))

    else:
        print(f"Unknown command: {command}")
        sys.exit(1)


if __name__ == "__main__":
    main()
