#!/usr/bin/env python3

import sys
import os
sys.path.append('/Users/nicolas/Documents/Code/DebatePlatform/backend')

from database import Database

def test_login_issue():
    """Test the login issue with test account"""
    print("Testing login issue...")
    
    # Create database instance
    db = Database('test_login.db')  # Use a temporary file
    
    # Test 1: Check if test account exists
    print("\n1. Checking if test account exists...")
    result = db.authenticate_user('test', 'passpass')
    print(f"Test account authentication result: {result}")
    
    # Test 2: Try to create a regular account
    print("\n2. Testing regular account creation...")
    user_id = db.create_user('testuser123', 'password123')
    print(f"Regular user creation result: {user_id}")
    
    if user_id:
        # Test 3: Try to authenticate the regular account
        print("\n3. Testing regular account authentication...")
        auth_result = db.authenticate_user('testuser123', 'password123')
        print(f"Regular user authentication result: {auth_result}")
    
    # Clean up
    try:
        os.remove('test_login.db')
        os.remove('database/test_login.db')
    except:
        pass

if __name__ == "__main__":
    test_login_issue()
