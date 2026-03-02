"""
Retry manager for copyright resolution attempts.

Manages the iterative process of remix generation, testing, and parameter adjustment.
"""

import time
from typing import Dict, List, Any, Optional, Callable
from datetime import datetime

try:
    from utils.logger import logger
    from utils.metadata_tracker import tracker
    from utils.config_loader import config
except ImportError:
    from utils.logger import logger
    from utils.metadata_tracker import tracker
    from utils.config_loader import config


class RetryManager:
    """Manages retry logic for copyright-free remix generation."""

    def __init__(self):
        """Initialize retry manager."""
        pass

    def calculate_attempt_parameters(
        self,
        attempt: int,
        channel_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Calculate parameters for a remix attempt.

        Args:
            attempt: Attempt number (1-based)
            channel_id: YouTube channel ID for channel-specific settings

        Returns:
            Dictionary containing attempt parameters
        """
        # Get channel preferences
        channel_settings = {}
        if channel_id:
            channel_settings = config.get_channel_settings(channel_id)

        # Base parameters from channel settings or defaults
        base_pitch = channel_settings.get('preferred_pitch', 2)
        base_tempo = channel_settings.get('preferred_tempo', 1.05)

        # Calculate incremental adjustments
        # Attempt 1: Small changes
        # Attempt 2-3: Medium changes
        # Attempt 4+: Larger changes

        if attempt == 1:
            pitch_shift = base_pitch
            tempo_multiplier = base_tempo
        elif attempt <= 3:
            pitch_shift = base_pitch + (attempt - 1)
            tempo_multiplier = base_tempo + (attempt - 1) * 0.02
        else:
            # More aggressive changes for later attempts
            pitch_shift = base_pitch + (attempt - 1) * 2
            tempo_multiplier = base_tempo + (attempt - 1) * 0.05

        # Ensure within bounds
        pitch_shift = max(config.min_pitch_shift, min(config.max_pitch_shift, pitch_shift))
        tempo_multiplier = max(config.min_tempo_multiplier, min(config.max_tempo_multiplier, tempo_multiplier))

        parameters = {
            'attempt': attempt,
            'pitch_shift': pitch_shift,
            'tempo_multiplier': tempo_multiplier,
            'channel_settings': channel_settings
        }

        logger.info(
            f"Calculated attempt parameters",
            **parameters
        )

        return parameters

    def should_retry(self, attempt: int, copyright_status: Dict[str, Any]) -> Dict[str, Any]:
        """
        Determine if another attempt should be made.

        Args:
            attempt: Current attempt number
            copyright_status: Copyright check results

        Returns:
            Dictionary with decision and reasoning
        """
        max_attempts = config.max_remix_attempts

        # Check if we've exceeded max attempts
        if attempt >= max_attempts:
            return {
                'should_retry': False,
                'reason': 'max_attempts_exceeded',
                'max_attempts': max_attempts
            }

        # Check copyright status
        has_copyright = copyright_status.get('has_copyright', False)

        if not has_copyright:
            return {
                'should_retry': False,
                'reason': 'no_copyright_detected',
                'safe': True
            }

        # Evaluate risk level
        claims = copyright_status.get('claims', [])
        max_match = 0
        for claim in claims:
            match_percent = claim.get('matchPercent', 0)
            max_match = max(max_match, match_percent)

        # Decision logic based on match percentage
        if max_match >= config.copyright_match_threshold:
            # High risk - definitely retry
            return {
                'should_retry': True,
                'reason': 'high_copyright_risk',
                'match_percent': max_match,
                'threshold': config.copyright_match_threshold
            }
        elif max_match >= config.safe_match_threshold:
            # Medium risk - retry but with different approach
            return {
                'should_retry': True,
                'reason': 'medium_copyright_risk',
                'match_percent': max_match,
                'threshold': config.safe_match_threshold
            }
        else:
            # Low risk - could proceed but we'll retry for safety
            return {
                'should_retry': True,
                'reason': 'low_risk_retry_for_safety',
                'match_percent': max_match
            }

    def execute_retry_loop(
        self,
        song_name: str,
        channel_style_id: str,
        remix_function: Callable,
        copyright_check_function: Callable,
        channel_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Execute the complete retry loop for copyright resolution.

        Args:
            song_name: Name of the song being remixed
            channel_style_id: Style ID to use for remixing
            remix_function: Function to generate remix (should accept attempt params)
            copyright_check_function: Function to check copyright
            channel_id: YouTube channel ID

        Returns:
            Final result dictionary
        """
        start_time = time.time()
        attempts = []

        logger.info(
            f"Starting retry loop for copyright resolution",
            song_name=song_name,
            channel_style_id=channel_style_id,
            channel_id=channel_id
        )

        for attempt in range(1, config.max_remix_attempts + 1):
            try:
                logger.info(
                    f"Starting attempt {attempt}/{config.max_remix_attempts}",
                    song_name=song_name
                )

                # Calculate parameters for this attempt
                attempt_params = self.calculate_attempt_parameters(attempt, channel_id)

                # Generate remix
                remix_result = remix_function(
                    song_name=song_name,
                    style_id=channel_style_id,
                    **attempt_params
                )

                if remix_result.get('status') != 'success':
                    logger.error(
                        f"Remix generation failed on attempt {attempt}",
                        error=remix_result.get('error')
                    )
                    attempts.append({
                        'attempt': attempt,
                        'status': 'remix_failed',
                        'error': remix_result.get('error'),
                        **attempt_params
                    })
                    continue

                # Check copyright
                copyright_result = copyright_check_function(remix_result['remix_file'], song_name)

                if copyright_result.get('status') == 'failed':
                    logger.error(
                        f"Copyright check failed on attempt {attempt}",
                        error=copyright_result.get('error')
                    )
                    attempts.append({
                        'attempt': attempt,
                        'status': 'copyright_check_failed',
                        'error': copyright_result.get('error'),
                        **attempt_params,
                        'remix_result': remix_result
                    })
                    continue

                # Record attempt
                attempt_data = {
                    'timestamp': datetime.now().isoformat(),
                    'song_name': song_name,
                    'attempt': attempt,
                    'style': channel_style_id,
                    'remix_result': remix_result,
                    'copyright_status': copyright_result.get('copyright_status'),
                    **attempt_params
                }

                attempts.append(attempt_data)

                # Track in metadata
                tracker.track_attempt(attempt_data)

                # Check if we should retry
                retry_decision = self.should_retry(attempt, copyright_result.get('copyright_status', {}))

                logger.info(
                    f"Attempt {attempt} completed",
                    should_retry=retry_decision.get('should_retry'),
                    reason=retry_decision.get('reason'),
                    has_copyright=copyright_result.get('copyright_status', {}).get('has_copyright')
                )

                if not retry_decision.get('should_retry'):
                    # Success or final failure
                    final_result = {
                        'status': 'success' if retry_decision.get('safe', False) else 'failed',
                        'song_name': song_name,
                        'final_remix': remix_result.get('remix_file'),
                        'total_attempts': attempt,
                        'attempts': attempts,
                        'final_parameters': attempt_params,
                        'copyright_status': copyright_result.get('copyright_status'),
                        'reason': retry_decision.get('reason'),
                        'processing_time': time.time() - start_time,
                        'channel_id': channel_id,
                        'style_used': channel_style_id
                    }

                    # Save session log
                    log_path = logger.save_session_log(song_name)
                    final_result['log_file'] = log_path

                    logger.info(
                        f"Retry loop completed",
                        status=final_result['status'],
                        total_attempts=attempt,
                        processing_time=final_result['processing_time']
                    )

                    return final_result

                # Wait before next attempt
                backoff_time = config.retry_backoff
                logger.info(f"Waiting {backoff_time} seconds before next attempt")
                time.sleep(backoff_time)

            except Exception as e:
                logger.error(
                    f"Unexpected error on attempt {attempt}",
                    error=str(e)
                )
                # attempt_params may not be defined yet if error occurred early
                attempt_data = {
                    'attempt': attempt,
                    'status': 'unexpected_error',
                    'error': str(e)
                }
                if 'attempt_params' in locals():
                    attempt_data.update(attempt_params)
                attempts.append(attempt_data)

        # All attempts exhausted
        final_result = {
            'status': 'failed',
            'reason': 'max_attempts_exceeded',
            'song_name': song_name,
            'total_attempts': config.max_remix_attempts,
            'attempts': attempts,
            'processing_time': time.time() - start_time,
            'channel_id': channel_id,
            'style_used': channel_style_id
        }

        # Save session log
        log_path = logger.save_session_log(song_name)
        final_result['log_file'] = log_path

        logger.warning(
            f"Retry loop failed after {config.max_remix_attempts} attempts",
            song_name=song_name
        )

        return final_result

    def get_attempt_summary(self, attempts: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Generate summary of all attempts.

        Args:
            attempts: List of attempt data

        Returns:
            Summary statistics
        """
        if not attempts:
            return {}

        successful_attempts = []
        failed_attempts = []
        copyright_claims = []

        for attempt in attempts:
            copyright_status = attempt.get('copyright_status', {})
            if copyright_status.get('has_copyright') == False:
                successful_attempts.append(attempt)
            else:
                failed_attempts.append(attempt)

            # Collect copyright claims
            claims = copyright_status.get('claims', [])
            copyright_claims.extend(claims)

        # Find best successful attempt
        best_attempt = None
        if successful_attempts:
            best_attempt = min(successful_attempts, key=lambda x: x.get('copyright_status', {}).get('claims', [{}])[0].get('matchPercent', 100))

        # Calculate match percentages
        match_percentages = []
        for claim in copyright_claims:
            match_percent = claim.get('matchPercent')
            if match_percent is not None:
                match_percentages.append(match_percent)

        summary = {
            'total_attempts': len(attempts),
            'successful_attempts': len(successful_attempts),
            'failed_attempts': len(failed_attempts),
            'success_rate': len(successful_attempts) / len(attempts) if attempts else 0,
            'avg_match_percent': sum(match_percentages) / len(match_percentages) if match_percentages else None,
            'min_match_percent': min(match_percentages) if match_percentages else None,
            'max_match_percent': max(match_percentages) if match_percentages else None,
            'best_attempt': best_attempt.get('attempt') if best_attempt else None
        }

        return summary

    def suggest_improvements(self, attempts: List[Dict[str, Any]]) -> List[str]:
        """
        Suggest improvements based on attempt history.

        Args:
            attempts: List of attempt data

        Returns:
            List of improvement suggestions
        """
        suggestions = []

        if not attempts:
            return suggestions

        summary = self.get_attempt_summary(attempts)

        # Analyze patterns
        if summary.get('success_rate', 0) == 0:
            suggestions.append("No successful attempts - try different remix styles")
            suggestions.append("Consider more aggressive parameter changes")

        elif summary.get('success_rate', 0) < 0.5:
            suggestions.append("Low success rate - try different pitch/tempo ranges")
            suggestions.append("Consider using different remix styles")

        # Check parameter patterns
        successful_params = []
        failed_params = []

        for attempt in attempts:
            params = {
                'pitch_shift': attempt.get('pitch_shift'),
                'tempo_multiplier': attempt.get('tempo_multiplier')
            }

            copyright_status = attempt.get('copyright_status', {})
            if copyright_status.get('has_copyright') == False:
                successful_params.append(params)
            else:
                failed_params.append(params)

        if successful_params:
            # Suggest parameter ranges that work
            avg_pitch = sum(p['pitch_shift'] for p in successful_params) / len(successful_params)
            avg_tempo = sum(p['tempo_multiplier'] for p in successful_params) / len(successful_params)

            suggestions.append(f"Successful parameters: pitch ~{avg_pitch:.1f}, tempo ~{avg_tempo:.2f}")

        if len(attempts) >= 5:
            suggestions.append("Consider manual review after 5+ failed attempts")

        return suggestions


# Global retry manager instance
retry_manager = RetryManager()
