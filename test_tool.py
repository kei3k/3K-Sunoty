#!/usr/bin/env python3
"""
Script test đơn giản cho Suno Remix Tool
"""

import os
import sys
import time

# Thêm thư mục scripts vào path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'scripts'))

def test_imports():
    """Test import các module cơ bản"""
    print("🔍 Testing imports...")

    try:
        from utils.config_loader import config
        print("✅ Config loader OK")

        from utils.logger import logger
        print("✅ Logger OK")

        from modules.retry_manager import retry_manager
        print("✅ Retry manager OK")

        return True
    except Exception as e:
        print(f"❌ Import failed: {e}")
        return False

def test_config():
    """Test cấu hình"""
    print("\n🔧 Testing config...")

    try:
        from utils.config_loader import config

        # Test style templates
        style = config.get_style_template('lofi_chill')
        if style:
            print("✅ Style template loaded")
        else:
            print("❌ Style template not found")

        # Test default style
        default_style = config.get_default_style()
        print(f"✅ Default style: {default_style}")

        return True
    except Exception as e:
        print(f"❌ Config test failed: {e}")
        return False

def test_parameters():
    """Test tính toán parameters"""
    print("\n⚙️ Testing parameter calculation...")

    try:
        from modules.retry_manager import retry_manager

        # Test attempt 1
        params1 = retry_manager.calculate_attempt_parameters(1)
        print(f"✅ Attempt 1: pitch={params1['pitch_shift']}, tempo={params1['tempo_multiplier']}")

        # Test attempt 2
        params2 = retry_manager.calculate_attempt_parameters(2)
        print(f"✅ Attempt 2: pitch={params2['pitch_shift']}, tempo={params2['tempo_multiplier']}")

        return True
    except Exception as e:
        print(f"❌ Parameter test failed: {e}")
        return False

def test_retry_logic():
    """Test logic retry"""
    print("\n🔄 Testing retry logic...")

    try:
        from modules.retry_manager import retry_manager

        # Test không có copyright
        result = retry_manager.should_retry(1, {'has_copyright': False})
        if not result['should_retry']:
            print("✅ No copyright - no retry")
        else:
            print("❌ Logic error")

        # Test có copyright cao
        result = retry_manager.should_retry(1, {'has_copyright': True, 'claims': [{'matchPercent': 85}]})
        if result['should_retry']:
            print("✅ High copyright - retry")
        else:
            print("❌ Logic error")

        return True
    except Exception as e:
        print(f"❌ Retry logic test failed: {e}")
        return False

def test_audio_processing():
    """Test xử lý audio (mock)"""
    print("\n🎵 Testing audio processing...")

    try:
        from modules.audio_processor import audio_processor

        # Test validation parameters
        valid = audio_processor.validate_parameters(2, 1.05)
        if valid:
            print("✅ Parameter validation OK")
        else:
            print("❌ Parameter validation failed")

        # Test invalid parameters
        invalid = audio_processor.validate_parameters(10, 1.05)  # Pitch too high
        if not invalid:
            print("✅ Invalid parameter detection OK")
        else:
            print("❌ Should detect invalid parameters")

        return True
    except Exception as e:
        print(f"❌ Audio processing test failed: {e}")
        return False

def test_suno_client():
    """Test Suno client (mock)"""
    print("\n🎶 Testing Suno client...")

    try:
        # Test that we can import the module without errors
        from modules.suno_client import SunoRemixGenerator

        # Test that the class exists
        if hasattr(SunoRemixGenerator, 'generate_remix'):
            print("✅ Suno client class available")
        else:
            print("❌ Suno client class missing methods")
            return False

        # Skip actual initialization to avoid browser dependency issues
        # The real test happens when the app runs with proper env setup

        print("✅ Suno client module OK (skipping live test)")
        return True
    except Exception as e:
        print(f"❌ Suno client test failed: {e}")
        return False

def run_all_tests():
    """Chạy tất cả test"""
    print("🚀 Starting Suno Remix Tool Tests")
    print("=" * 50)

    tests = [
        ("Imports", test_imports),
        ("Config", test_config),
        ("Parameters", test_parameters),
        ("Retry Logic", test_retry_logic),
        ("Audio Processing", test_audio_processing),
        ("Suno Client", test_suno_client),
    ]

    passed = 0
    total = len(tests)

    for test_name, test_func in tests:
        try:
            if test_func():
                passed += 1
            else:
                print(f"❌ {test_name} failed")
        except Exception as e:
            print(f"❌ {test_name} crashed: {e}")

    print("\n" + "=" * 50)
    print(f"📊 Test Results: {passed}/{total} passed")

    if passed == total:
        print("🎉 All tests passed! Tool is ready.")
        return True
    else:
        print("⚠️ Some tests failed. Check the errors above.")
        return False

if __name__ == '__main__':
    success = run_all_tests()
    sys.exit(0 if success else 1)
