# -*- coding: utf-8 -*-
"""
Quick test of authentication and rate limiting services
"""
import sys
import os

sys.path.insert(0, '..')
from api.services.auth import AuthService
from api.services.audit_logger import AuditLogger
import pyotp
import redis


def test_auth_service():
    """Test authentication service"""
    print("=" * 60)
    print("Testing Authentication Service")
    print("=" * 60)
    
    # Create test auth service
    test_key = "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIMockKeyForTesting test@aegis"
    auth_service = AuthService(
        authorized_keys=[test_key],
        whitelisted_ips=["127.0.0.1"],
        jwt_secret="test-secret-key-min-32-characters-long",
        session_timeout=1800
    )
    
    # Test 1: IP verification
    print("\n1. Testing IP whitelisting...")
    assert auth_service.verify_ip("127.0.0.1") == True, "[FAIL] IP should be whitelisted"
    assert auth_service.verify_ip("1.2.3.4") == False, "[FAIL] IP should not be whitelisted"
    print("   [PASS] IP whitelisting works")
    
    # Test 2: SSH key verification  
    print("\n2. Testing SSH key verification...")
    assert auth_service.verify_ssh_key(test_key) == True, "[FAIL] Key should be authorized"
    assert auth_service.verify_ssh_key("ssh-ed25519 AAAAC3 fake@key") == False, "[FAIL] Key should not be authorized"
    print("   [PASS] SSH key verification works")
    
    # Test 3: TOTP
    print("\n3. Testing TOTP...")
    secret = pyotp.random_base32()
    auth_service.register_totp_secret("test_user", secret)
    totp = pyotp.TOTP(secret)
    valid_token = totp.now()
    assert auth_service.verify_totp("test_user", valid_token) == True, "[FAIL] Valid TOTP should pass"
    assert auth_service.verify_totp("test_user", "000000") == False, "[FAIL] Invalid TOTP should fail"
    print("   [PASS] TOTP verification works")
    
    # Test 4: Session token
    print("\n4. Testing JWT session tokens...")
    token = auth_service.create_session_token("test_user", {"test": "metadata"})
    assert token is not None, "[FAIL] Token should be created"
    payload = auth_service.verify_session_token(token)
    assert payload["sub"] == "test_user", "[FAIL] Token should contain user"
    assert payload["test"] == "metadata", "[FAIL] Token should contain metadata"
    print("   [PASS] JWT session tokens work")
    
    print("\n" + "=" * 60)
    print("[SUCCESS] All authentication tests passed!")
    print("=" * 60)


def test_audit_logger():
    """Test audit logger"""
    print("\n" + "=" * 60)
    print("Testing Audit Logger")
    print("=" * 60)
    
    # Connect to Redis (ensure Redis is running)
    try:
        redis_client = redis.from_url("redis://localhost:6379/1", decode_responses=True)
        redis_client.ping()
    except Exception as e:
        print(f"\n[SKIP] Redis not available: {e}")
        print("   Skipping audit logger tests (install and start Redis to test)")
        return
    
    # Clear test data
    redis_client.flushdb()
    
    audit_logger = AuditLogger(redis_client, retention_days=90)
    
    # Test 1: Log action
    print("\n1. Testing audit logging...")
    audit_logger.log_action(
        user="test_user",
        action="test.action",
        details={"test": "data"},
        client_ip="127.0.0.1",
        success=True
    )
    print("   [PASS] Action logged")
    
    # Test 2: Retrieve logs
    print("\n2. Testing log retrieval...")
    logs = audit_logger.get_logs(limit=10)
    assert len(logs) == 1, "[FAIL] Should have 1 log entry"
    assert logs[0]["user"] == "test_user", "[FAIL] User mismatch"
    assert logs[0]["action"] == "test.action", "[FAIL] Action mismatch"
    print("   [PASS] Logs retrieved successfully")
    
    # Test 3: Search logs
    print("\n3. Testing log search...")
    audit_logger.log_action("user2", "other.action", {}, "1.2.3.4", True)
    search_results = audit_logger.search_logs(user="test_user")
    assert len(search_results) == 1, "[FAIL] Should find 1 matching log"
    assert search_results[0]["user"] == "test_user", "[FAIL] Wrong user in results"
    print("   [PASS] Log search works")
    
    # Cleanup
    redis_client.flushdb()
    redis_client.close()
    
    print("\n" + "=" * 60)
    print("[SUCCESS] All audit logger tests passed!")
    print("=" * 60)


if __name__ == "__main__":
    try:
        test_auth_service()
        test_audit_logger()
        
        print("\n" + "=" * 60)
        print("[SUCCESS] ALL TESTS PASSED")
        print("=" * 60)
        print("\nNext steps:")
        print("1. Install CLI dependencies: cd cli && python -m pip install -r requirements.txt")
        print("2. Run CLI setup: cd cli && python setup_2fa.py")
        print("3. Configure Control Plane: copy .env.example to .env and set JWT_SECRET")
        print("4. Start Control Plane: uvicorn api.main:app --reload")
        print("5. Connect CLI: cd cli && python aegis_cli.py connect localhost")
        
    except AssertionError as e:
        print(f"\n[FAIL] TEST FAILED: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n[ERROR] {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
