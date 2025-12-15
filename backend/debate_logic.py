import asyncio
import json
from typing import Dict, List, Optional
from datetime import datetime, timedelta

class DebateSession:
    def __init__(self, debate_id, user1_id, user2_id, topic, websocket_manager, database):
        self.debate_id = debate_id
        self.user1_id = user1_id
        self.user2_id = user2_id
        self.topic = topic
        self.websocket_manager = websocket_manager
        self.database = database
        
        # Side assignment - user1 gets Proposition, user2 gets Negation
        self.user1_side = 'Proposition'
        self.user2_side = 'Negation'
        
        # Debate flow control
        self.phase = 'preparation'  # preparation, debate, ended
        self.current_turn = user1_id  # Who's turn it is
        self.turn_count = 0
        self.max_turns = 6  # 3 turns per player
        
        # Timing
        self.prep_time_minutes = 3
        self.turn_time_minutes = 2
        self.prep_start_time = None
        self.turn_start_time = None
        
        # Debate log
        self.messages = []
        
        # Timers
        self.prep_timer_task = None
        self.turn_timer_task = None
    
    async def start_debate(self):
        """Start the debate session"""
        print(f"Starting debate {self.debate_id}: {self.topic}")
        print(f"User1 ({self.user1_id}) side: {self.user1_side}")
        print(f"User2 ({self.user2_id}) side: {self.user2_side}")
        
        # Send initial topic and preparation timer with side assignments
        await self.websocket_manager.send_to_user(self.user1_id, {
            'type': 'debate_started',
            'debate_id': self.debate_id,
            'topic': self.topic,
            'prep_time_minutes': self.prep_time_minutes,
            'your_side': self.user1_side,
            'opponent_side': self.user2_side
        })
        
        await self.websocket_manager.send_to_user(self.user2_id, {
            'type': 'debate_started',
            'debate_id': self.debate_id,
            'topic': self.topic,
            'prep_time_minutes': self.prep_time_minutes,
            'your_side': self.user2_side,
            'opponent_side': self.user1_side
        })
        
        # Start preparation phase
        await self.start_preparation_phase()
    
    async def start_preparation_phase(self):
        """Start the preparation timer"""
        self.phase = 'preparation'
        self.prep_start_time = datetime.now()
        
        # Send preparation timer start
        await self.send_to_both_users({
            'type': 'prep_timer_start',
            'duration_minutes': self.prep_time_minutes
        })
        
        # Start countdown
        self.prep_timer_task = asyncio.create_task(
            self.preparation_countdown()
        )
    
    async def preparation_countdown(self):
        """Handle preparation phase countdown"""
        prep_duration = int(self.prep_time_minutes * 60)  # Convert to seconds and ensure integer
        
        for remaining in range(prep_duration, -1, -1):
            if self.phase != 'preparation':
                return
            
            minutes = remaining // 60
            seconds = remaining % 60
            
            await self.send_to_both_users({
                'type': 'prep_timer',
                'remaining_seconds': remaining,
                'display': f"{minutes:02d}:{seconds:02d}"
            })
            
            if remaining == 0:
                await self.start_debate_phase()
                return
            
            await asyncio.sleep(1)
    
    async def start_debate_phase(self):
        """Start the main debate phase"""
        self.phase = 'debate'
        self.turn_count = 0
        self.current_turn = self.user1_id
        
        await self.send_to_both_users({
            'type': 'debate_phase_start',
            'message': 'Preparation time is over. The debate begins!'
        })
        
        await self.start_turn()
    
    async def start_turn(self):
        """Start a new turn"""
        if self.turn_count >= self.max_turns:
            await self.end_debate()
            return
        
        self.turn_start_time = datetime.now()
        
        # Determine whose turn it is
        if self.turn_count % 2 == 0:
            self.current_turn = self.user1_id
            other_user = self.user2_id
        else:
            self.current_turn = self.user2_id
            other_user = self.user1_id
        
        # Get current user's side
        current_user_side = self.user1_side if self.current_turn == self.user1_id else self.user2_side
        other_user_side = self.user2_side if self.current_turn == self.user1_id else self.user1_side
        
        # Notify users about the turn
        await self.websocket_manager.send_to_user(self.current_turn, {
            'type': 'your_turn',
            'turn_number': (self.turn_count // 2) + 1,
            'time_limit_minutes': self.turn_time_minutes,
            'your_side': current_user_side
        })
        
        await self.websocket_manager.send_to_user(other_user, {
            'type': 'opponent_turn',
            'turn_number': (self.turn_count // 2) + 1,
            'time_limit_minutes': self.turn_time_minutes,
            'opponent_side': current_user_side,
            'your_side': other_user_side
        })
        
        # Start turn timer
        self.turn_timer_task = asyncio.create_task(
            self.turn_countdown()
        )
    
    async def turn_countdown(self):
        """Handle turn countdown timer"""
        turn_duration = int(self.turn_time_minutes * 60)  # Convert to seconds and ensure integer
        
        for remaining in range(turn_duration, -1, -1):
            if self.phase != 'debate':
                return
            
            minutes = remaining // 60
            seconds = remaining % 60
            
            current_user_side = self.user1_side if self.current_turn == self.user1_id else self.user2_side
            
            await self.send_to_both_users({
                'type': 'turn_timer',
                'remaining_seconds': remaining,
                'display': f"{minutes:02d}:{seconds:02d}",
                'current_turn_user': self.current_turn,
                'current_turn_side': current_user_side
            })
            
            if remaining == 0:
                # Time's up, skip turn
                await self.handle_message(self.current_turn, "[Time expired - no argument submitted]")
                return
            
            await asyncio.sleep(1)
    
    async def handle_message(self, user_id: int, content: str):
        """Handle a message from a user during their turn"""
        if self.phase != 'debate':
            await self.websocket_manager.send_to_user(user_id, {
                'type': 'error',
                'message': 'Debate is not in progress'
            })
            return
        
        if user_id != self.current_turn:
            await self.websocket_manager.send_to_user(user_id, {
                'type': 'error',
                'message': 'It is not your turn'
            })
            return
        
        # Cancel turn timer
        if self.turn_timer_task:
            self.turn_timer_task.cancel()
        
        # Add message to log
        user_info = self.database.get_user_by_id(user_id)
        message_data = {
            'type': 'message',
            'sender_id': user_id,
            'sender_username': user_info['username'] if user_info else 'Unknown',
            'content': content,
            'timestamp': datetime.now().isoformat(),
            'turn_number': (self.turn_count // 2) + 1
        }
        
        self.messages.append(message_data)
        
        # Send message to both users
        await self.send_to_both_users(message_data)
        
        # Update database log
        await self.update_debate_log()
        
        # Move to next turn
        self.turn_count += 1
        await self.start_turn()
    
    async def end_debate(self):
        """End the debate session"""
        self.phase = 'ended'
        
        # Cancel any running timers
        if self.prep_timer_task:
            self.prep_timer_task.cancel()
        if self.turn_timer_task:
            self.turn_timer_task.cancel()
        
        # Send end message to both users
        await self.send_to_both_users({
            'type': 'debate_ended',
            'message': 'Debate has ended',
            'final_log': self.messages,
            'topic': self.topic
        })
        
        print(f"Debate {self.debate_id} ended")
    
    async def send_to_both_users(self, message: dict):
        """Send a message to both users in the debate"""
        await self.websocket_manager.send_to_user(self.user1_id, message)
        await self.websocket_manager.send_to_user(self.user2_id, message)
    
    async def update_debate_log(self):
        """Update the debate log in the database"""
        try:
            log_json = json.dumps(self.messages)
            self.database.update_debate_log(self.debate_id, log_json)
        except Exception as e:
            print(f"Error updating debate log: {e}")
    
    def get_debate_info(self):
        """Get current debate information"""
        return {
            'debate_id': self.debate_id,
            'user1_id': self.user1_id,
            'user2_id': self.user2_id,
            'topic': self.topic,
            'phase': self.phase,
            'current_turn': self.current_turn,
            'turn_count': self.turn_count,
            'messages': self.messages
        }

class DebateManager:
    def __init__(self, websocket_manager, database):
        self.websocket_manager = websocket_manager
        self.database = database
        self.active_debates: Dict[int, DebateSession] = {}  # debate_id -> DebateSession
        self.user_debates: Dict[int, int] = {}  # user_id -> debate_id
    
    async def create_debate_session(self, debate_id: int, user1_id: int, user2_id: int, topic: str):
        """Create and start a new debate session"""
        if debate_id in self.active_debates:
            print(f"Warning: Debate {debate_id} already exists")
            return
        
        session = DebateSession(
            debate_id, user1_id, user2_id, topic, 
            self.websocket_manager, self.database
        )
        
        self.active_debates[debate_id] = session
        self.user_debates[user1_id] = debate_id
        self.user_debates[user2_id] = debate_id
        
        await session.start_debate()
    
    async def handle_user_message(self, user_id: int, content: str):
        """Handle a message from a user"""
        if user_id not in self.user_debates:
            await self.websocket_manager.send_to_user(user_id, {
                'type': 'error',
                'message': 'You are not in an active debate'
            })
            return
        
        debate_id = self.user_debates[user_id]
        if debate_id not in self.active_debates:
            await self.websocket_manager.send_to_user(user_id, {
                'type': 'error',
                'message': 'Debate session not found'
            })
            return
        
        session = self.active_debates[debate_id]
        await session.handle_message(user_id, content)
    
    def get_user_debate_session(self, user_id: int) -> Optional[DebateSession]:
        """Get the debate session for a user"""
        if user_id not in self.user_debates:
            return None
        
        debate_id = self.user_debates[user_id]
        return self.active_debates.get(debate_id)
    
    def remove_debate_session(self, debate_id: int):
        """Remove a completed debate session"""
        if debate_id in self.active_debates:
            session = self.active_debates[debate_id]
            
            # Remove user mappings
            if session.user1_id in self.user_debates:
                del self.user_debates[session.user1_id]
            if session.user2_id in self.user_debates:
                del self.user_debates[session.user2_id]
            
            # Remove session
            del self.active_debates[debate_id]
            print(f"Removed debate session {debate_id}")
    
    def get_active_debates_count(self) -> int:
        """Get the number of active debates"""
        return len(self.active_debates)
