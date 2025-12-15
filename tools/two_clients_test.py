#!/usr/bin/env python3
import asyncio
import websockets
import json

SERVER = 'ws://localhost:8765'

async def run_client(client_name, username, password, delay_before_ping=1):
    try:
        async with websockets.connect(SERVER) as ws:
            print(f"[{client_name}] connected, sending authenticate")
            await ws.send(json.dumps({"type": "authenticate", "username": username, "password": password}))

            user_id = None

            async def receiver():
                nonlocal user_id
                try:
                    async for msg in ws:
                        print(f"[{client_name}] recv: {msg}")
                        try:
                            data = json.loads(msg)
                            if data.get('type') == 'auth_response' and data.get('success'):
                                user_id = data.get('user_id')
                        except Exception:
                            pass
                except websockets.ConnectionClosed as e:
                    print(f"[{client_name}] receiver: connection closed: {e.code} {e.reason}")

            recv_task = asyncio.create_task(receiver())

            # wait for auth to complete or timeout
            waited = 0
            while user_id is None and waited < 5:
                await asyncio.sleep(0.5)
                waited += 0.5

            if user_id is None:
                print(f"[{client_name}] did not authenticate, aborting ping attempts")
                recv_task.cancel()
                return

            # wait for a short time then start debate session and ping ready
            await asyncio.sleep(delay_before_ping)
            
            # First, try to start the debate session
            start_msg = {"type": "start_debate", "debate_id": 1, "user_id": user_id}
            print(f"[{client_name}] send start_debate (user_id={user_id})")
            await ws.send(json.dumps(start_msg))
            await asyncio.sleep(1)
            
            # Then send ping_ready messages
            for i in range(6):
                msg = {"type": "ping_ready", "debate_id": 1, "user_id": user_id}
                print(f"[{client_name}] send ping_ready #{i+1} (user_id={user_id})")
                await ws.send(json.dumps(msg))
                await asyncio.sleep(1)

            # keep connection open a bit
            await asyncio.sleep(5)
            recv_task.cancel()
    except Exception as e:
        print(f"[{client_name}] exception: {e}")

async def main():
    # Use test accounts with correct passwords (from database.py init)
    tasks = [
        run_client('clientA', 'test', 'passpass', delay_before_ping=1),
        run_client('clientB', 'test2', 'passpass', delay_before_ping=2),
    ]
    await asyncio.gather(*tasks)

if __name__ == '__main__':
    asyncio.run(main())
