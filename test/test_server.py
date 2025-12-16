#!/usr/bin/env python3
"""
Server Functionality Tests
Test the debate server components directly
"""

import sys
import os
import asyncio
import tempfile

# Add backend directory to path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'backend'))

try:
    from clean_server import DebatePlatform
    from clean_database import Database
except ImportError as e:
    print(f"Import Error: {e}")
    print("Make sure clean_server.py and clean_database.py are in the backend directory")
    sys.exit(1)

def test_server_initialization():
    """Test server initialization"""
    print("Testing server initialization...")
    
    try:
        # Create a temporary database for testing
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as temp_db:
            temp_db_path = temp_db.name
        
        # Initialize server
        server = DebatePlatform(database_path=temp_db_path)
        
        # Check if server has required attributes
        required_attributes = ['database', 'waiting_users', 'active_debates']
        for attr in required_attributes:
            if not hasattr(server, attr):
                print(f"Server missing attribute: {attr}")
                return False
        
        print("Server initialization successful")
        
        # Cleanup
        os.unlink(temp_db_path)
        return True
        
    except Exception as e:
        print(f"Server initialization failed: {e}")
        return False

def test_database_integration():
    """Test server database integration"""
    print("Testing server-database integration...")
    
    try:
        # Create temporary database
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as temp_db:
            temp_db_path = temp_db.name
        
        server = DebatePlatform(database_path=temp_db_path)
        
        # Test database connection
        if server.database is None:
            print("Database not initialized")
            return False
        
        # Test basic database operation through server
        test_user = server.database.create_user("servertest", "testpass123", "server@test.com")
        if not test_user:
            print("Failed to create user through server database")
            return False
        
        print("Server-database integration working")
        
        # Cleanup
        os.unlink(temp_db_path)
        return True
        
    except Exception as e:
        print(f"Server-database integration failed: {e}")
        return False

def test_user_management():
    """Test server user management"""
    print("Testing server user management...")
    
    try:
        # Create temporary database
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as temp_db:
            temp_db_path = temp_db.name
        
        server = DebatePlatform(database_path=temp_db_path)
        
        # Test user creation
        user_data = {
            'username': 'testuser',
            'password': 'testpass123',
            'email': 'test@example.com'
        }
        
        user = server.database.create_user(
            user_data['username'],
            user_data['password'], 
            user_data['email']
        )
        
        if not user:
            print("User creation failed")
            return False
        
        # Test user authentication
        auth_user = server.database.authenticate_user(
            user_data['username'],
            user_data['password']
        )
        
        if not auth_user:
            print("User authentication failed")
            return False
        
        print("Server user management working")
        
        # Cleanup
        os.unlink(temp_db_path)
        return True
        
    except Exception as e:
        print(f"Server user management failed: {e}")
        return False

def test_topic_management():
    """Test server topic management"""
    print("Testing server topic management...")
    
    try:
        # Create temporary database
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as temp_db:
            temp_db_path = temp_db.name
        
        server = DebatePlatform(database_path=temp_db_path)
        
        # Test getting topics
        topics = server.database.get_all_topics()
        
        # Should have some default topics
        if not topics:
            print("No topics found (this might be OK for a fresh database)")
        else:
            print(f"Found {len(topics)} topics in database")
        
        # Test adding a topic
        new_topic = server.database.add_topic(
            "Test Topic",
            "This is a test topic for server testing"
        )
        
        if not new_topic:
            print("Failed to add topic")
            return False
        
        print("Server topic management working")
        
        # Cleanup
        os.unlink(temp_db_path)
        return True
        
    except Exception as e:
        print(f"Server topic management failed: {e}")
        return False

def test_matchmaking_logic():
    """Test server matchmaking logic"""
    print("Testing server matchmaking logic...")
    
    try:
        # Create temporary database
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as temp_db:
            temp_db_path = temp_db.name
        
        server = DebatePlatform(database_path=temp_db_path)
        
        # Create test users
        user1 = server.database.create_user("user1", "pass1", "user1@test.com")
        user2 = server.database.create_user("user2", "pass2", "user2@test.com")
        
        if not user1 or not user2:
            print("Failed to create test users")
            return False
        
        # Simulate adding users to waiting queue
        server.waiting_users.append({
            'user_id': user1['id'],
            'username': user1['username'],
            'websocket': None  # Mock websocket
        })
        
        server.waiting_users.append({
            'user_id': user2['id'], 
            'username': user2['username'],
            'websocket': None  # Mock websocket
        })
        
        # Test that we have users waiting
        if len(server.waiting_users) != 2:
            print("Users not added to waiting queue properly")
            return False
        
        print("Server matchmaking logic setup working")
        
        # Cleanup
        os.unlink(temp_db_path)
        return True
        
    except Exception as e:
        print(f"Server matchmaking logic failed: {e}")
        return False

def test_debate_storage():
    """Test server debate storage"""
    print("Testing server debate storage...")
    
    try:
        # Create temporary database
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as temp_db:
            temp_db_path = temp_db.name
        
        server = DebatePlatform(database_path=temp_db_path)
        
        # Create test users and topic
        user1 = server.database.create_user("debater1", "pass1", "debater1@test.com")
        user2 = server.database.create_user("debater2", "pass2", "debater2@test.com")
        topic = server.database.add_topic("Test Debate Topic", "A topic for testing debates")
        
        if not user1 or not user2 or not topic:
            print("Failed to create test data")
            return False
        
        # Test creating a debate
        debate_data = {
            'topic_id': topic['id'],
            'pro_user_id': user1['id'],
            'con_user_id': user2['id'],
            'messages': '{"messages": [{"user": "debater1", "message": "Test message"}]}',
            'winner_id': None,
            'status': 'active'
        }
        
        debate = server.database.save_debate(
            debate_data['topic_id'],
            debate_data['pro_user_id'],
            debate_data['con_user_id'],
            debate_data['messages'],
            debate_data['winner_id'],
            debate_data['status']
        )
        
        if not debate:
            print("Failed to save debate")
            return False
        
        print("Server debate storage working")
        
        # Cleanup
        os.unlink(temp_db_path)
        return True
        
    except Exception as e:
        print(f"Server debate storage failed: {e}")
        return False

def run_server_tests():
    """Run all server functionality tests"""
    print("Starting Server Functionality Tests")
    print("=" * 40)
    
    tests = [
        ("Server Initialization", test_server_initialization),
        ("Database Integration", test_database_integration),
        ("User Management", test_user_management),
        ("Topic Management", test_topic_management),
        ("Matchmaking Logic", test_matchmaking_logic),
        ("Debate Storage", test_debate_storage)
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n{test_name}:")
        try:
            result = test_func()
            if result:
                passed += 1
                print(f"{test_name} PASSED")
            else:
                print(f"{test_name} FAILED")
        except Exception as e:
            print(f"{test_name} ERROR: {e}")
    
    print("\n" + "=" * 40)
    print(f"Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("All server tests PASSED!")
    else:
        print("Some tests failed - check implementation")
    
    return passed == total

if __name__ == "__main__":
    success = run_server_tests()
    sys.exit(0 if success else 1)
