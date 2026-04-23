"""测试LLM服务重构后的功能"""

from app.services.llm_service import get_llm, reset_llm
from app.services.llm_monitor import create_llm_with_monitoring, TokenUsageCallback


def test_singleton():
    """测试单例模式"""
    print("Test 1: Singleton pattern")
    reset_llm()
    llm1 = get_llm(token_key='user1')
    llm2 = get_llm(token_key='user2')
    assert llm1 is llm2, "Singleton should return same instance"
    print("  [OK] Singleton works correctly\n")


def test_monitoring():
    """测试监控功能"""
    print("Test 2: Monitoring functionality")
    reset_llm()
    llm = get_llm()
    assert len(llm.callbacks) > 0, "LLM should have callbacks"
    print(f"  [OK] LLM has {len(llm.callbacks)} callback(s)\n")


def test_create_monitoring():
    """测试工具函数"""
    print("Test 3: create_llm_with_monitoring tool")
    reset_llm()
    llm = get_llm()
    llm_monitored = create_llm_with_monitoring(llm, token_key='test_token')
    assert len(llm_monitored.callbacks) == 2, "Should have 2 callbacks (one from get_llm, one added)"
    print(f"  [OK] Added monitoring with token_key 'test_token'\n")


def test_imports():
    """测试导入"""
    print("Test 4: Module imports")
    from app.services.llm_service import get_llm, reset_llm
    from app.services.llm_monitor import create_llm_with_monitoring, TokenUsageCallback
    print("  [OK] All imports successful\n")


if __name__ == '__main__':
    print("=" * 60)
    print("LLM Service Refactor Verification Tests")
    print("=" * 60 + "\n")

    try:
        test_imports()
        test_singleton()
        test_monitoring()
        test_create_monitoring()

        print("=" * 60)
        print("[SUCCESS] All tests passed!")
        print("=" * 60)
    except AssertionError as e:
        print(f"\n[ERROR] Test failed: {e}")
        raise
    except Exception as e:
        print(f"\n[ERROR] Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        raise
