import asyncio
import json
import weakref
from typing import Dict, Optional
import websockets
from websockets.exceptions import ConnectionClosed

class WebSocketManager:
    def __init__(self):
        self.connections: Dict[int, websockets.WebSocketServerProtocol] = {}
        self.user_sessions: Dict[int, dict] = {}  # user_id -> session_info
    
    def add_connection(self, user_id: int, websocket: websockets.WebSocketServerProtocol):
        """Add a WebSocket connection for a user"""
        # Remove old connection if exists
        if user_id in self.connections:
            old_ws = self.connections[user_id]
            if not old_ws.closed:
                asyncio.create_task(old_ws.close())
        
        self.connections[user_id] = websocket
        self.user_sessions[user_id] = {
            'connected_at': asyncio.get_event_loop().time(),
            'active': True
        }
        print(f"WebSocket connection added for user {user_id}")
    
    def remove_connection(self, user_id: int):
        """Remove a WebSocket connection for a user"""
        if user_id in self.connections:
            del self.connections[user_id]
        if user_id in self.user_sessions:
            del self.user_sessions[user_id]
        print(f"WebSocket connection removed for user {user_id}")
    
    async def send_to_user(self, user_id: int, message: dict) -> bool:
        """Send a message to a specific user"""
        if user_id not in self.connections:
            print(f"No WebSocket connection for user {user_id}")
            return False
        
        websocket = self.connections[user_id]
        
        try:
            if websocket.closed:
                print(f"WebSocket connection closed for user {user_id}")
                self.remove_connection(user_id)
                return False
            
            message_json = json.dumps(message)
            await websocket.send(message_json)
            return True
            
        except ConnectionClosed:
            print(f"Connection closed while sending to user {user_id}")
            self.remove_connection(user_id)
            return False
        except Exception as e:
            print(f"Error sending message to user {user_id}: {e}")
            self.remove_connection(user_id)
            return False
    
    async def broadcast_to_all(self, message: dict, exclude_users: Optional[list] = None):
        """Broadcast a message to all connected users"""
        exclude_users = exclude_users or []
        
        for user_id in list(self.connections.keys()):
            if user_id not in exclude_users:
                await self.send_to_user(user_id, message)
    
    def is_user_connected(self, user_id: int) -> bool:
        """Check if a user is currently connected"""
        return user_id in self.connections and not self.connections[user_id].closed
    
    def get_connected_users(self) -> list:
        """Get list of currently connected user IDs"""
        connected = []
        for user_id, websocket in list(self.connections.items()):
            if not websocket.closed:
                connected.append(user_id)
            else:
                self.remove_connection(user_id)
        return connected
    
    def get_connection_count(self) -> int:
        """Get the number of active connections"""
        return len([ws for ws in self.connections.values() if not ws.closed])

class WebSocketHandler:
    def __init__(self, websocket_manager, matchmaker, debate_manager, database):
        self.websocket_manager = websocket_manager
        self.matchmaker = matchmaker
        self.debate_manager = debate_manager
        self.database = database
    
    async def handle_connection(self, websocket, path):
        """Handle a new WebSocket connection"""
        user_id = None
        
        try:
            print(f"New WebSocket connection from {websocket.remote_address}")
            
            async for message in websocket:
                try:
                    data = json.loads(message)
                    response = await self.process_message(data, websocket)
                    
                    if response:
                        # Extract user_id from successful authentication
                        if data.get('type') == 'authenticate' and response.get('success'):
                            user_id = response.get('user_id')
                            if user_id:
                                self.websocket_manager.add_connection(user_id, websocket)
                        
                        await websocket.send(json.dumps(response))
                        
                except json.JSONDecodeError:
                    await websocket.send(json.dumps({
                        'type': 'error',
                        'message': 'Invalid JSON format'
                    }))
                except Exception as e:
                    print(f"Error processing message: {e}")
                    await websocket.send(json.dumps({
                        'type': 'error',
                        'message': 'Internal server error'
                    }))
                    
        except ConnectionClosed:
            print(f"WebSocket connection closed for user {user_id}")
        except Exception as e:
            print(f"WebSocket connection error: {e}")
        finally:
            # Cleanup on disconnect
            if user_id:
                self.websocket_manager.remove_connection(user_id)
                await self.matchmaker.remove_user_from_queue(user_id)
                print(f"Cleaned up connection for user {user_id}")
    
    async def process_message(self, data: dict, websocket) -> Optional[dict]:
        """Process incoming WebSocket messages"""
        message_type = data.get('type')
        
        if message_type == 'authenticate':
            return await self.handle_authentication(data)
        
        elif message_type == 'create_account':
            return await self.handle_account_creation(data)
        
        elif message_type == 'join_matchmaking':
            return await self.handle_join_matchmaking(data, websocket)
        
        elif message_type == 'leave_matchmaking':
            return await self.handle_leave_matchmaking(data)
        
        elif message_type == 'debate_message':
            return await self.handle_debate_message(data)
        
        elif message_type == 'start_debate':
            return await self.handle_start_debate(data)
        
        elif message_type == 'admin_get_data':
            return await self.handle_admin_get_data(data)
        
        elif message_type == 'admin_get_item':
            return await self.handle_admin_get_item(data)
        
        elif message_type == 'admin_update_item':
            return await self.handle_admin_update_item(data)
        
        elif message_type == 'admin_delete_item':
            return await self.handle_admin_delete_item(data)
        
        elif message_type == 'ping':
            return {'type': 'pong', 'timestamp': data.get('timestamp')}
        
        else:
            return {
                'type': 'error',
                'message': f'Unknown message type: {message_type}'
            }
    
    async def handle_authentication(self, data: dict) -> dict:
        """Handle user authentication"""
        username = data.get('username')
        password = data.get('password')
        
        if not username or not password:
            return {
                'type': 'auth_response',
                'success': False,
                'error': 'Username and password are required'
            }
        
        result = self.database.authenticate_user(username, password)
        
        if result is not None:
            return {
                'type': 'auth_response',
                'success': True,
                'user_id': result['id'],
                'mmr': result['mmr'],
                'username': result['username'],
                'user_class': result['user_class']
            }
        else:
            return {
                'type': 'auth_response',
                'success': False,
                'error': 'Invalid username or password'
            }
    
    async def handle_account_creation(self, data: dict) -> dict:
        """Handle account creation"""
        username = data.get('username')
        password = data.get('password')
        
        if not username or not password:
            return {
                'type': 'account_creation_response',
                'success': False,
                'error': 'Username and password are required'
            }
        
        if len(username) < 3:
            return {
                'type': 'account_creation_response',
                'success': False,
                'error': 'Username must be at least 3 characters long'
            }
        
        if len(password) < 6:
            return {
                'type': 'account_creation_response',
                'success': False,
                'error': 'Password must be at least 6 characters long'
            }
        
        user_id = self.database.create_user(username, password)
        
        if user_id is not None:
            return {
                'type': 'account_creation_response',
                'success': True,
                'user_id': user_id,
                'message': 'Account created successfully'
            }
        else:
            return {
                'type': 'account_creation_response',
                'success': False,
                'error': 'Failed to create account. Username may already exist.'
            }
    
    async def handle_join_matchmaking(self, data: dict, websocket) -> dict:
        """Handle joining matchmaking queue"""
        user_id = data.get('user_id')
        
        if not user_id:
            return {
                'type': 'matchmaking_response',
                'success': False,
                'error': 'User ID is required'
            }
        
        # Check if user is already in a debate
        if self.debate_manager.get_user_debate_session(user_id):
            return {
                'type': 'matchmaking_response',
                'success': False,
                'error': 'You are already in an active debate'
            }
        
        await self.matchmaker.add_user_to_queue(user_id, websocket)
        
        return {
            'type': 'matchmaking_response',
            'success': True,
            'message': 'Added to matchmaking queue'
        }
    
    async def handle_leave_matchmaking(self, data: dict) -> dict:
        """Handle leaving matchmaking queue"""
        user_id = data.get('user_id')
        
        if not user_id:
            return {
                'type': 'matchmaking_response',
                'success': False,
                'error': 'User ID is required'
            }
        
        await self.matchmaker.remove_user_from_queue(user_id)
        
        return {
            'type': 'matchmaking_response',
            'success': True,
            'message': 'Removed from matchmaking queue'
        }
    
    async def handle_debate_message(self, data: dict) -> dict:
        """Handle debate message submission"""
        user_id = data.get('user_id')
        content = data.get('content', '').strip()
        
        if not user_id:
            return {
                'type': 'debate_response',
                'success': False,
                'error': 'User ID is required'
            }
        
        if not content:
            return {
                'type': 'debate_response',
                'success': False,
                'error': 'Message content cannot be empty'
            }
        
        if len(content) > 1000:  # Limit message length
            return {
                'type': 'debate_response',
                'success': False,
                'error': 'Message too long (max 1000 characters)'
            }
        
        await self.debate_manager.handle_user_message(user_id, content)
        
        return {
            'type': 'debate_response',
            'success': True,
            'message': 'Message submitted'
        }
    
    async def handle_start_debate(self, data: dict) -> dict:
        """Handle request to start a debate session"""
        user_id = data.get('user_id')
        debate_id = data.get('debate_id')
        
        if not user_id or not debate_id:
            return {
                'type': 'start_debate_response',
                'success': False,
                'error': 'User ID and Debate ID are required'
            }
        
        # Check if debate exists in database
        debate_info = self.database.get_debate_by_id(debate_id)
        if not debate_info:
            return {
                'type': 'start_debate_response',
                'success': False,
                'error': 'Debate not found'
            }
        
        # Check if user is part of this debate
        if user_id != debate_info['user1_id'] and user_id != debate_info['user2_id']:
            return {
                'type': 'start_debate_response',
                'success': False,
                'error': 'You are not a participant in this debate'
            }
        
        # Check if debate session already exists
        existing_session = self.debate_manager.active_debates.get(debate_id)
        if existing_session:
            return {
                'type': 'start_debate_response',
                'success': True,
                'message': 'Debate session already active'
            }
        
        # Create the debate session
        try:
            await self.debate_manager.create_debate_session(
                debate_id,
                debate_info['user1_id'],
                debate_info['user2_id'],
                debate_info['topic']
            )
            
            return {
                'type': 'start_debate_response',
                'success': True,
                'message': 'Debate session started'
            }
            
        except Exception as e:
            print(f"Error starting debate session: {e}")
            return {
                'type': 'start_debate_response',
                'success': False,
                'error': 'Failed to start debate session'
            }
    
    async def handle_admin_get_data(self, data: dict) -> dict:
        """Handle admin request to get data"""
        user_id = data.get('user_id')
        data_type = data.get('data_type')
        
        # Check admin privileges
        user_info = self.database.get_user_by_id(user_id)
        if not user_info or user_info['user_class'] <= 0:
            return {
                'type': 'admin_data_response',
                'success': False,
                'error': 'Admin privileges required'
            }
        
        try:
            if data_type == 'users':
                users = self.database.get_all_users()
                return {
                    'type': 'admin_data_response',
                    'success': True,
                    'data_type': 'users',
                    'data': users
                }
            elif data_type == 'debates':
                debates = self.database.get_all_debates()
                return {
                    'type': 'admin_data_response',
                    'success': True,
                    'data_type': 'debates',
                    'data': debates
                }
            elif data_type == 'topics':
                topics = self.database.get_all_topics()
                return {
                    'type': 'admin_data_response',
                    'success': True,
                    'data_type': 'topics',
                    'data': topics
                }
            else:
                return {
                    'type': 'admin_data_response',
                    'success': False,
                    'error': 'Invalid data type'
                }
        except Exception as e:
            print(f"Error getting admin data: {e}")
            return {
                'type': 'admin_data_response',
                'success': False,
                'error': 'Failed to retrieve data'
            }
    
    async def handle_admin_get_item(self, data: dict) -> dict:
        """Handle admin request to get specific item"""
        user_id = data.get('user_id')
        data_type = data.get('data_type')
        item_id = data.get('item_id')
        
        # Check admin privileges
        user_info = self.database.get_user_by_id(user_id)
        if not user_info or user_info['user_class'] <= 0:
            return {
                'type': 'admin_item_response',
                'success': False,
                'error': 'Admin privileges required'
            }
        
        try:
            if data_type == 'user':
                item = self.database.get_user_by_id(item_id)
            elif data_type == 'debate':
                item = self.database.get_debate_by_id(item_id)
            elif data_type == 'topic':
                item = self.database.get_topic_by_id(item_id)
            else:
                return {
                    'type': 'admin_item_response',
                    'success': False,
                    'error': 'Invalid data type'
                }
            
            if item:
                return {
                    'type': 'admin_item_response',
                    'success': True,
                    'data_type': data_type,
                    'item': item
                }
            else:
                return {
                    'type': 'admin_item_response',
                    'success': False,
                    'error': 'Item not found'
                }
        except Exception as e:
            print(f"Error getting admin item: {e}")
            return {
                'type': 'admin_item_response',
                'success': False,
                'error': 'Failed to retrieve item'
            }
    
    async def handle_admin_update_item(self, data: dict) -> dict:
        """Handle admin request to update item"""
        user_id = data.get('user_id')
        data_type = data.get('data_type')
        item_data = data.get('item_data')
        
        # Check admin privileges
        user_info = self.database.get_user_by_id(user_id)
        if not user_info or user_info['user_class'] <= 0:
            return {
                'type': 'admin_update_response',
                'success': False,
                'error': 'Admin privileges required'
            }
        
        try:
            if data_type == 'user':
                success = self.database.update_user_admin(
                    item_data['id'],
                    item_data.get('username'),
                    item_data.get('mmr'),
                    item_data.get('user_class')
                )
            elif data_type == 'topic':
                success = self.database.update_topic(
                    item_data['id'],
                    item_data.get('topic_text')
                )
            else:
                return {
                    'type': 'admin_update_response',
                    'success': False,
                    'error': 'Invalid data type or read-only'
                }
            
            return {
                'type': 'admin_update_response',
                'success': success,
                'error': None if success else 'Failed to update item'
            }
        except Exception as e:
            print(f"Error updating admin item: {e}")
            return {
                'type': 'admin_update_response',
                'success': False,
                'error': 'Failed to update item'
            }
    
    async def handle_admin_delete_item(self, data: dict) -> dict:
        """Handle admin request to delete item"""
        user_id = data.get('user_id')
        data_type = data.get('data_type')
        item_id = data.get('item_id')
        
        # Check admin privileges
        user_info = self.database.get_user_by_id(user_id)
        if not user_info or user_info['user_class'] <= 0:
            return {
                'type': 'admin_delete_response',
                'success': False,
                'error': 'Admin privileges required'
            }
        
        try:
            if data_type == 'user':
                success = self.database.delete_user(item_id)
            elif data_type == 'debate':
                success = self.database.delete_debate(item_id)
            elif data_type == 'topic':
                success = self.database.delete_topic(item_id)
            else:
                return {
                    'type': 'admin_delete_response',
                    'success': False,
                    'error': 'Invalid data type'
                }
            
            return {
                'type': 'admin_delete_response',
                'success': success,
                'error': None if success else 'Failed to delete item'
            }
        except Exception as e:
            print(f"Error deleting admin item: {e}")
            return {
                'type': 'admin_delete_response',
                'success': False,
                'error': 'Failed to delete item'
            }
