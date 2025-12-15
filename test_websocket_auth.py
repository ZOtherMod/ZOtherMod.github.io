#!/usr/bin/env python3
"""
Simple WebSocket test script to validate authentication flow
"""
import asyncio
import websockets
import json

async def test_websocket():
    uri = "ws://localhost:8765"
    
    try:
        print(f"Connecting to {uri}...")
        async with websockets.connect(uri) as websocket:
            print("✅ WebSocket connected!")
            
            # Test authentication
            auth_message = {
                "type": "authenticate",
                "username": "test",
                "password": "testpass"
            }
            
            print(f"🔐 Sending authentication: {auth_message}")
            await websocket.send(json.dumps(auth_message))
            
            # Wait for response
            response = await websocket.recv()
            print(f"📨 Received: {response}")
            
            auth_response = json.loads(response)
            
            if auth_response.get('success'):
                user_id = auth_response.get('user_id')
                print(f"✅ Authentication successful! User ID: {user_id}")
                
                # Test start_debate
                start_debate_message = {
                    "type": "start_debate",
                    "user_id": user_id,
                    "debate_id": 1
                }
                
                print(f"🎯 Sending start_debate: {start_debate_message}")
                await websocket.send(json.dumps(start_debate_message))
                
                # Wait for debate started message
                print("⏳ Waiting for debate_started message...")
                while True:
                    response = await asyncio.wait_for(websocket.recv(), timeout=10)
                    print(f"📨 Received: {response}")
                    
                    data = json.loads(response)
                    if data.get('type') == 'debate_started':
                        print(f"🎉 SUCCESS! Received debate_started: {data}")
                        break
                    elif data.get('type') == 'timer_update':
                        print(f"⏱️ Timer update: {data}")
                        
            else:
                print(f"❌ Authentication failed: {auth_response.get('error')}")
                
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    asyncio.run(test_websocket())
