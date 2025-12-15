#!/usr/bin/env python3

import asyncio
import json
import websockets

async def test_login():
    """Test login with the test account"""
    try:
        async with websockets.connect('ws://localhost:8765') as websocket:
            print("Connected to server")
            
            # Test the test account
            print("Testing test account login...")
            message = {
                'type': 'authenticate',
                'username': 'test',
                'password': 'passpass'
            }
            
            await websocket.send(json.dumps(message))
            response = await websocket.recv()
            data = json.loads(response)
            
            print(f"Test account result: {data}")
            
            if data.get('success'):
                print("✅ Test account login works!")
                print(f"   User ID: {data.get('user_id')}")
                print(f"   Username: {data.get('username')}")
                print(f"   MMR: {data.get('mmr')}")
                print(f"   UserClass: {data.get('user_class')}")
            else:
                print("❌ Test account login failed!")
                
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(test_login())
