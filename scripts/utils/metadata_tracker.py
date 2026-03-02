"""
Metadata tracker for remix attempts and copyright detection results.

Tracks all remix attempts, parameters used, and copyright detection outcomes.
"""

import json
import os
from datetime import datetime
from typing import Dict, List, Any, Optional
from pathlib import Path


class MetadataTracker:
    """Tracks metadata for remix attempts and copyright detection."""

    def __init__(self, metadata_dir: str = "output/metadata"):
        """
        Initialize metadata tracker.

        Args:
            metadata_dir: Directory to store metadata files
        """
        self.metadata_dir = Path(metadata_dir)
        self.metadata_dir.mkdir(parents=True, exist_ok=True)

    def track_attempt(self, attempt_data: Dict[str, Any]) -> str:
        """
        Track a remix attempt.

        Args:
            attempt_data: Dictionary containing attempt information

        Returns:
            Path to saved metadata file
        """
        # Add timestamp if not present
        if 'timestamp' not in attempt_data:
            attempt_data['timestamp'] = datetime.now().isoformat()

        # Generate filename
        song_name = attempt_data.get('song_name', 'unknown')
        attempt = attempt_data.get('attempt', 1)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        safe_song_name = "".join(c for c in song_name if c.isalnum() or c in (' ', '-', '_')).rstrip()
        filename = f"attempt_{timestamp}_{safe_song_name}_att{attempt}.json"
        filepath = self.metadata_dir / filename

        # Save metadata
        with open(filepath, 'w') as f:
            json.dump(attempt_data, f, indent=2)

        return str(filepath)

    def get_attempt_history(self, song_name: str) -> List[Dict[str, Any]]:
        """
        Get attempt history for a song.

        Args:
            song_name: Song name to search for

        Returns:
            List of attempt metadata dictionaries
        """
        attempts = []

        # Search for files containing the song name
        safe_song_name = "".join(c for c in song_name if c.isalnum() or c in (' ', '-', '_')).rstrip()

        for file_path in self.metadata_dir.glob("*.json"):
            if safe_song_name in file_path.name:
                try:
                    with open(file_path, 'r') as f:
                        data = json.load(f)
                        attempts.append(data)
                except (json.JSONDecodeError, IOError) as e:
                    print(f"Error reading metadata file {file_path}: {e}")

        # Sort by timestamp
        attempts.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
        return attempts

    def find_successful_parameters(self, song_name: str) -> List[Dict[str, Any]]:
        """
        Find successful parameter combinations for a song.

        Args:
            song_name: Song name

        Returns:
            List of successful parameter sets
        """
        attempts = self.get_attempt_history(song_name)
        successful = []

        for attempt in attempts:
            copyright_status = attempt.get('copyright_status', {})
            if copyright_status.get('has_copyright') == False:
                successful.append({
                    'pitch_shift': attempt.get('pitch_shift'),
                    'tempo_multiplier': attempt.get('tempo_multiplier'),
                    'style': attempt.get('style'),
                    'match_percent': copyright_status.get('match_percent'),
                    'attempt': attempt.get('attempt')
                })

        return successful

    def analyze_patterns(self, limit: int = 100) -> Dict[str, Any]:
        """
        Analyze patterns in successful remix attempts.

        Args:
            limit: Maximum number of recent files to analyze

        Returns:
            Analysis results
        """
        all_files = list(self.metadata_dir.glob("*.json"))
        all_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)

        # Limit to recent files
        recent_files = all_files[:limit]

        analysis = {
            'total_attempts': len(recent_files),
            'successful_attempts': 0,
            'failed_attempts': 0,
            'success_rate': 0.0,
            'avg_attempts_per_song': 0.0,
            'popular_styles': {},
            'pitch_shift_distribution': {},
            'tempo_multiplier_distribution': {},
            'copyright_match_ranges': {
                '0-25': 0,
                '26-50': 0,
                '51-75': 0,
                '76-100': 0
            }
        }

        song_attempts = {}
        successful_params = []

        for file_path in recent_files:
            try:
                with open(file_path, 'r') as f:
                    data = json.load(f)

                    song_name = data.get('song_name', 'unknown')
                    if song_name not in song_attempts:
                        song_attempts[song_name] = []
                    song_attempts[song_name].append(data)

                    # Track styles
                    style = data.get('style')
                    if style:
                        analysis['popular_styles'][style] = analysis['popular_styles'].get(style, 0) + 1

                    # Track pitch shifts
                    pitch = data.get('pitch_shift')
                    if pitch is not None:
                        analysis['pitch_shift_distribution'][pitch] = analysis['pitch_shift_distribution'].get(pitch, 0) + 1

                    # Track tempo multipliers
                    tempo = data.get('tempo_multiplier')
                    if tempo is not None:
                        # Round to 2 decimal places for grouping
                        tempo_key = round(tempo, 2)
                        analysis['tempo_multiplier_distribution'][tempo_key] = analysis['tempo_multiplier_distribution'].get(tempo_key, 0) + 1

                    # Check copyright status
                    copyright_status = data.get('copyright_status', {})
                    has_copyright = copyright_status.get('has_copyright')

                    if has_copyright is False:
                        analysis['successful_attempts'] += 1
                        successful_params.append(data)

                        match_percent = copyright_status.get('match_percent', 0)
                        if match_percent <= 25:
                            analysis['copyright_match_ranges']['0-25'] += 1
                        elif match_percent <= 50:
                            analysis['copyright_match_ranges']['26-50'] += 1
                        elif match_percent <= 75:
                            analysis['copyright_match_ranges']['51-75'] += 1
                        else:
                            analysis['copyright_match_ranges']['76-100'] += 1
                    elif has_copyright is True:
                        analysis['failed_attempts'] += 1

            except (json.JSONDecodeError, IOError) as e:
                print(f"Error reading metadata file {file_path}: {e}")

        # Calculate rates
        if analysis['total_attempts'] > 0:
            analysis['success_rate'] = analysis['successful_attempts'] / analysis['total_attempts']

        if song_attempts:
            analysis['avg_attempts_per_song'] = sum(len(attempts) for attempts in song_attempts.values()) / len(song_attempts)

        return analysis

    def export_analysis_report(self, output_path: str) -> str:
        """
        Export analysis report to file.

        Args:
            output_path: Path to save the report

        Returns:
            Path to saved report
        """
        analysis = self.analyze_patterns()

        report = {
            'generated_at': datetime.now().isoformat(),
            'analysis': analysis
        }

        with open(output_path, 'w') as f:
            json.dump(report, f, indent=2)

        return output_path


# Global metadata tracker instance
tracker = MetadataTracker()
