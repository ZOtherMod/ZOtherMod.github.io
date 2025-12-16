#!/usr/bin/env python3
"""
Clean Database Manager for Debate Platform
Handles user authentication, debate storage, and topic management
"""

import sqlite3
import hashlib
import json
import os
from datetime import datetime
from typing import Dict, List, Optional, Any

class Database:
    """
    Database manager for the debate platform
    Handles SQLite operations with clean, readable methods
    """
    
    def __init__(self, db_path: str = 'database/debate.db'):
        """
        Initialize database connection and create tables if needed
        
        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = db_path
        self._ensure_database_directory()
        self._initialize_database()
        print(f"✅ Database initialized: {db_path}")
    
    def _ensure_database_directory(self):
        """Create database directory if it doesn't exist"""
        db_dir = os.path.dirname(self.db_path)
        if db_dir and db_dir != ':memory:':
            os.makedirs(db_dir, exist_ok=True)
    
    def _get_connection(self) -> sqlite3.Connection:
        """
        Get database connection with proper configuration
        
        Returns:
            SQLite connection with row factory enabled
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row  # Enable dict-like access to rows
        conn.execute('PRAGMA foreign_keys = ON')  # Enable foreign key constraints
        return conn
    
    def _initialize_database(self):
        """Create all necessary tables and populate with default data"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # Create tables
            self._create_users_table(cursor)
            self._create_debates_table(cursor)
            self._create_topics_table(cursor)
            
            # Populate with default data
            self._create_default_topics(cursor)
            self._create_test_account(cursor)
            
            conn.commit()
    
    def _create_users_table(self, cursor: sqlite3.Cursor):
        """Create users table with all necessary fields"""
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                mmr INTEGER DEFAULT 1000,
                user_class INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                wins INTEGER DEFAULT 0,
                losses INTEGER DEFAULT 0,
                debates_count INTEGER DEFAULT 0
            )
        ''')
    
    def _create_debates_table(self, cursor: sqlite3.Cursor):
        """Create debates table to store debate history"""
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS debates (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user1_id INTEGER NOT NULL,
                user2_id INTEGER NOT NULL,
                topic TEXT NOT NULL,
                messages TEXT NOT NULL,  -- JSON array of messages
                winner_id INTEGER,
                status TEXT DEFAULT 'completed',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                duration_minutes INTEGER,
                FOREIGN KEY (user1_id) REFERENCES users (id),
                FOREIGN KEY (user2_id) REFERENCES users (id),
                FOREIGN KEY (winner_id) REFERENCES users (id)
            )
        ''')
    
    def _create_topics_table(self, cursor: sqlite3.Cursor):
        """Create topics table for debate topics"""
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS topics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                topic TEXT UNIQUE NOT NULL,
                category TEXT DEFAULT 'general',
                difficulty TEXT DEFAULT 'medium',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
    
    def _create_default_topics(self, cursor: sqlite3.Cursor):
        """Add default debate topics to the database"""
        default_topics = [
            ("Artificial intelligence will benefit humanity more than it will harm it", "technology", "medium"),
            ("Social media does more harm than good to society", "social", "easy"),
            ("Remote work is better than office work", "workplace", "easy"),
            ("Climate change is primarily caused by human activity", "environment", "medium"),
            ("Universal basic income should be implemented globally", "economics", "hard"),
            ("Privacy is more important than security", "society", "medium"),
            ("Space exploration is worth the cost", "science", "medium"),
            ("Nuclear energy is safer than renewable energy", "environment", "hard"),
            ("Standardized testing accurately measures student ability", "education", "medium"),
            ("Video games have a positive impact on mental health", "health", "easy"),
        ]
        
        for topic, category, difficulty in default_topics:
            try:
                cursor.execute(
                    'INSERT OR IGNORE INTO topics (topic, category, difficulty) VALUES (?, ?, ?)',
                    (topic, category, difficulty)
                )
            except sqlite3.IntegrityError:
                pass  # Topic already exists
    
    def _create_test_account(self, cursor: sqlite3.Cursor):
        """Create a test account for development and testing"""
        try:
            password_hash = self._hash_password("testpass")
            cursor.execute('''
                INSERT OR IGNORE INTO users (username, password_hash, mmr, user_class)
                VALUES (?, ?, ?, ?)
            ''', ("testuser", password_hash, 1500, 2))  # user_class 2 = admin
        except sqlite3.IntegrityError:
            pass  # Test account already exists
    
    def _hash_password(self, password: str) -> str:
        """
        Hash a password using SHA-256
        
        Args:
            password: Plain text password
            
        Returns:
            Hashed password as hex string
        """
        return hashlib.sha256(password.encode()).hexdigest()
    
    # User Management Methods
    
    def create_user(self, username: str, password: str, user_class: int = 0) -> Dict[str, Any]:
        """
        Create a new user account
        
        Args:
            username: Unique username
            password: Plain text password (will be hashed)
            user_class: User permission level (0=user, 2=admin)
            
        Returns:
            Dictionary with success status and user data or error message
        """
        if len(username.strip()) < 3:
            return {'success': False, 'error': 'Username must be at least 3 characters'}
        
        if len(password) < 6:
            return {'success': False, 'error': 'Password must be at least 6 characters'}
        
        password_hash = self._hash_password(password)
        
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO users (username, password_hash, user_class)
                    VALUES (?, ?, ?)
                ''', (username.strip(), password_hash, user_class))
                
                user_id = cursor.lastrowid
                conn.commit()
                
                return {
                    'success': True,
                    'user_id': user_id,
                    'username': username.strip(),
                    'mmr': 1000,
                    'user_class': user_class
                }
        except sqlite3.IntegrityError:
            return {'success': False, 'error': 'Username already exists'}
        except Exception as e:
            return {'success': False, 'error': f'Database error: {str(e)}'}
    
    def authenticate_user(self, username: str, password: str) -> Dict[str, Any]:
        """
        Authenticate a user login
        
        Args:
            username: Username to authenticate
            password: Plain text password
            
        Returns:
            Dictionary with success status and user data or error message
        """
        if not username.strip() or not password:
            return {'success': False, 'error': 'Username and password required'}
        
        password_hash = self._hash_password(password)
        
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT id, username, mmr, user_class, wins, losses, debates_count
                    FROM users 
                    WHERE username = ? AND password_hash = ?
                ''', (username.strip(), password_hash))
                
                user = cursor.fetchone()
                
                if user:
                    return {
                        'success': True,
                        'user_id': user['id'],
                        'username': user['username'],
                        'mmr': user['mmr'],
                        'user_class': user['user_class'],
                        'wins': user['wins'],
                        'losses': user['losses'],
                        'debates_count': user['debates_count']
                    }
                else:
                    return {'success': False, 'error': 'Invalid username or password'}
        except Exception as e:
            return {'success': False, 'error': f'Database error: {str(e)}'}
    
    def get_user_by_id(self, user_id: int) -> Optional[Dict[str, Any]]:
        """
        Get user information by user ID
        
        Args:
            user_id: User ID to look up
            
        Returns:
            User data dictionary or None if not found
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT id, username, mmr, user_class, wins, losses, debates_count
                    FROM users WHERE id = ?
                ''', (user_id,))
                
                user = cursor.fetchone()
                return dict(user) if user else None
        except Exception:
            return None
    
    def update_user_mmr(self, user_id: int, new_mmr: int) -> bool:
        """
        Update a user's MMR (Matchmaking Rating)
        
        Args:
            user_id: User ID to update
            new_mmr: New MMR value
            
        Returns:
            True if successful, False otherwise
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    UPDATE users SET mmr = ? WHERE id = ?
                ''', (new_mmr, user_id))
                conn.commit()
                return cursor.rowcount > 0
        except Exception:
            return False
    
    # Topic Management Methods
    
    def get_random_topic(self) -> str:
        """
        Get a random debate topic
        
        Returns:
            Random topic string
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT topic FROM topics ORDER BY RANDOM() LIMIT 1')
                result = cursor.fetchone()
                
                if result:
                    return result['topic']
                else:
                    # Fallback topic if database is empty
                    return "Technology has improved the quality of human life"
        except Exception:
            return "Technology has improved the quality of human life"
    
    def get_all_topics(self) -> List[Dict[str, Any]]:
        """
        Get all available topics
        
        Returns:
            List of topic dictionaries
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT id, topic, category, difficulty 
                    FROM topics 
                    ORDER BY category, topic
                ''')
                return [dict(row) for row in cursor.fetchall()]
        except Exception:
            return []
    
    def add_topic(self, topic: str, category: str = 'general', difficulty: str = 'medium') -> bool:
        """
        Add a new debate topic
        
        Args:
            topic: Topic text
            category: Topic category
            difficulty: Topic difficulty level
            
        Returns:
            True if successful, False otherwise
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO topics (topic, category, difficulty)
                    VALUES (?, ?, ?)
                ''', (topic.strip(), category, difficulty))
                conn.commit()
                return True
        except sqlite3.IntegrityError:
            return False  # Topic already exists
        except Exception:
            return False
    
    # Debate Management Methods
    
    def save_debate(self, user1_id: int, user2_id: int, topic: str, 
                   messages: List[Dict], winner_id: Optional[int] = None,
                   duration_minutes: Optional[int] = None) -> Optional[int]:
        """
        Save a completed debate to the database
        
        Args:
            user1_id: First user's ID
            user2_id: Second user's ID
            topic: Debate topic
            messages: List of debate messages
            winner_id: Winner's ID (optional)
            duration_minutes: Debate duration in minutes
            
        Returns:
            Debate ID if successful, None otherwise
        """
        try:
            messages_json = json.dumps(messages)
            
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO debates (user1_id, user2_id, topic, messages, winner_id, duration_minutes)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (user1_id, user2_id, topic, messages_json, winner_id, duration_minutes))
                
                debate_id = cursor.lastrowid
                
                # Update user statistics
                self._update_user_stats(cursor, user1_id, winner_id)
                self._update_user_stats(cursor, user2_id, winner_id)
                
                conn.commit()
                return debate_id
        except Exception as e:
            print(f"Error saving debate: {e}")
            return None
    
    def _update_user_stats(self, cursor: sqlite3.Cursor, user_id: int, winner_id: Optional[int]):
        """Update user statistics after a debate"""
        cursor.execute('''
            UPDATE users SET 
                debates_count = debates_count + 1,
                wins = wins + ?,
                losses = losses + ?
            WHERE id = ?
        ''', (
            1 if winner_id == user_id else 0,  # wins
            1 if winner_id and winner_id != user_id else 0,  # losses
            user_id
        ))
    
    def get_user_debates(self, user_id: int, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get recent debates for a user
        
        Args:
            user_id: User ID
            limit: Maximum number of debates to return
            
        Returns:
            List of debate dictionaries
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT d.id, d.topic, d.created_at, d.duration_minutes,
                           u1.username as opponent_username,
                           CASE 
                               WHEN d.winner_id = ? THEN 'won'
                               WHEN d.winner_id IS NULL THEN 'draw'
                               ELSE 'lost'
                           END as result
                    FROM debates d
                    JOIN users u1 ON (d.user1_id = u1.id OR d.user2_id = u1.id) AND u1.id != ?
                    WHERE d.user1_id = ? OR d.user2_id = ?
                    ORDER BY d.created_at DESC
                    LIMIT ?
                ''', (user_id, user_id, user_id, user_id, limit))
                
                return [dict(row) for row in cursor.fetchall()]
        except Exception:
            return []
    
    # Admin Methods
    
    def get_all_users(self) -> List[Dict[str, Any]]:
        """Get all users (admin function)"""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT id, username, mmr, user_class, wins, losses, debates_count, created_at
                    FROM users 
                    ORDER BY created_at DESC
                ''')
                return [dict(row) for row in cursor.fetchall()]
        except Exception:
            return []
    
    def get_all_debates(self) -> List[Dict[str, Any]]:
        """Get all debates (admin function)"""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT d.id, d.topic, d.created_at, d.duration_minutes,
                           u1.username as user1_name, u2.username as user2_name,
                           w.username as winner_name
                    FROM debates d
                    LEFT JOIN users u1 ON d.user1_id = u1.id
                    LEFT JOIN users u2 ON d.user2_id = u2.id  
                    LEFT JOIN users w ON d.winner_id = w.id
                    ORDER BY d.created_at DESC
                ''')
                return [dict(row) for row in cursor.fetchall()]
        except Exception:
            return []
    
    def delete_user(self, user_id: int) -> bool:
        """Delete a user (admin function)"""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                # Delete user's debates first (foreign key constraint)
                cursor.execute('DELETE FROM debates WHERE user1_id = ? OR user2_id = ?', (user_id, user_id))
                # Delete user
                cursor.execute('DELETE FROM users WHERE id = ?', (user_id,))
                conn.commit()
                return cursor.rowcount > 0
        except Exception:
            return False
    
    def delete_debate(self, debate_id: int) -> bool:
        """Delete a debate (admin function)"""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('DELETE FROM debates WHERE id = ?', (debate_id,))
                conn.commit()
                return cursor.rowcount > 0
        except Exception:
            return False


# Test function to verify database functionality
def test_database():
    """Test database functionality"""
    print("🧪 Testing database functionality...")
    
    # Create test database in memory
    db = Database(':memory:')
    
    # Test user creation
    result = db.create_user("alice", "password123")
    assert result['success'], f"User creation failed: {result}"
    print("✅ User creation works")
    
    # Test authentication
    auth = db.authenticate_user("alice", "password123")
    assert auth['success'], f"Authentication failed: {auth}"
    print("✅ Authentication works")
    
    # Test topic retrieval
    topic = db.get_random_topic()
    assert topic, "No topic retrieved"
    print(f"✅ Topic retrieval works: {topic[:50]}...")
    
    # Test debate saving
    messages = [
        {'sender': 'alice', 'content': 'My argument is...', 'timestamp': datetime.now().isoformat()}
    ]
    debate_id = db.save_debate(auth['user_id'], auth['user_id'], topic, messages)
    assert debate_id, "Debate saving failed"
    print("✅ Debate saving works")
    
    print("🎉 All database tests passed!")


if __name__ == "__main__":
    test_database()
