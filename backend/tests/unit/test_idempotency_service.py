"""
    Unit Tests for Idempotency Service

    To run this TEST:
        uv run pytest tests/unit/test_idempotency_service.py -v
"""

import pytest
from app.services.idempotency_service import IdempotencyService

def test_check_key_returns_none_for_new_key(idempotency_service):
    """
    TEST CASE 1: Check new key returns None

    SCENARIO: First time checking an idempotency key
    EXPECTED: Returns None (key doesn't exist yet)
    """

    result = idempotency_service.check_key("test-key-1")

    assert result is None, "New key should return None"

    print("✅ New key correctly returned None")

def test_store_and_retrieve_key(idempotency_service):
    """
    TEST CASE 2: Store key and retrieve it

    SCENARIO: Store an idempotency key with a bill ID, then retrieve it
    EXPECTED: Retrieved value matches stored bill ID
    """

    test_key = "test-key_store-123"
    test_bill_id = "01HXXX1234ABCD567890EFGH"

    idempotency_service.store_key(test_key, test_bill_id)

    result = idempotency_service.check_key(test_key)

    assert result == test_bill_id, \
        f"Expected bill ID {test_bill_id}, got {result}"

    print(f"✅ Successfully stored and retrieved: {test_key} → {test_bill_id}")

def test_duplicate_request_returns_same_bill_id(idempotency_service):
    """
    TEST CASE 3: Duplicate requests return smae bill ID

    SCNENARIO:
        1. First request with key -> Store bill ID
        2. Second request with SAME key -> Returns existing bill ID
    EXPECTED: Both requests get the same bill ID (no duplicates!)
    """

    service = idempotency_service

    idempotency_key = "user-123-timestamp-456"
    original_bill_id = "01BILL_ORIGINAL_1234"

    service.store_key(idempotency_key, original_bill_id)
    retrieved_bill_id = service.check_key(idempotency_key)

    assert retrieved_bill_id == original_bill_id, \
        "Duplicate request should return original bill ID"
    

    new_bill_id = "01BILL_DUPLICATE_99999"

    existing_id = service.check_key(idempotency_key)

    assert existing_id == original_bill_id, \
        "Should still return original bill, not allow duplicate"
    
    print(f"✅ Idempotency working! Key {idempotency_key} → {original_bill_id}")
    print("Prevented duplicate bill creation!")

def test_delete_key_removes_from_redis(idempotency_service):
    """
    TEST CASE 4: Delete key removes it from Redis

    SCENARIO: Store a key, then delete it
    EXPECTED: After deletion, key should return None (not found)
    """

    test_key = "key-to-delete"
    test_bill_id = "01BILL_DELETE_TEST"

    idempotency_service.store_key(test_key, test_bill_id)

    result_before = idempotency_service.check_key(test_key)
    assert result_before == test_bill_id, "Key should exist before deletion"

    idempotency_service.delete_key(test_key)

    result_after = idempotency_service.check_key(test_key)
    assert result_after is None, "Key should return None after deletion"

    print("✅ Successfully deleted key: {test_key}")

def test_multiple_different_keys_are_independent(idempotency_service):
    """
      TEST CASE 5: Multiple keys don't interfere with each other

      SCENARIO: Store multiple different idempotency keys simultaneously
      EXPECTED: Each key returns its own bill ID independently
    """

    key1 = "user-1-request-123"
    key2 = "user-2-request-456"
    key3 = "user-3-request-789"

    bill1 = "01BILL_USER1_AAA"
    bill2 = "01BILL_USER2_BBB"
    bill3 = "01BILL_USER3_CCC"

    idempotency_service.store_key(key1, bill1)
    idempotency_service.store_key(key2, bill2)
    idempotency_service.store_key(key3, bill3)

    assert idempotency_service.check_key(key1) == bill1, \
        "Key 1 should return its own bill ID"
    assert idempotency_service.check_key(key2) == bill2, \
        "Key 1 should return its own bill ID"
    assert idempotency_service.check_key(key3) == bill3, \
        "Key 1 should return its own bill ID"

    idempotency_service.delete_key(key2)

    assert idempotency_service.check_key(key1) == bill1, \
        "Key 1 should still exist after deleting key 2"
    assert idempotency_service.check_key(key2) is None, \
        "Key 2 should be None after deleting"
    assert idempotency_service.check_key(key3) == bill3, \
        "Key 3 should still exist after deleting key 2"

    print("✅ Multiple keys are correctly independent!")
    print(f"   {key1} → {bill1}")
    print(f"   {key2} → deleted")
    print(f"   {key3} → {bill3}")



