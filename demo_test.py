#!/usr/bin/env python3
"""
Demo test cho Suno Remix Tool - Test với bài hát mẫu
"""

import os
import sys

# Thêm thư mục scripts vào path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'scripts'))

def demo_remix_process():
    """Demo quy trình remix"""
    print("🎵 DEMO: Suno Remix Tool Process")
    print("=" * 50)

    try:
        # Test với bài hát mẫu
        song_name = "Shape of You - Ed Sheeran"
        print(f"🎶 Testing with song: {song_name}")

        # Simulate the process (không gọi API thật)
        print("\n📋 Workflow simulation:")

        # 1. Parameter calculation
        from modules.retry_manager import retry_manager
        params = retry_manager.calculate_attempt_parameters(1)
        print(f"   1. Parameters: pitch={params['pitch_shift']}, tempo={params['tempo_multiplier']}")

        # 2. Style selection
        from utils.config_loader import config
        style = config.get_style_template('lofi_chill')
        print(f"   2. Style: {style['name']}")

        # 3. Prompt generation
        prompt = style['prompt_template'].replace('[SONG_NAME]', song_name)
        print(f"   3. Prompt: {prompt[:80]}...")

        # 4. Simulate remix generation
        print("   4. Remix generation: [MOCK] Generated successfully")

        # 5. Simulate copyright check
        print("   5. Copyright check: [MOCK] No copyright detected (12.5% match)")

        # 6. Result
        print("\n🎉 SUCCESS!")
        print("   ✅ Final remix: output/music/Shape_of_You_remix_lofi_att1.mp3")
        print("   ✅ Attempts: 1")
        print("   ✅ Copyright safe: Yes")
        print("   ✅ Log: output/logs/remix_session.json")

        return True

    except Exception as e:
        print(f"❌ Demo failed: {e}")
        return False

def show_config():
    """Hiển thị cấu hình hiện tại"""
    print("\n⚙️ CONFIGURATION:")
    print("-" * 30)

    try:
        from utils.config_loader import config

        print(f"Default style: {config.get_default_style()}")
        print(f"Max attempts: {config.max_remix_attempts}")
        print(f"Copyright threshold: {config.copyright_match_threshold}%")

        styles = config.get_config('remix_styles')['styles']
        print(f"Available styles: {len(styles)}")
        for style in styles:
            print(f"  - {style['id']}: {style['name']}")

    except Exception as e:
        print(f"Config error: {e}")

if __name__ == '__main__':
    print("🚀 Suno Remix Tool Demo")
    print("=" * 50)

    # Show config
    show_config()

    # Run demo
    print("\n" + "=" * 50)
    success = demo_remix_process()

    print("\n" + "=" * 50)
    if success:
        print("🎊 Demo completed successfully!")
        print("\n💡 Để test với API thật:")
        print("   1. Cập nhật .env với API keys thật")
        print("   2. Chạy: python scripts/2_remix_with_suno_advanced.py 'Tên bài hát'")
        print("   3. Theo dõi logs trong output/logs/")
    else:
        print("⚠️ Demo failed. Check errors above.")
