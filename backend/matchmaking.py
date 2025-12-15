import asyncio
import json
from typing import Dict, List, Optional, Tuple

class MatchmakingQueue:
    def __init__(self):
        self.queue: List[Tuple[int, int]] = []
        self.waiting_users: Dict[int, dict] = {}
        self.match_expansion_time = 30
        self.initial_mmr_range = 100
        self.max_mmr_range = 500
        
    def add_to_queue(self, user_id: int, mmr: int, user_info: dict):
        if user_id not in [u[0] for u in self.queue]:
            self.queue.append((user_id, mmr))
            self.waiting_users[user_id] = {
                **user_info,
                'queue_time': asyncio.get_event_loop().time()
            }
            print(f"User {user_id} added to queue with MMR {mmr}")
    
    def remove_from_queue(self, user_id: int):
        self.queue = [(uid, mmr) for uid, mmr in self.queue if uid != user_id]
        if user_id in self.waiting_users:
            del self.waiting_users[user_id]
            print(f"User {user_id} removed from queue")
    
    def get_allowed_mmr_range(self, wait_time: float) -> int:
        expansions = int(wait_time // self.match_expansion_time)
        expanded_range = self.initial_mmr_range + (expansions * 50)
        return min(expanded_range, self.max_mmr_range)
    
    def find_match(self) -> Optional[Tuple[int, int]]:
        if len(self.queue) < 2:
            return None
        
        current_time = asyncio.get_event_loop().time()
        best_match = None
        smallest_diff = float('inf')
        
        for i in range(len(self.queue)):
            for j in range(i + 1, len(self.queue)):
                user1_id, mmr1 = self.queue[i]
                user2_id, mmr2 = self.queue[j]
                
                # Get wait times for both users
                wait_time1 = current_time - self.waiting_users[user1_id]['queue_time']
                wait_time2 = current_time - self.waiting_users[user2_id]['queue_time']
                
                # Use the longer wait time to determine MMR range
                max_wait_time = max(wait_time1, wait_time2)
                allowed_range = self.get_allowed_mmr_range(max_wait_time)
                
                mmr_diff = abs(mmr1 - mmr2)
                
                # Check if this is a valid match within the allowed range
                if mmr_diff <= allowed_range and mmr_diff < smallest_diff:
                    smallest_diff = mmr_diff
                    best_match = (user1_id, user2_id)
        
        if best_match:
            # Remove both users from queue
            self.remove_from_queue(best_match[0])
            self.remove_from_queue(best_match[1])
            print(f"Match found: User {best_match[0]} vs User {best_match[1]} (MMR diff: {smallest_diff})")
        
        return best_match
    
    def get_queue_status(self) -> dict:
        return {
            'queue_size': len(self.queue),
            'waiting_users': list(self.waiting_users.keys())
        }

class Matchmaker:
    def __init__(self, websocket_manager, database):
        self.queue = MatchmakingQueue()
        self.websocket_manager = websocket_manager
        self.database = database
        self.running = False
        self.match_check_interval = 2
        
    async def start_matchmaking_service(self):
        self.running = True
        print("Matchmaking service started")
        
        while self.running:
            try:
                match = self.queue.find_match()
                if match:
                    print(f"Match found: {match[0]} vs {match[1]}")
                    await self.create_match(match[0], match[1])
                
                await asyncio.sleep(self.match_check_interval)
            except Exception as e:
                print(f"Error in matchmaking service: {e}")
                await asyncio.sleep(self.match_check_interval)
    
    def stop_matchmaking_service(self):
        """Stop the matchmaking service"""
        self.running = False
        print("Matchmaking service stopped")
    
    async def add_user_to_queue(self, user_id: int, websocket):
        """Add a user to the matchmaking queue"""
        user_info = self.database.get_user_by_id(user_id)
        if not user_info:
            await self.websocket_manager.send_to_user(user_id, {
                'type': 'error',
                'message': 'User not found'
            })
            return
        
        # Add user to queue
        self.queue.add_to_queue(user_id, user_info['mmr'], user_info)
        
        # Store the websocket connection
        self.websocket_manager.add_connection(user_id, websocket)
        
        print(f"Added user {user_info['username']} (ID: {user_id}) to matchmaking queue")
        print(f"Queue status: {self.queue.get_queue_status()}")
        
        # Send confirmation to user
        await self.websocket_manager.send_to_user(user_id, {
            'type': 'queue_joined',
            'message': 'Searching for opponent...',
            'queue_status': self.queue.get_queue_status()
        })
    
    async def remove_user_from_queue(self, user_id: int):
        """Remove a user from the matchmaking queue"""
        self.queue.remove_from_queue(user_id)
        
        # Send confirmation to user
        await self.websocket_manager.send_to_user(user_id, {
            'type': 'queue_left',
            'message': 'Removed from matchmaking queue'
        })
    
    async def create_match(self, user1_id: int, user2_id: int):
        """Create a debate match between two users"""
        try:
            # Get user information
            user1_info = self.database.get_user_by_id(user1_id)
            user2_info = self.database.get_user_by_id(user2_id)
            
            if not user1_info or not user2_info:
                print(f"Error: Could not find user info for match {user1_id} vs {user2_id}")
                return
            
            # Get random topic
            topic = self.database.get_random_topic()
            
            # Create debate in database
            debate_id = self.database.create_debate(user1_id, user2_id, topic)
            
            if debate_id is None:
                print(f"Failed to create debate in database")
                error_msg = {
                    'type': 'error',
                    'message': 'Failed to create debate. Please try again.'
                }
                await self.websocket_manager.send_to_user(user1_id, error_msg)
                await self.websocket_manager.send_to_user(user2_id, error_msg)
                return
            
            # Notify both users of the match
            match_data = {
                'type': 'match_found',
                'debate_id': debate_id,
                'topic': topic,
                'opponent': {
                    'id': user2_id,
                    'username': user2_info['username'],
                    'mmr': user2_info['mmr']
                }
            }
            
            # Send to user1 with user2's info
            await self.websocket_manager.send_to_user(user1_id, match_data)
            
            # Send to user2 with user1's info (swap opponent info)
            match_data['opponent'] = {
                'id': user1_id,
                'username': user1_info['username'],
                'mmr': user1_info['mmr']
            }
            await self.websocket_manager.send_to_user(user2_id, match_data)
            
            print(f"Match created: Debate {debate_id} between {user1_info['username']} and {user2_info['username']}")
            
        except Exception as e:
            print(f"Error creating match: {e}")
            # Notify users of error
            error_msg = {
                'type': 'error',
                'message': 'Failed to create match. Please try again.'
            }
            await self.websocket_manager.send_to_user(user1_id, error_msg)
            await self.websocket_manager.send_to_user(user2_id, error_msg)
