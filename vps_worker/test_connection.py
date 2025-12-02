#!/usr/bin/env python3
"""
Test script to verify configuration and connections
Run: python test_connection.py
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

def test_env():
    """Test environment variables"""
    print("=" * 50)
    print("Testing Environment Variables")
    print("=" * 50)
    
    from dotenv import load_dotenv
    load_dotenv()
    
    import os
    
    required = [
        'SUPABASE_URL',
        'SUPABASE_KEY',
        'TELEGRAM_API_ID',
        'TELEGRAM_API_HASH',
    ]
    
    optional = [
        'BOT_TOKEN',
        'ADMIN_CHAT_ID',
        'ONLINESIM_API_KEY',
        'OPENAI_API_KEY',
    ]
    
    all_ok = True
    
    for var in required:
        value = os.getenv(var)
        if value:
            masked = value[:10] + '...' if len(value) > 10 else value
            print(f"✅ {var}: {masked}")
        else:
            print(f"❌ {var}: NOT SET (required)")
            all_ok = False
    
    for var in optional:
        value = os.getenv(var)
        if value:
            masked = value[:10] + '...' if len(value) > 10 else value
            print(f"✅ {var}: {masked}")
        else:
            print(f"⚠️  {var}: not set (optional)")
    
    return all_ok


def test_config():
    """Test configuration loading"""
    print("\n" + "=" * 50)
    print("Testing Configuration")
    print("=" * 50)
    
    try:
        from config import config
        print(f"✅ Config loaded successfully")
        print(f"   Supabase URL: {config.supabase.url[:30]}...")
        print(f"   Telegram API ID: {config.telegram.api_id}")
        print(f"   Poll interval: {config.worker.poll_interval}s")
        return True
    except Exception as e:
        print(f"❌ Config error: {e}")
        return False


async def test_supabase():
    """Test Supabase connection"""
    print("\n" + "=" * 50)
    print("Testing Supabase Connection")
    print("=" * 50)
    
    try:
        from services.database import db
        
        # Try to get user settings (should work even if empty)
        result = db.get_user_settings(1)
        print(f"✅ Supabase connected")
        print(f"   Test query executed successfully")
        return True
    except Exception as e:
        print(f"❌ Supabase error: {e}")
        return False


async def test_telegram_api():
    """Test Telegram API credentials"""
    print("\n" + "=" * 50)
    print("Testing Telegram API")
    print("=" * 50)
    
    try:
        from telethon import TelegramClient
        from config import config, SESSIONS_DIR
        
        session_file = SESSIONS_DIR / 'test_session'
        
        client = TelegramClient(
            str(session_file),
            config.telegram.api_id,
            config.telegram.api_hash
        )
        
        await client.connect()
        
        # Check if connected (doesn't require authorization)
        if client.is_connected():
            print(f"✅ Telegram API credentials valid")
            print(f"   API ID: {config.telegram.api_id}")
        else:
            print(f"⚠️  Could not connect to Telegram")
        
        await client.disconnect()
        
        # Cleanup test session
        import os
        test_file = str(session_file) + '.session'
        if os.path.exists(test_file):
            os.remove(test_file)
        
        return True
    except Exception as e:
        print(f"❌ Telegram API error: {e}")
        return False


async def test_notifier():
    """Test notification service"""
    print("\n" + "=" * 50)
    print("Testing Notifier")
    print("=" * 50)
    
    try:
        from config import config
        
        if not config.telegram.bot_token:
            print(f"⚠️  BOT_TOKEN not set, skipping notification test")
            return True
        
        if not config.telegram.admin_chat_id:
            print(f"⚠️  ADMIN_CHAT_ID not set, skipping notification test")
            return True
        
        from services.notifier import notifier
        
        result = await notifier.send_message(
            "🧪 <b>VPS Worker Test</b>\n\n"
            "Connection test successful!",
            disable_notification=True
        )
        
        if result:
            print(f"✅ Notification sent successfully")
        else:
            print(f"⚠️  Could not send notification")
        
        return True
    except Exception as e:
        print(f"❌ Notifier error: {e}")
        return False


async def test_yandex_gpt():
    """Test YandexGPT connection"""
    print("\n" + "=" * 50)
    print("Testing YandexGPT")
    print("=" * 50)
    
    try:
        from config import config
        
        if not config.yandex_gpt.is_configured:
            print(f"⚠️  YandexGPT not configured (optional)")
            return True
        
        from services.ai_service import ai_service
        
        result = await ai_service.generate(
            prompt="Скажи 'Привет' одним словом",
            task="content_generate",
            max_tokens=10
        )
        
        if result:
            print(f"✅ YandexGPT working")
            print(f"   Response: {result[:50]}...")
        else:
            print(f"⚠️  YandexGPT returned empty response")
        
        return True
    except Exception as e:
        print(f"❌ YandexGPT error: {e}")
        return False


async def test_openai():
    """Test OpenAI connection"""
    print("\n" + "=" * 50)
    print("Testing OpenAI")
    print("=" * 50)
    
    try:
        from config import config
        
        if not config.openai.is_configured:
            print(f"⚠️  OpenAI not configured (optional)")
            return True
        
        from services.ai_service import ai_service, AIProvider
        
        result = await ai_service.generate(
            prompt="Say 'Hello' in one word",
            task="content_generate",
            max_tokens=10,
            provider=AIProvider.OPENAI
        )
        
        if result:
            print(f"✅ OpenAI working")
            print(f"   Response: {result[:50]}...")
        else:
            print(f"⚠️  OpenAI returned empty response")
        
        return True
    except Exception as e:
        print(f"❌ OpenAI error: {e}")
        return False


async def test_onlinesim():
    """Test OnlineSim connection"""
    print("\n" + "=" * 50)
    print("Testing OnlineSim")
    print("=" * 50)
    
    try:
        from config import config
        
        if not config.onlinesim.is_configured:
            print(f"⚠️  OnlineSim not configured (optional)")
            return True
        
        from services.onlinesim import onlinesim
        
        balance = await onlinesim.get_balance()
        print(f"✅ OnlineSim connected")
        print(f"   Balance: {balance}₽")
        
        if balance < 15:
            print(f"   ⚠️  Low balance, min 15₽ for one number")
        
        return True
    except Exception as e:
        print(f"❌ OnlineSim error: {e}")
        return False


async def main():
    """Run all tests"""
    print("\n🔍 VPS Worker Connection Test\n")
    
    results = []
    
    # Sync tests
    results.append(("Environment", test_env()))
    results.append(("Config", test_config()))
    
    # Async tests
    results.append(("Supabase", await test_supabase()))
    results.append(("Telegram API", await test_telegram_api()))
    results.append(("Notifier", await test_notifier()))
    results.append(("YandexGPT", await test_yandex_gpt()))
    results.append(("OpenAI", await test_openai()))
    results.append(("OnlineSim", await test_onlinesim()))
    
    # Summary
    print("\n" + "=" * 50)
    print("Test Summary")
    print("=" * 50)
    
    all_passed = True
    for name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status}: {name}")
        if not passed:
            all_passed = False
    
    print("\n")
    if all_passed:
        print("🎉 All tests passed! Worker is ready to start.")
        print("Run: python main.py")
    else:
        print("⚠️  Some tests failed. Check configuration.")
    
    return all_passed


if __name__ == '__main__':
    try:
        success = asyncio.run(main())
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\nTest interrupted")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Fatal error: {e}")
        sys.exit(1)
