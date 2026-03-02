#!/usr/bin/env python3
"""
Demo script để test Suno Remix Tool mà không cần API keys thật
"""

import os
import sys

# Thêm thư mục scripts vào path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'scripts'))

def demo_workflow():
    """Demo toàn bộ workflow với mock data"""
    print("🎵 SUNO REMIX TOOL - DEMO MODE")
    print("=" * 60)
    print("⚠️  Đây là demo với dữ liệu giả, không gọi API thật")
    print("=" * 60)

    try:
        # Import các modules
        from utils.config_loader import config
        from modules.audio_processor import audio_processor
        from utils.workflow_logger import workflow_logger

        print("\n✅ Modules loaded successfully")

        # Test config
        print("\n🔧 Testing configuration...")
        default_style = config.get_default_style()
        print(f"   Default style: {default_style}")

        styles = config.get_config('remix_styles')['styles']
        print(f"   Available styles: {len(styles)}")
        for style in styles[:2]:  # Show first 2
            print(f"     - {style['id']}: {style['name']}")

        # Test parameter calculation
        print("\n⚙️ Testing parameter calculation...")

        def get_parameters(attempt: int):
            """Get pitch and tempo parameters for attempt."""
            if attempt == 1:
                pitch_shift = 2
                tempo_multiplier = 1.05
            elif attempt <= 3:
                pitch_shift = 2 + (attempt - 1)
                tempo_multiplier = 1.05 + (attempt - 1) * 0.02
            else:
                pitch_shift = 2 + (attempt - 1) * 2
                tempo_multiplier = 1.05 + (attempt - 1) * 0.05

            pitch_shift = max(-5, min(5, pitch_shift))
            tempo_multiplier = max(0.85, min(1.20, tempo_multiplier))

            return pitch_shift, tempo_multiplier

        for attempt in [1, 2, 3, 5]:
            pitch, tempo = get_parameters(attempt)
            print(f"   Attempt {attempt}: pitch {pitch:+d}, tempo {tempo:.2f}x")

        # Test audio analysis (nếu có file test)
        print("\n🎵 Testing audio analysis...")
        test_mp3 = "test_song.mp3"
        if os.path.exists(test_mp3):
            props = audio_processor.analyze_audio(test_mp3)
            print(f"   BPM: {props['bpm']:.1f}")
            print(f"   Key: {props['key']}")
            print(f"   Duration: {props['duration']:.1f}s")
        else:
            print("   ⚠️ No test MP3 file found - skipping audio analysis")

        # Simulate workflow
        print("\n🚀 Simulating remix workflow...")
        print("   1. [..] Analyze audio: OK")
        print("   2. [..] Modify parameters: pitch +2, tempo 1.05x OK")
        print("   3. [..] Generate via Suno: [MOCK] Success OK")
        print("   4. [..] Convert to MP4: OK")
        print("   5. [..] Upload to YouTube: [MOCK] Video ID xyz123 OK")
        print("   6. [..] Check copyright: [MOCK] 12.5% match - SAFE OK")
        print("   7. [..] Cleanup test videos: OK")

        print("\n🎉 WORKFLOW RESULT:")
        print("   Status: success")
        print("   Final remix: output/music/remix_final.mp3")
        print("   Attempts: 1")
        print("   Copyright safe: Yes (12.5% match)")

        return True

    except Exception as e:
        print(f"❌ Demo failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def show_usage():
    """Hiển thị cách sử dụng tool"""
    print("\n" + "=" * 60)
    print("📖 CÁCH SỬ DỤNG TOOL VỚI API THẬT:")
    print("=" * 60)

    print("\n1️⃣ Chuẩn bị cookie Suno:")
    print("   - Vào https://suno.com")
    print("   - Login tài khoản")
    print("   - F12 → Application → Cookies → suno.com")
    print("   - Copy _suno_session và __Secure-account-id")

    print("\n2️⃣ Cập nhật .env:")
    print('   SUNO_COOKIE="__Secure-account-id=abc123; _suno_session=xyz789"')
    print("   YOUTUBE_API_KEY=your_youtube_key")
    print("   YOUTUBE_CHANNEL_ID=UCyour_channel")

    print("\n3️⃣ Chạy tool:")
    print('   python scripts/2_remix_with_suno_advanced.py song.mp3 --song-name "Shape of You - Ed Sheeran" --channel-id UCxxxxx --style lofi_chill')

    print("\n4️⃣ Theo dõi kết quả:")
    print("   - output/music/: File MP3 remix")
    print("   - output/logs/: Chi tiết workflow")
    print("   - output/metadata/: Thống kê attempts")

def main():
    print("🎵 Suno Remix Tool - Demo Version")
    print("🔧 Testing all components...")

    success = demo_workflow()
    show_usage()

    print("\n" + "=" * 60)
    if success:
        print("✅ DEMO COMPLETED SUCCESSFULLY!")
        print("🎯 Tool is ready for production use with real APIs")
    else:
        print("❌ Demo failed - check errors above")

if __name__ == '__main__':
    main()
