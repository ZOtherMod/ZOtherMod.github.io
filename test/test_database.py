#!/usr/bin/env python3
"""
Simple Database Tests
Test basic database operations for the debate platform
"""

import sys
import os
import tempfile

# Add backend directory to path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'backend'))

try:
    from clean_database import Database
except ImportError as e:
    print(f"Import Error: {e}")
    print("Make sure clean_database.py is in the backend directory")
    sys.exit(1)

def test_database_creation():
    """Test that database creates successfully"""
    print("Testing database creation...")
    db = Database(':memory:')  # Use in-memory database for testing
    assert db is not None
    print("Database created successfully")

def test_user_creation():
    """Test creating new users"""
    print("Testing user creation...")
    db = Database(':memory:')
    
    # Test valid user creation
    result = db.create_user("alice", "password123")
    assert result['success'] == True
    assert result['username'] == "alice"
    print("Valid user created successfully")
    
    # Test duplicate username
    result2 = db.create_user("alice", "different_password")
    assert result2['success'] == False
    assert "already exists" in result2['error']
    print("Duplicate username rejected correctly")
    
    # Test short username
    result3 = db.create_user("ab", "password123")
    assert result3['success'] == False
    assert "3 characters" in result3['error']
    print("Short username rejected correctly")
    
    # Test short password
    result4 = db.create_user("bob", "12345")
    assert result4['success'] == False
    assert "6 characters" in result4['error']
    print("Short password rejected correctly")

def test_user_authentication():
    """Test user login authentication"""
    print("Testing user authentication...")
    db = Database(':memory:')
    
    # Create a test user
    db.create_user("testuser", "testpass")
    
    # Test correct credentials
    auth = db.authenticate_user("testuser", "testpass")
    assert auth['success'] == True
    assert auth['username'] == "testuser"
    assert auth['mmr'] == 1000  # Default MMR
    print("Correct authentication works")
    
    # Test wrong password
    auth2 = db.authenticate_user("testuser", "wrongpass")
    assert auth2['success'] == False
    print("Wrong password rejected")
    
    # Test nonexistent user
    auth3 = db.authenticate_user("nonexistent", "password")
    assert auth3['success'] == False
    print("Nonexistent user rejected")

def test_topics():
    """Test topic management"""
    print("Testing topic management...")
    db = Database(':memory:')
    
    # Test getting random topic
    topic = db.get_random_topic()
    assert topic is not None
    assert len(topic) > 0
    print(f"Got random topic: {topic[:50]}...")
    
    # Test adding new topic
    success = db.add_topic("Test topic for debate", "test", "easy")
    assert success == True
    print("Added new topic successfully")
    
    # Test getting all topics
    topics = db.get_all_topics()
    assert len(topics) > 0
    print(f"Retrieved {len(topics)} topics")

def test_debate_storage():
    """Test saving debate information"""
    print("Testing debate storage...")
    db = Database(':memory:')
    
    # Create test users
    user1 = db.create_user("debater1", "password1")
    user2 = db.create_user("debater2", "password2")
    
    # Test debate messages
    messages = [
        {
            'sender_id': user1['user_id'],
            'sender_username': 'debater1',
            'content': 'My opening argument is...',
            'side': 'pro',
            'timestamp': '2025-12-16T10:00:00Z'
        },
        {
            'sender_id': user2['user_id'],
            'sender_username': 'debater2', 
            'content': 'I disagree because...',
            'side': 'con',
            'timestamp': '2025-12-16T10:05:00Z'
        }
    ]
    
    # Save debate
    debate_id = db.save_debate(
        user1['user_id'], 
        user2['user_id'], 
        "Technology improves life",
        messages,
        winner_id=user1['user_id'],
        duration_minutes=15
    )
    
    assert debate_id is not None
    print(f"Debate saved with ID: {debate_id}")
    
    # Check user statistics were updated
    user1_updated = db.get_user_by_id(user1['user_id'])
    assert user1_updated['wins'] == 1
    assert user1_updated['debates_count'] == 1
    print("Winner statistics updated correctly")
    
    user2_updated = db.get_user_by_id(user2['user_id'])
    assert user2_updated['losses'] == 1
    assert user2_updated['debates_count'] == 1
    print("Loser statistics updated correctly")

def run_all_tests():
    """Run all database tests"""
    print(" Starting Database Tests")
    print("=" * 40)
    
    try:
        test_database_creation()
        test_user_creation()
        test_user_authentication()
        test_topics()
        test_debate_storage()
        
        print("=" * 40)
        print("All database tests PASSED!")
        return True
        
    except Exception as e:
        print(f"Test FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
