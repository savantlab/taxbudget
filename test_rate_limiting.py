#!/usr/bin/env python
"""
Manual test for rate limiting functionality
Run this after starting the Django server to verify rate limiting works.
"""

import requests
import time

BASE_URL = 'http://localhost:8000'

def test_rate_limiting():
    """Test that rate limiting blocks after 10 requests per hour"""
    
    print("Testing rate limiting on allocation submission...")
    print(f"Limit: 10 submissions per hour per user/IP\n")
    
    # Get CSRF token first
    session = requests.Session()
    response = session.get(f'{BASE_URL}/')
    csrf_token = session.cookies.get('csrftoken')
    
    # Prepare test data (must sum to 100%)
    test_data = {
        'csrfmiddlewaretoken': csrf_token,
        'category_1': '10',
        'category_2': '10',
        'category_3': '10',
        'category_4': '10',
        'category_5': '10',
        'category_6': '10',
        'category_7': '10',
        'category_8': '10',
        'category_9': '10',
        'category_10': '10',
    }
    
    success_count = 0
    rate_limited = False
    
    # Try to submit 12 times (should hit limit at 11th)
    for i in range(1, 13):
        response = session.post(
            f'{BASE_URL}/',
            data=test_data,
            headers={'Referer': f'{BASE_URL}/'}
        )
        
        if response.status_code == 200:
            if 'Rate limit exceeded' in response.text:
                print(f"Request {i}: ❌ RATE LIMITED")
                rate_limited = True
                break
            elif 'successfully' in response.text or response.url != f'{BASE_URL}/':
                print(f"Request {i}: ✅ Success")
                success_count += 1
            else:
                print(f"Request {i}: ⚠️  Form error (check validation)")
        else:
            print(f"Request {i}: ❌ HTTP {response.status_code}")
        
        time.sleep(0.1)  # Small delay between requests
    
    print(f"\n{'='*50}")
    print(f"Results:")
    print(f"  Successful submissions: {success_count}")
    print(f"  Rate limited: {'YES' if rate_limited else 'NO'}")
    print(f"{'='*50}\n")
    
    if rate_limited and success_count == 10:
        print("✅ Rate limiting is working correctly!")
        print("   - Allowed exactly 10 submissions")
        print("   - Blocked 11th submission")
    elif success_count < 10:
        print("⚠️  Check your form data - submissions may be failing validation")
    else:
        print("❌ Rate limiting may not be working")
        print("   - Expected to be blocked after 10 submissions")

if __name__ == '__main__':
    print("\nMake sure Django server is running: python manage.py runserver\n")
    input("Press Enter to start test...")
    test_rate_limiting()
