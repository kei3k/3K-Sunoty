# Suno Remix Tool with Copyright Detection

Advanced remix generation system that creates copyright-free remixes through iterative audio parameter adjustment and YouTube Content ID testing.

## Overview

This tool is part of a 6-step YouTube automation pipeline. It takes trending songs as input, automatically remixes them to avoid copyright strikes, manages multiple remix style templates, tests uploads against YouTube's Content ID, and returns final copyright-cleared remix files.

## Features

- **Audio Parameter Modification**: Pitch and tempo shifting using librosa
- **Suno API Integration**: Generate remixes with various styles
- **YouTube Copyright Detection**: Automated Content ID checking
- **Iterative Retry Loop**: Automatically adjusts parameters if copyright detected
- **Multiple Style Templates**: Lo-fi, EDM, Jazz, Acoustic styles
- **Comprehensive Logging**: Detailed logs and metadata tracking
- **Batch Processing**: Process multiple songs at once

## Installation

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Install FFmpeg (required for video conversion):
```bash
# Ubuntu/Debian
sudo apt install ffmpeg

# macOS
brew install ffmpeg

# Windows
# Download from https://ffmpeg.org/download.html
```

3. **CRITICAL: Get Suno Cookie**
   - Open https://suno.com in your browser
   - Login to your account
   - Press F12 to open DevTools
   - Go to Application → Cookies → suno.com
   - Copy the session cookies (especially `_suno_session` and `__Secure-account-id`)

4. Configure environment variables in `.env`:
```bash
# Suno Configuration (Cookie-based)
SUNO_COOKIE=__Secure-account-id=your_account_id_here; _suno_session=your_session_cookie_here

# YouTube Configuration
YOUTUBE_API_KEY=your_youtube_api_key_here
YOUTUBE_CHANNEL_ID=UCyour_channel_id_here

# Optional settings
MAX_REMIX_ATTEMPTS=10
COPYRIGHT_MATCH_THRESHOLD=75
SAFE_MATCH_THRESHOLD=50
```

## Configuration

### Style Templates (`scripts/configs/remix_styles.json`)

Define remix styles with prompts and parameters:

```json
{
  "styles": [
    {
      "id": "lofi_chill",
      "name": "Lo-fi Chill",
      "prompt_template": "Create a lo-fi chill remix of [SONG_NAME]. Keep the melody but make it relaxing, 80 BPM, with ambient vibes.",
      "parameters": {
        "duration": "180s",
        "model": "chirp-v3"
      }
    }
  ]
}
```

### Channel Settings (`scripts/configs/remix_settings.json`)

Configure per-channel preferences:

```json
{
  "default_style": "lofi_chill",
  "channels": {
    "UCxxxxxx": {
      "style": "edm_remix",
      "preferred_tempo": 1.15,
      "preferred_pitch": 3
    }
  }
}
```

## Usage

### Single Song Processing

```bash
python scripts/2_remix_with_suno_advanced.py "Song Name - Artist"
```

### With Channel ID

```bash
python scripts/2_remix_with_suno_advanced.py "Song Name - Artist" --channel-id UCxxxxxx
```

### With Specific Style

```bash
python scripts/2_remix_with_suno_advanced.py "Song Name - Artist" --style-id edm_remix
```

### Batch Processing

```bash
# Create a file with one song per line
echo -e "Song 1\nSong 2\nSong 3" > songs.txt

python scripts/2_remix_with_suno_advanced.py dummy --batch-file songs.txt
```

## Workflow

1. **Input**: Song name (or batch file)
2. **Style Selection**: Choose remix style based on channel preferences
3. **Parameter Calculation**: Set initial pitch/tempo adjustments
4. **Audio Processing**: Apply modifications (if using original audio)
5. **Suno Generation**: Generate remix via Suno API
6. **Video Conversion**: Convert audio to MP4 for YouTube
7. **Copyright Check**: Upload unlisted video and check Content ID
8. **Decision**:
   - ✅ No copyright → Success
   - ❌ Copyright detected → Adjust parameters and retry
   - 🔄 Max attempts → Failure

## Output Structure

```
output/
├── music/          # Generated remix MP3 files
├── videos/         # Converted MP4 files for testing
├── logs/           # Detailed processing logs
└── metadata/       # Attempt metadata and analytics
```

## Success Criteria

- **Match Percent < 50%**: Safe to use
- **Match Percent 50-75%**: Borderline, retry recommended
- **Match Percent > 75%**: High risk, retry with different parameters

## Error Handling

The tool includes comprehensive error handling for:

- API failures and rate limits
- Network timeouts
- Invalid audio files
- YouTube upload issues
- FFmpeg conversion errors

## Logging

All operations are logged with structured JSON output including:

- Attempt parameters and results
- API responses and errors
- Copyright detection outcomes
- Processing times and performance metrics

## Testing

Run tests with:

```bash
python -m pytest tests/
```

## Production Notes

- **API Limits**: Monitor Suno and YouTube API quotas
- **Costs**: Track API usage costs
- **Performance**: Typical processing time is 5-15 minutes per song
- **Success Rate**: Expect 60-80% success rate depending on song popularity
- **Cleanup**: Test videos are automatically deleted after checking

## Troubleshooting

### Common Issues

1. **FFmpeg not found**: Install FFmpeg and ensure it's in PATH
2. **API Key errors**: Verify environment variables are set correctly
3. **Upload failures**: Check YouTube API permissions and quotas
4. **High failure rate**: Try different remix styles or parameter ranges

### Debug Mode

Enable debug logging:

```bash
export PYTHONPATH=$PYTHONPATH:$(pwd)
python -c "import logging; logging.basicConfig(level=logging.DEBUG)"
python scripts/2_remix_with_suno_advanced.py "Test Song"
```

## Contributing

1. Follow the existing code structure
2. Add comprehensive logging
3. Include error handling
4. Update documentation
5. Add tests for new features

## License

[Add your license here]
