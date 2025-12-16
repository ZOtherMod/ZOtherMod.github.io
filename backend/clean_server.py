#!/usr/bin/env python3
"""
Clean Debate Platform Server
A simplified, readable implementation for real-time debates
"""

import asyncio
import json
import logging
import websockets
from datetime import datetime
from database import Database

# Set up clear, informative logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class DebatePlatform:
    """
    Main debate platform server
    Handles user connections, matchmaking, and debate sessions
    """
    
    def __init__(self):
        # Initialize database connection
        self.db = Database()
        
        # Track connected users
        self.users = {}  # websocket -> user_data
        
        # Matchmaking queue
        self.queue = []  # list of users waiting for matches
        
        # Active debate sessions
        self.debates = {}  # debate_id -> debate_data
        self.next_debate_id = 1
        
        logger.info("Debate Platform initialized")
    
    async def handle_connection(self, websocket, path):
        """
        Handle new WebSocket connections
        This is the main entry point for all client interactions
        """
        try:
            logger.info("New client connected")
            await self.register_user(websocket)
            
            # Listen for messages from this client
            async for message in websocket:
                await self.process_message(websocket, message)
                
        except websockets.exceptions.ConnectionClosed:
            logger.info("Client disconnected normally")
        except Exception as e:
            logger.error(f"Error handling connection: {e}")
        finally:
            await self.cleanup_user(websocket)
    
    async def register_user(self, websocket):
        """Register a new user connection"""
        self.users[websocket] = {
            'authenticated': False,
            'username': None,
            'user_id': None,
            'in_queue': False,
            'in_debate': False
        }
        logger.info("User registered, waiting for authentication")
    
    async def cleanup_user(self, websocket):
        """Clean up when a user disconnects"""
        if websocket in self.users:
            user_data = self.users[websocket]
            username = user_data.get('username', 'Unknown')
            
            # Remove from queue if waiting
            if websocket in self.queue:
                self.queue.remove(websocket)
                logger.info(f"Removed {username} from matchmaking queue")
            
            # Handle debate cleanup if in active debate
            if user_data.get('in_debate'):
                await self.handle_user_left_debate(websocket)
            
            # Remove user record
            del self.users[websocket]
            logger.info(f"Cleaned up user: {username}")
    
    async def process_message(self, websocket, message):
        """
        Process incoming messages from clients
        Routes messages to appropriate handlers based on type
        """
        try:
            data = json.loads(message)
            message_type = data.get('type')
            
            logger.info(f"Received message type: {message_type}")
            
            # Route to appropriate handler
            handlers = {
                'authenticate': self.handle_authentication,
                'join_matchmaking': self.handle_join_matchmaking,
                'leave_matchmaking': self.handle_leave_matchmaking,
                'debate_message': self.handle_debate_message,
                'start_debate': self.handle_start_debate
            }
            
            handler = handlers.get(message_type)
            if handler:
                await handler(websocket, data)
            else:
                await self.send_error(websocket, f"Unknown message type: {message_type}")
                
        except json.JSONDecodeError:
            await self.send_error(websocket, "Invalid JSON format")
        except Exception as e:
            logger.error(f"Error processing message: {e}")
            await self.send_error(websocket, "Internal server error")
    
    async def handle_authentication(self, websocket, data):
        """
        Handle user authentication
        Validates credentials and sets up user session
        """
        username = data.get('username', '').strip()
        password = data.get('password', '')
        
        if not username or not password:
            await self.send_error(websocket, "Username and password required")
            return
        
        # Authenticate with database
        auth_result = self.db.authenticate_user(username, password)
        
        if auth_result['success']:
            # Update user data
            self.users[websocket].update({
                'authenticated': True,
                'username': username,
                'user_id': auth_result['user_id'],
                'mmr': auth_result['mmr'],
                'user_class': auth_result['user_class']
            })
            
            # Send success response
            await self.send_message(websocket, {
                'type': 'auth_response',
                'success': True,
                'user_data': {
                    'username': username,
                    'user_id': auth_result['user_id'],
                    'mmr': auth_result['mmr'],
                    'user_class': auth_result['user_class']
                }
            })
            
            logger.info(f"User authenticated: {username}")
        else:
            await self.send_error(websocket, auth_result['error'])
    
    async def handle_join_matchmaking(self, websocket, data):
        """
        Add user to matchmaking queue
        Attempts to find a match immediately
        """
        user_data = self.users.get(websocket)
        
        if not user_data or not user_data['authenticated']:
            await self.send_error(websocket, "Must be authenticated to join matchmaking")
            return
        
        if user_data['in_queue']:
            await self.send_error(websocket, "Already in matchmaking queue")
            return
        
        if user_data['in_debate']:
            await self.send_error(websocket, "Already in a debate")
            return
        
        # Add to queue
        self.queue.append(websocket)
        user_data['in_queue'] = True
        
        await self.send_message(websocket, {
            'type': 'queue_joined',
            'position': len(self.queue),
            'message': 'Looking for an opponent...'
        })
        
        logger.info(f"User {user_data['username']} joined matchmaking queue")
        
        # Try to make a match
        await self.attempt_matchmaking()
    
    async def handle_leave_matchmaking(self, websocket, data):
        """Remove user from matchmaking queue"""
        user_data = self.users.get(websocket)
        
        if websocket in self.queue:
            self.queue.remove(websocket)
            user_data['in_queue'] = False
            
            await self.send_message(websocket, {
                'type': 'left_queue',
                'message': 'Left matchmaking queue'
            })
            
            logger.info(f"User {user_data['username']} left matchmaking queue")
    
    async def attempt_matchmaking(self):
        """
        Try to match users in the queue
        Creates new debate sessions for matched pairs
        """
        if len(self.queue) < 2:
            return  # Need at least 2 users to make a match
        
        # Simple matching: take first two users
        user1_ws = self.queue.pop(0)
        user2_ws = self.queue.pop(0)
        
        user1_data = self.users[user1_ws]
        user2_data = self.users[user2_ws]
        
        # Update user states
        user1_data['in_queue'] = False
        user2_data['in_queue'] = False
        user1_data['in_debate'] = True
        user2_data['in_debate'] = True
        
        # Create debate session
        debate_id = self.next_debate_id
        self.next_debate_id += 1
        
        # Get random topic
        topic = self.db.get_random_topic()
        
        # Assign sides randomly
        import random
        if random.choice([True, False]):
            pro_user, con_user = user1_ws, user2_ws
        else:
            pro_user, con_user = user2_ws, user1_ws
        
        # Create debate data
        debate_data = {
            'id': debate_id,
            'topic': topic,
            'user1': user1_ws,
            'user2': user2_ws,
            'pro_user': pro_user,
            'con_user': con_user,
            'status': 'starting',
            'messages': [],
            'start_time': datetime.now(),
            'current_turn': None
        }
        
        self.debates[debate_id] = debate_data
        
        # Store debate IDs in user data
        user1_data['debate_id'] = debate_id
        user2_data['debate_id'] = debate_id
        
        # Notify both users
        await self.notify_match_found(user1_ws, user2_ws, debate_data)
        
        logger.info(f"Created debate {debate_id}: {user1_data['username']} vs {user2_data['username']}")
    
    async def notify_match_found(self, user1_ws, user2_ws, debate_data):
        """Notify both users that a match was found and debate is starting"""
        
        user1_data = self.users[user1_ws]
        user2_data = self.users[user2_ws]
        
        # Determine sides for each user
        user1_side = 'pro' if debate_data['pro_user'] == user1_ws else 'con'
        user2_side = 'pro' if debate_data['pro_user'] == user2_ws else 'con'
        
        # Send match notifications
        await self.send_message(user1_ws, {
            'type': 'match_found',
            'opponent': {
                'username': user2_data['username'],
                'mmr': user2_data['mmr']
            },
            'topic': debate_data['topic'],
            'your_side': user1_side,
            'debate_id': debate_data['id']
        })
        
        await self.send_message(user2_ws, {
            'type': 'match_found',
            'opponent': {
                'username': user1_data['username'],
                'mmr': user1_data['mmr']
            },
            'topic': debate_data['topic'],
            'your_side': user2_side,
            'debate_id': debate_data['id']
        })
        
        # Start the debate after a short delay
        await asyncio.sleep(2)
        await self.start_debate(debate_data['id'])
    
    async def start_debate(self, debate_id):
        """Start the actual debate session"""
        debate_data = self.debates.get(debate_id)
        if not debate_data:
            return
        
        debate_data['status'] = 'active'
        
        # Notify both users that debate has started
        message = {
            'type': 'debate_started',
            'debate_id': debate_id,
            'topic': debate_data['topic'],
            'message': 'Debate has begun! You have 3 minutes of preparation time.'
        }
        
        await self.send_message(debate_data['user1'], message)
        await self.send_message(debate_data['user2'], message)
        
        # Start preparation timer
        await self.start_preparation_phase(debate_id)
    
    async def start_preparation_phase(self, debate_id):
        """Start the 3-minute preparation phase"""
        debate_data = self.debates.get(debate_id)
        if not debate_data:
            return
        
        prep_time = 180  # 3 minutes in seconds
        
        # Send preparation timer updates
        for remaining in range(prep_time, 0, -30):  # Update every 30 seconds
            if debate_id not in self.debates:  # Debate ended early
                return
            
            minutes = remaining // 60
            seconds = remaining % 60
            
            timer_message = {
                'type': 'prep_timer',
                'remaining_seconds': remaining,
                'display': f"{minutes:02d}:{seconds:02d}",
                'message': 'Preparation time remaining'
            }
            
            await self.send_message(debate_data['user1'], timer_message)
            await self.send_message(debate_data['user2'], timer_message)
            
            await asyncio.sleep(30)
        
        # Preparation phase over
        await self.start_debate_phase(debate_id)
    
    async def start_debate_phase(self, debate_id):
        """Start the main debate phase"""
        debate_data = self.debates.get(debate_id)
        if not debate_data:
            return
        
        debate_data['status'] = 'debating'
        debate_data['current_turn'] = debate_data['pro_user']  # Pro side starts
        
        # Notify users that debate phase has started
        start_message = {
            'type': 'debate_phase_start',
            'message': 'Preparation time is over. The debate begins now!'
        }
        
        await self.send_message(debate_data['user1'], start_message)
        await self.send_message(debate_data['user2'], start_message)
        
        # Notify whose turn it is
        await self.notify_turn(debate_id)
    
    async def notify_turn(self, debate_id):
        """Notify users whose turn it is to speak"""
        debate_data = self.debates.get(debate_id)
        if not debate_data:
            return
        
        current_user = debate_data['current_turn']
        other_user = debate_data['user2'] if current_user == debate_data['user1'] else debate_data['user1']
        
        current_user_data = self.users[current_user]
        current_side = 'pro' if current_user == debate_data['pro_user'] else 'con'
        
        # Tell current user it's their turn
        await self.send_message(current_user, {
            'type': 'your_turn',
            'side': current_side,
            'message': f"It's your turn to present your {current_side} argument."
        })
        
        # Tell other user to wait
        await self.send_message(other_user, {
            'type': 'opponent_turn',
            'message': f"Waiting for {current_user_data['username']}'s argument..."
        })
    
    async def handle_debate_message(self, websocket, data):
        """Handle messages sent during debates"""
        user_data = self.users.get(websocket)
        
        if not user_data or not user_data['in_debate']:
            await self.send_error(websocket, "Not in an active debate")
            return
        
        debate_id = user_data['debate_id']
        debate_data = self.debates.get(debate_id)
        
        if not debate_data or debate_data['status'] != 'debating':
            await self.send_error(websocket, "Debate not active")
            return
        
        if debate_data['current_turn'] != websocket:
            await self.send_error(websocket, "Not your turn to speak")
            return
        
        content = data.get('content', '').strip()
        if not content:
            await self.send_error(websocket, "Message cannot be empty")
            return
        
        # Create message record
        message = {
            'sender_id': user_data['user_id'],
            'sender_username': user_data['username'],
            'content': content,
            'timestamp': datetime.now().isoformat(),
            'side': 'pro' if websocket == debate_data['pro_user'] else 'con'
        }
        
        # Add to debate log
        debate_data['messages'].append(message)
        
        # Broadcast message to both users
        broadcast_message = {
            'type': 'debate_message',
            **message
        }
        
        await self.send_message(debate_data['user1'], broadcast_message)
        await self.send_message(debate_data['user2'], broadcast_message)
        
        # Switch turns
        other_user = debate_data['user2'] if websocket == debate_data['user1'] else debate_data['user1']
        debate_data['current_turn'] = other_user
        
        await self.notify_turn(debate_id)
        
        logger.info(f"Debate message from {user_data['username']}: {content[:50]}...")
    
    async def handle_user_left_debate(self, websocket):
        """Handle when a user leaves an active debate"""
        user_data = self.users.get(websocket)
        if not user_data or not user_data.get('debate_id'):
            return
        
        debate_id = user_data['debate_id']
        debate_data = self.debates.get(debate_id)
        
        if debate_data:
            # Notify the other user
            other_user = debate_data['user2'] if websocket == debate_data['user1'] else debate_data['user1']
            
            if other_user in self.users:
                await self.send_message(other_user, {
                    'type': 'opponent_left',
                    'message': 'Your opponent has left the debate.'
                })
                
                # Clean up other user's state
                self.users[other_user]['in_debate'] = False
                self.users[other_user]['debate_id'] = None
            
            # Remove debate
            del self.debates[debate_id]
            logger.info(f"Debate {debate_id} ended due to user disconnect")
    
    async def send_message(self, websocket, message):
        """Send a message to a specific client"""
        try:
            await websocket.send(json.dumps(message))
        except websockets.exceptions.ConnectionClosed:
            logger.warning("Tried to send message to closed connection")
        except Exception as e:
            logger.error(f"Error sending message: {e}")
    
    async def send_error(self, websocket, error_message):
        """Send an error message to a client"""
        await self.send_message(websocket, {
            'type': 'error',
            'message': error_message
        })
    
    def start_server(self, host='localhost', port=8765):
        """Start the WebSocket server"""
        logger.info(f"Starting Debate Platform server on {host}:{port}")
        
        return websockets.serve(
            self.handle_connection,
            host,
            port,
            ping_interval=20,
            ping_timeout=10,
            close_timeout=10
        )


async def main():
    """Main server entry point"""
    # Create server instance
    server = DebatePlatform()
    
    # Start the WebSocket server
    start_server = server.start_server()
    
    print("🎯 DEBATE PLATFORM SERVER")
    print("=" * 40)
    print("🌐 Server: ws://localhost:8765")
    print("👥 Ready for real-time debates")
    print("📝 Check logs for connection details")
    print("=" * 40)
    print("Press Ctrl+C to stop the server")
    
    try:
        await start_server
        await asyncio.Future()  # Run forever
    except KeyboardInterrupt:
        print("\n⏹️  Server stopped by user")
    except Exception as e:
        logger.error(f"Server error: {e}")


if __name__ == "__main__":
    asyncio.run(main())
