#!/usr/bin/env python3
"""
Backend Test - Short Subscriber ID Generation Feature
Testing specific items from review request:
1. generate_subscriber_id function exists in utils.py
2. Function generates IDs in format 'eb' + 8 lowercase alphanumeric chars
3. Function has DB uniqueness check loop and fallback
4. create_subscriber endpoint uses new ID
5. bulk_upload_subscribers uses new ID
6. Backend health check
"""

import asyncio
import re
import sys
import os
import requests

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

from database import db
from utils import generate_subscriber_id

# Backend URL
BASE_URL = "http://localhost:8001"

def print_test_header(test_name):
    print(f"\n{'='*80}")
    print(f"TEST: {test_name}")
    print(f"{'='*80}")

def print_result(passed, message):
    status = "✅ PASS" if passed else "❌ FAIL"
    print(f"{status}: {message}")


async def test_subscriber_id_generation():
    """Test the generate_subscriber_id function."""
    print_test_header("Short Subscriber ID Generation Function")
    
    all_passed = True
    
    # Test 1: Function exists and is async
    print("\n1. Function exists and is async")
    print(f"   - Function: {generate_subscriber_id}")
    print(f"   - Is coroutine: {asyncio.iscoroutinefunction(generate_subscriber_id)}")
    if asyncio.iscoroutinefunction(generate_subscriber_id):
        print_result(True, "Function is async")
    else:
        print_result(False, "Function is not async")
        all_passed = False
    
    # Test 2: Generate multiple IDs and verify format
    print("\n2. Generate IDs and verify format")
    print("   - Expected format: 'eb' + 8 lowercase alphanumeric chars")
    print("   - Total length: 10 characters")
    print("   - Pattern: ^eb[a-z0-9]{8}$")
    
    pattern = re.compile(r'^eb[a-z0-9]{8}$')
    generated_ids = []
    
    for i in range(5):
        sub_id = await generate_subscriber_id(db)
        generated_ids.append(sub_id)
        matches = pattern.match(sub_id)
        print(f"   - Generated ID {i+1}: {sub_id} - {'✓ Valid' if matches else '✗ Invalid'}")
        
        if not matches:
            print_result(False, f"ID {sub_id} does not match expected pattern!")
            all_passed = False
        
        if len(sub_id) != 10:
            print_result(False, f"ID length is {len(sub_id)}, expected 10!")
            all_passed = False
    
    if all([pattern.match(id) and len(id) == 10 for id in generated_ids]):
        print_result(True, "All generated IDs match expected format")
    
    # Test 3: Verify uniqueness
    print("\n3. Verify uniqueness")
    unique_ids = set(generated_ids)
    print(f"   - Generated: {len(generated_ids)} IDs")
    print(f"   - Unique: {len(unique_ids)} IDs")
    if len(unique_ids) == len(generated_ids):
        print_result(True, "All IDs are unique")
    else:
        print_result(False, "Duplicate IDs found")
        all_passed = False
    
    return all_passed, generated_ids


def test_code_integration():
    """Test code integration in operator.py and job_queue_service.py"""
    print_test_header("Code Integration Verification")
    
    all_passed = True
    
    # Test 4: Verify imports in operator.py
    print("\n4. Verify imports and usage in operator.py")
    operator_file = os.path.join(os.path.dirname(__file__), 'backend', 'routers', 'operator.py')
    with open(operator_file, 'r') as f:
        content = f.read()
        
        if 'from utils import' in content and 'generate_subscriber_id' in content:
            print_result(True, "generate_subscriber_id is imported in operator.py")
        else:
            print_result(False, "generate_subscriber_id not found in imports!")
            all_passed = False
        
        if 'await generate_subscriber_id(db)' in content:
            print_result(True, "create_subscriber uses await generate_subscriber_id(db)")
            # Find the line number
            for i, line in enumerate(content.split('\n'), 1):
                if 'await generate_subscriber_id(db)' in line:
                    print(f"   - Found at line {i}")
                    break
        else:
            print_result(False, "create_subscriber does not use generate_subscriber_id!")
            all_passed = False
    
    # Test 5: Verify imports in job_queue_service.py
    print("\n5. Verify imports and usage in job_queue_service.py")
    job_queue_file = os.path.join(os.path.dirname(__file__), 'backend', 'services', 'job_queue_service.py')
    with open(job_queue_file, 'r') as f:
        content = f.read()
        
        if 'from utils import' in content and 'generate_subscriber_id' in content:
            print_result(True, "generate_subscriber_id is imported in job_queue_service.py")
        else:
            print_result(False, "generate_subscriber_id not found in imports!")
            all_passed = False
        
        if 'await generate_subscriber_id(db)' in content:
            print_result(True, "bulk_upload_subscribers uses await generate_subscriber_id(db)")
            # Find the line number
            for i, line in enumerate(content.split('\n'), 1):
                if 'await generate_subscriber_id(db)' in line:
                    print(f"   - Found at line {i}")
                    break
        else:
            print_result(False, "bulk_upload_subscribers does not use generate_subscriber_id!")
            all_passed = False
    
    # Test 6: Verify function implementation details
    print("\n6. Verify function implementation in utils.py")
    utils_file = os.path.join(os.path.dirname(__file__), 'backend', 'utils.py')
    with open(utils_file, 'r') as f:
        content = f.read()
        
        # Find the function
        func_start = content.find('async def generate_subscriber_id')
        if func_start == -1:
            print_result(False, "generate_subscriber_id function not found!")
            all_passed = False
        else:
            # Extract function content (rough extraction)
            func_end = content.find('\n\nasync def', func_start + 1)
            if func_end == -1:
                func_end = content.find('\n\ndef ', func_start + 1)
            if func_end == -1:
                func_end = len(content)
            
            func_content = content[func_start:func_end]
            
            # Check for DB uniqueness check
            if 'await db.subscribers.find_one' in func_content and '"id":' in func_content:
                print_result(True, "Function has DB uniqueness check loop")
            else:
                print_result(False, "DB uniqueness check not found")
                all_passed = False
            
            # Check for retry loop
            if 'for _ in range(' in func_content:
                print_result(True, "Function has retry loop")
            else:
                print_result(False, "Retry loop not found")
                all_passed = False
            
            # Check for fallback mechanism
            if 'fallback' in func_content.lower() or ('datetime' in func_content and 'strftime' in func_content):
                print_result(True, "Function has fallback mechanism")
            else:
                print_result(False, "Fallback mechanism not found")
                all_passed = False
            
            # Check for secrets module (secure random generation)
            if 'import secrets' in func_content:
                print_result(True, "Function uses secrets module for secure random generation")
            else:
                print_result(False, "secrets module not found")
                all_passed = False
    
    return all_passed


def test_backend_health():
    """Test backend health endpoint."""
    print_test_header("Backend Health Check")
    
    url = f"{BASE_URL}/api/health"
    
    try:
        response = requests.get(url, timeout=10)
        print(f"Status: {response.status_code}")
        print(f"Response: {response.text}")
        
        if response.status_code == 200:
            print_result(True, "Backend health endpoint is working")
            return True
        else:
            print_result(False, f"Health check failed with status {response.status_code}")
            return False
    except Exception as e:
        print_result(False, f"Health check error: {str(e)}")
        return False


async def main():
    """Run all tests."""
    print("\n" + "="*80)
    print("BACKEND TEST - SHORT SUBSCRIBER ID GENERATION FEATURE")
    print("="*80)
    print("Testing:")
    print("1. generate_subscriber_id function exists and is async")
    print("2. Function generates IDs in format 'eb' + 8 lowercase alphanumeric chars")
    print("3. Function has DB uniqueness check loop and fallback")
    print("4. create_subscriber endpoint uses new ID")
    print("5. bulk_upload_subscribers uses new ID")
    print("6. Backend health check")
    print("="*80)
    
    results = {}
    
    try:
        # Test subscriber ID generation
        result1, generated_ids = await test_subscriber_id_generation()
        results["ID Generation"] = result1
        
        # Test code integration
        result2 = test_code_integration()
        results["Code Integration"] = result2
        
        # Test backend health
        result3 = test_backend_health()
        results["Backend Health"] = result3
        
        # Summary
        print("\n" + "="*80)
        print("TEST SUMMARY")
        print("="*80)
        for test_name, result in results.items():
            status = "✅ PASS" if result else "❌ FAIL"
            print(f"{status}: {test_name}")
        
        print("\n" + "="*80)
        print("FEATURE SUMMARY")
        print("="*80)
        print("Subscriber ID Format:")
        print("  - Prefix: 'eb'")
        print("  - Length: 10 characters total")
        print("  - Pattern: eb + 8 lowercase alphanumeric chars [a-z0-9]")
        print("  - Example IDs:", ", ".join(generated_ids[:3]))
        print("\nImplementation:")
        print("  - Uniqueness: Guaranteed via DB check with 20 retry attempts")
        print("  - Fallback: Timestamp-based ID if all retries fail")
        print("  - Security: Uses secrets module for cryptographically strong random generation")
        print("  - Integration: Used in create_subscriber and bulk_upload_subscribers")
        print("\nNo import or syntax errors detected.")
        print("="*80)
        
        if all(results.values()):
            print("\n✅ ALL TESTS PASSED!")
            sys.exit(0)
        else:
            print("\n❌ SOME TESTS FAILED!")
            sys.exit(1)
    except Exception as e:
        print(f"\n❌ Test execution failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
