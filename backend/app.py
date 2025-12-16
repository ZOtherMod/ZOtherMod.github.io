#!/usr/bin/env python3
"""
Simplified Debate Platform Server
Based on the working LAN chat application architecture
"""

import asyncio
import json
import os
import websockets
import logging
from datetime import datetime

# Use the same simple structure that works
from database import Database
from debate_logic import DebateManager
from websocket_manager import WebSocketManager
from matchmaking import Matchmaker

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SimpleDebateServer:
    def __init__(self):
        self.database = Database()
        
        # SIMPLE MATCHING - just like the chat app
        self.connected_users = {}  # websocket -> user_info
        self.waiting_queue = []    # users waiting for matches
        self.active_debates = {}   # debate_id -> debate_info
        self.debate_counter = 0
        
    async def register_client(self, websocket):
        """Register a new client"""
        logger.info(f"Client connected")
        
    async def unregister_client(self, websocket):
        """Clean up disconnected client"""
        if websocket in self.connected_users:
            user_info = self.connected_users.pop(websocket)
            logger.info(f"User {user_info.get('username', 'Unknown')} disconnected")
            
        if websocket in self.waiting_queue:
            self.waiting_queue.remove(websocket)
            logger.info(f"Removed user from waiting queue")
            
        # Remove from any active debate
        for debate_id, debate in list(self.active_debates.items()):
            if websocket in [debate['user1_ws'], debate['user2_ws']]:
                logger.info(f"User left active debate {debate_id}")
                await self.end_debate_early(debate_id)
                break
            
    async def handle_client(self, websocket, path):
        """Handle a client connection (simplified like chat app)"""
        await self.register_client(websocket)
        try:
            async for message in websocket:
                await self.handle_message(websocket, message)
        except websockets.exceptions.ConnectionClosed:
            logger.info("Client disconnected normally")
        except Exception as e:
            logger.error(f"Client error: {e}")
        finally:
            await self.unregister_client(websocket)
            
    async def handle_message(self, websocket, message_data):
        """Handle incoming message (simplified)"""
        try:
            data = json.loads(message_data)
            message_type = data.get("type")
            
            if message_type == "authenticate" or message_type == "join":
                await self.handle_authenticate(websocket, data)
            elif message_type == "join_matchmaking":
                await self.handle_join_matchmaking(websocket, data)
            elif message_type == "leave_matchmaking":
                await self.handle_leave_matchmaking(websocket, data)
            elif message_type == "debate_message":
                await self.handle_debate_message(websocket, data)
            elif message_type == "ping":
                await self.handle_ping(websocket, data)
            else:
                await websocket.send(json.dumps({
                    "type": "error",
                    "message": f"Unknown message type: {message_type}"
                }))
                
        except json.JSONDecodeError:
            await websocket.send(json.dumps({
                "type": "error", 
                "message": "Invalid JSON format"
            }))
        except Exception as e:
            logger.error(f"Error handling message: {e}")
            await websocket.send(json.dumps({
                "type": "error",
                "message": "Server error"
            }))
            
    async def handle_authenticate(self, websocket, data):
        """SUPER SIMPLE AUTH - just username, no password"""
        username = data.get('username', '').strip()
        
        if not username:
            await websocket.send(json.dumps({
                'type': 'auth_response',
                'success': False,
                'error': 'Username required'
            }))
            return
            
        # SIMPLE STORAGE - just keep user info, no password checking
        self.connected_users[websocket] = {
            'username': username,
            'authenticated': True
        }
        
        await websocket.send(json.dumps({
            'type': 'auth_response',
            'success': True,
            'username': username,
            'message': 'Ready to debate!'
        }))
        
        logger.info(f"User {username} joined (no password needed)")
            

        
    async def handle_create_account(self, websocket, data):
        """NO ACCOUNT CREATION NEEDED - just use any username"""
        await websocket.send(json.dumps({
            'type': 'account_creation_response',
            'success': True,
            'message': 'No account needed! Just pick any username to debate.'
        }))
            
    async def handle_join_matchmaking(self, websocket, data):
        """SIMPLE MATCHMAKING - add to queue, match if 2+ users"""
        if websocket not in self.connected_users or not self.connected_users[websocket].get('authenticated'):
            await websocket.send(json.dumps({
                'type': 'error',
                'message': 'Not authenticated'
            }))
            return
            
        user_info = self.connected_users[websocket]
        
        # Add to waiting queue if not already there
        if websocket not in self.waiting_queue:
            self.waiting_queue.append(websocket)
            logger.info(f"User {user_info['username']} joined queue. Queue size: {len(self.waiting_queue)}")
        
        # Try to match users
        if len(self.waiting_queue) >= 2:
            await self.create_instant_debate()
        else:
            await websocket.send(json.dumps({
                'type': 'waiting',
                'message': f'Waiting for opponent... ({len(self.waiting_queue)}/2)',
                'queue_size': len(self.waiting_queue)
            }))
            
    async def handle_leave_matchmaking(self, websocket, data):
        """SIMPLE LEAVE QUEUE"""
        if websocket in self.waiting_queue:
            self.waiting_queue.remove(websocket)
            await websocket.send(json.dumps({
                'type': 'queue_left', 
                'message': 'Left queue'
            }))
            logger.info("User left matchmaking queue")
            

            
    async def handle_ping(self, websocket, data):
        """Handle basic ping requests"""
        timestamp = data.get('timestamp', datetime.now().isoformat())
        await websocket.send(json.dumps({
            'type': 'pong',
            'timestamp': timestamp
        }))
        
    async def create_instant_debate(self):
        """FORCE CREATE DEBATE - grab two users and throw them in a room"""
        if len(self.waiting_queue) < 2:
            return
            
        # Grab two users
        user1_ws = self.waiting_queue.pop(0)
        user2_ws = self.waiting_queue.pop(0)
        
        user1_info = self.connected_users[user1_ws]
        user2_info = self.connected_users[user2_ws]
        
        # Create debate
        self.debate_counter += 1
        debate_id = self.debate_counter
        
        topics = [
            "Social media does more harm than good",
            "AI will replace most human jobs",
            "Remote work is better than office work",
            "Video games should be considered a sport",
            "Cryptocurrency is the future of money"
        ]
        topic = topics[debate_id % len(topics)]
        
        debate_info = {
            'id': debate_id,
            'topic': topic,
            'user1_ws': user1_ws,
            'user2_ws': user2_ws,
            'user1_name': user1_info['username'],
            'user2_name': user2_info['username'],
            'start_time': datetime.now(),
            'messages': [],
            'duration_minutes': 5
        }
        
        self.active_debates[debate_id] = debate_info
        
        # Tell both users the debate started
        start_msg1 = {
            'type': 'debate_started',
            'debate_id': debate_id,
            'topic': topic,
            'your_side': 'Pro',
            'opponent': user2_info['username'],
            'duration_minutes': 5,
            'message': 'Debate started! You have 5 minutes. Go!'
        }
        
        start_msg2 = {
            'type': 'debate_started', 
            'debate_id': debate_id,
            'topic': topic,
            'your_side': 'Con',
            'opponent': user1_info['username'],
            'duration_minutes': 5,
            'message': 'Debate started! You have 5 minutes. Go!'
        }
        
        await user1_ws.send(json.dumps(start_msg1))
        await user2_ws.send(json.dumps(start_msg2))
        
        logger.info(f"🥊 DEBATE {debate_id} STARTED: {user1_info['username']} vs {user2_info['username']}")
        logger.info(f"📝 Topic: {topic}")
        
        # Start 5-minute timer
        asyncio.create_task(self.debate_timer(debate_id))
        
    async def handle_debate_message(self, websocket, data):
        """SIMPLE MESSAGE HANDLING - find debate and broadcast"""
        message_text = data.get('content', '').strip()
        if not message_text:
            return
            
        # Find which debate this user is in
        user_info = self.connected_users.get(websocket)
        if not user_info:
            return
            
        debate_id = None
        for did, debate in self.active_debates.items():
            if websocket in [debate['user1_ws'], debate['user2_ws']]:
                debate_id = did
                break
                
        if not debate_id:
            await websocket.send(json.dumps({
                'type': 'error',
                'message': 'You are not in an active debate'
            }))
            return
            
        debate = self.active_debates[debate_id]
        sender = user_info['username']
        timestamp = datetime.now().strftime('%H:%M:%S')
        
        # Log the message
        message_entry = {
            'sender': sender,
            'message': message_text,
            'timestamp': timestamp
        }
        debate['messages'].append(message_entry)
        
        # Send to both users
        broadcast_msg = {
            'type': 'debate_message',
            'sender': sender,
            'message': message_text,
            'timestamp': timestamp
        }
        
        try:
            await debate['user1_ws'].send(json.dumps(broadcast_msg))
            await debate['user2_ws'].send(json.dumps(broadcast_msg))
        except:
            pass  # Handle disconnections
            
        logger.info(f"💬 [{debate_id}] {sender}: {message_text[:50]}...")
        
    async def debate_timer(self, debate_id):
        """FORCE END DEBATE after 5 minutes"""
        await asyncio.sleep(5 * 60)  # 5 minutes
        await self.end_debate(debate_id)
        
    async def end_debate(self, debate_id):
        """FORCE END DEBATE and save log"""
        if debate_id not in self.active_debates:
            return
            
        debate = self.active_debates[debate_id]
        end_time = datetime.now()
        
        # Save to database
        self.save_debate_log(debate, end_time)
        
        # Tell users it's over
        end_msg = {
            'type': 'debate_ended',
            'message': f'Debate finished! {len(debate["messages"])} messages exchanged.',
            'total_messages': len(debate['messages']),
            'can_join_new': True
        }
        
        try:
            await debate['user1_ws'].send(json.dumps(end_msg))
            await debate['user2_ws'].send(json.dumps(end_msg))
        except:
            pass
            
        logger.info(f"🏁 DEBATE {debate_id} ENDED - {len(debate['messages'])} messages saved")
        
        # Clean up
        del self.active_debates[debate_id]
        
    async def end_debate_early(self, debate_id):
        """End debate early if someone leaves"""
        await self.end_debate(debate_id)
        
    def save_debate_log(self, debate, end_time):
        """Save debate to database"""
        try:
            messages_json = json.dumps(debate['messages'])
            duration = int((end_time - debate['start_time']).total_seconds() / 60)
            
            # Simple database save - add to debates table
            conn = self.database.get_connection()
            cursor = conn.cursor()
            
            if self.database.use_postgres:
                cursor.execute('''
                    INSERT INTO debates (user1_id, user2_id, topic, log, timestamp)
                    VALUES ((SELECT id FROM users WHERE username = %s), 
                           (SELECT id FROM users WHERE username = %s), 
                           %s, %s, %s)
                ''', (debate['user1_name'], debate['user2_name'], 
                     debate['topic'], messages_json, end_time))
            else:
                cursor.execute('''
                    INSERT INTO debates (user1_id, user2_id, topic, log, timestamp)
                    VALUES ((SELECT id FROM users WHERE username = ?), 
                           (SELECT id FROM users WHERE username = ?), 
                           ?, ?, ?)
                ''', (debate['user1_name'], debate['user2_name'], 
                     debate['topic'], messages_json, end_time))
                
            conn.commit()
            conn.close()
            
            logger.info(f"💾 Debate saved: {debate['user1_name']} vs {debate['user2_name']}")
            
        except Exception as e:
            logger.error(f"Failed to save debate: {e}")

async def main():
    """Main server entry point (like the chat app)"""
    server = SimpleDebateServer()
    
    # Use same port detection as working chat app
    host = "0.0.0.0"  # Listen on all interfaces
    port = int(os.environ.get("PORT", 8765))  # Cloud platforms use PORT env var
    
    # Check if running in cloud environment (like chat app)
    is_cloud = os.environ.get("DYNO") or os.environ.get("RENDER") or os.environ.get("RAILWAY_ENVIRONMENT")
    
    print("🎯 Simple Debate Platform Server Starting...")
    print("=" * 50)
    if is_cloud:
        print("☁️  Environment: Cloud Deployment")
        print(f"📡 Port: {port}")
        print("✅ Server is ONLINE and accessible from anywhere!")
    else:
        print(f"🌐 Local server: ws://localhost:{port}")
        print("🔗 WebSocket endpoint ready")
    print("=" * 50)
    print("Press Ctrl+C to stop the server")
    
    try:
        # SIMPLE SERVER - no complex matchmaking service needed
        async with websockets.serve(server.handle_client, host, port):
            print("🚀 FORCE MODE: Server running - users will be matched instantly!")
            await asyncio.Future()  # Run forever
    except KeyboardInterrupt:
        print("\n🛑 Server stopped by user")
    except Exception as e:
        print(f"❌ Server error: {e}")

if __name__ == "__main__":
    asyncio.run(main())
