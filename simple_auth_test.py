#!/usr/bin/env python3
import asyncio
import websockets
import json

async def test_auth():
    try:
        print("Connecting to WebSocket server...")
        async with websockets.connect('ws://localhost:8765') as websocket:
            print("✅ Connected!")
            
            # Test user 'test' authentication  
            auth_msg = {
                'type': 'authenticate',
                'username': 'test',
                'password': 'passpass'
            }
            
            print(f"Sending: {json.dumps(auth_msg, indent=2)}")
            await websocket.send(json.dumps(auth_msg))
            
            print("Waiting for response...")
            response = await websocket.recv()
            print(f"✅ Received: {response}")
            
            # Test user 'test2' authentication
            auth_msg2 = {
                'type': 'authenticate', 
                'username': 'test2',
                'password': 'passpass'
            }
            
            print(f"\nSending: {json.dumps(auth_msg2, indent=2)}")
            await websocket.send(json.dumps(auth_msg2))
            
            print("Waiting for response...")
            response2 = await websocket.recv()
            print(f"✅ Received: {response2}")
            
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    asyncio.run(test_auth())
