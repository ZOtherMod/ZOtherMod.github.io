#!/usr/bin/env python3
"""
Simple WebSocket Server Test
Test basic WebSocket connection and messaging
"""

import asyncio
import websockets
import json
import sys
import os

# Add backend directory to path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'backend'))

async def test_websocket_connection():
    """Test basic WebSocket connection to server"""
    print("Testing WebSocket connection...")
    
    try:
        # Connect to the debate server
        uri = "ws://localhost:8765"
        async with websockets.connect(uri) as websocket:
            print("WebSocket connection established")
            
            # Test sending a message
            test_message = {
                "type": "test",
                "message": "Hello from test client"
            }
            
            await websocket.send(json.dumps(test_message))
            print("Message sent successfully")
            
            # Try to receive a response (with timeout)
            try:
                response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                response_data = json.loads(response)
                print(f"Received response: {response_data.get('type', 'unknown')}")
            except asyncio.TimeoutError:
                print("No response received (timeout)")
            
            return True
            
    except Exception as e:
        print(f"WebSocket connection failed: {e}")
        return False

async def test_authentication():
    """Test user authentication through WebSocket"""
    print("Testing WebSocket authentication...")
    
    try:
        uri = "ws://localhost:8765"
        async with websockets.connect(uri) as websocket:
            
            # Test authentication message
            auth_message = {
                "type": "authenticate",
                "username": "testuser",
                "password": "testpass"
            }
            
            await websocket.send(json.dumps(auth_message))
            print("Authentication message sent")
            
            # Wait for authentication response
            response = await asyncio.wait_for(websocket.recv(), timeout=10.0)
            response_data = json.loads(response)
            
            if response_data.get('type') == 'auth_response':
                if response_data.get('success'):
                    print("Authentication successful")
                    return True
                else:
                    print(f"Authentication failed: {response_data.get('error', 'Unknown error')}")
                    return False
            else:
                print(f"Unexpected response type: {response_data.get('type')}")
                return False
                
    except Exception as e:
        print(f"Authentication test failed: {e}")
        return False

async def test_matchmaking():
    """Test joining matchmaking queue"""
    print("Testing matchmaking...")
    
    try:
        uri = "ws://localhost:8765"
        async with websockets.connect(uri) as websocket:
            
            # First authenticate
            auth_message = {
                "type": "authenticate", 
                "username": "testuser",
                "password": "testpass"
            }
            await websocket.send(json.dumps(auth_message))
            
            # Wait for auth response
            auth_response = await websocket.recv()
            auth_data = json.loads(auth_response)
            
            if not auth_data.get('success'):
                print("Authentication failed for matchmaking test")
                return False
            
            # Join matchmaking
            matchmaking_message = {
                "type": "join_matchmaking"
            }
            await websocket.send(json.dumps(matchmaking_message))
            print("Matchmaking request sent")
            
            # Wait for queue response
            response = await asyncio.wait_for(websocket.recv(), timeout=10.0)
            response_data = json.loads(response)
            
            if response_data.get('type') == 'queue_joined':
                print("Successfully joined matchmaking queue")
                return True
            else:
                print(f"Unexpected matchmaking response: {response_data}")
                return False
                
    except Exception as e:
        print(f"Matchmaking test failed: {e}")
        return False

async def test_two_user_match():
    """Test matching two users for a debate"""
    print("Testing two-user matching...")
    
    async def user_client(username, password, user_number):
        """Simulate a single user client"""
        try:
            uri = "ws://localhost:8765"
            async with websockets.connect(uri) as websocket:
                
                # Authenticate
                auth_message = {
                    "type": "authenticate",
                    "username": username,
                    "password": password
                }
                await websocket.send(json.dumps(auth_message))
                
                auth_response = await websocket.recv()
                auth_data = json.loads(auth_response)
                
                if not auth_data.get('success'):
                    print(f"User {user_number} authentication failed")
                    return False
                
                print(f"User {user_number} authenticated")
                
                # Join matchmaking
                matchmaking_message = {"type": "join_matchmaking"}
                await websocket.send(json.dumps(matchmaking_message))
                
                # Wait for responses
                for _ in range(3):  # Wait for up to 3 messages
                    try:
                        response = await asyncio.wait_for(websocket.recv(), timeout=15.0)
                        response_data = json.loads(response)
                        
                        if response_data.get('type') == 'match_found':
                            print(f"User {user_number} found a match!")
                            return True
                        elif response_data.get('type') == 'queue_joined':
                            print(f"User {user_number} joined queue")
                        else:
                            print(f"User {user_number} received: {response_data.get('type')}")
                            
                    except asyncio.TimeoutError:
                        print(f"User {user_number} timeout waiting for match")
                        break
                        
                return False
                
        except Exception as e:
            print(f"User {user_number} client failed: {e}")
            return False
    
    # Run both users concurrently
    try:
        results = await asyncio.gather(
            user_client("testuser1", "testpass1", 1),
            user_client("testuser2", "testpass2", 2),
            return_exceptions=True
        )
        
        success_count = sum(1 for result in results if result is True)
        print(f"{success_count}/2 users successfully matched")
        return success_count >= 1  # At least one match is good
        
    except Exception as e:
        print(f"Two-user match test failed: {e}")
        return False

async def run_websocket_tests():
    """Run all WebSocket tests"""
    print("Starting WebSocket Tests")
    print("=" * 40)
    print("Make sure the debate server is running on localhost:8765")
    print("=" * 40)
    
    tests = [
        ("Connection Test", test_websocket_connection),
        ("Authentication Test", test_authentication),
        ("Matchmaking Test", test_matchmaking),
        ("Two-User Match Test", test_two_user_match)
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n{test_name}:")
        try:
            result = await test_func()
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
        print("All WebSocket tests PASSED!")
    else:
        print("Some tests failed - check server status")
    
    return passed == total

if __name__ == "__main__":
    success = asyncio.run(run_websocket_tests())
    sys.exit(0 if success else 1)
