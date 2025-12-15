import sqlite3
import hashlib
from datetime import datetime
import os

try:
    import psycopg2
    from psycopg2.extras import RealDictCursor
    HAS_PSYCOPG2 = True
except ImportError:
    HAS_PSYCOPG2 = False

class Database:
    def __init__(self, db_path='database/app.db'):
        self.database_url = os.getenv('DATABASE_URL')
        
        if self.database_url and self.database_url.startswith('postgres') and HAS_PSYCOPG2:
            self.use_postgres = True
            print("Using PostgreSQL database")
        else:
            self.use_postgres = False
            self.db_path = db_path
            print("Using SQLite database")
            
        self.init_database()
    
    def get_connection(self):
        if self.use_postgres:
            return psycopg2.connect(self.database_url, cursor_factory=RealDictCursor)
        else:
            if self.db_path != ':memory:':
                db_dir = os.path.dirname(self.db_path)
                if db_dir:  # Only create directory if dirname is not empty
                    os.makedirs(db_dir, exist_ok=True)
            return sqlite3.connect(self.db_path)
    
    def init_database(self):
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
        except Exception as e:
            print(f"Database connection failed: {e}")
            self.use_postgres = False
            self.db_path = ':memory:'
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
        
        if self.use_postgres:
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    id SERIAL PRIMARY KEY,
                    username VARCHAR(255) UNIQUE NOT NULL,
                    password_hash VARCHAR(255) NOT NULL,
                    mmr INTEGER DEFAULT 1000,
                    user_class INTEGER DEFAULT 0
                )
            ''')
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS debates (
                    id SERIAL PRIMARY KEY,
                    user1_id INTEGER NOT NULL,
                    user2_id INTEGER NOT NULL,
                    topic TEXT NOT NULL,
                    log TEXT NOT NULL,
                    winner INTEGER,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user1_id) REFERENCES users (id),
                    FOREIGN KEY (user2_id) REFERENCES users (id),
                    FOREIGN KEY (winner) REFERENCES users (id)
                )
            ''')
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS topics (
                    id SERIAL PRIMARY KEY,
                    topic_text TEXT NOT NULL
                )
            ''')
        else:
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE NOT NULL,
                    password_hash TEXT NOT NULL,
                    mmr INTEGER DEFAULT 1000,
                    user_class INTEGER DEFAULT 0
                )
            ''')
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS debates (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user1_id INTEGER NOT NULL,
                    user2_id INTEGER NOT NULL,
                    topic TEXT NOT NULL,
                    log TEXT NOT NULL,
                    winner INTEGER,
                    timestamp DATETIME NOT NULL,
                    FOREIGN KEY (user1_id) REFERENCES users (id),
                    FOREIGN KEY (user2_id) REFERENCES users (id),
                    FOREIGN KEY (winner) REFERENCES users (id)
                )
            ''')
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS topics (
                    id INTEGER PRIMARY KEY,
                    topic_text TEXT NOT NULL
                )
            ''')
        
        conn.commit()
        
        if self.use_postgres:
            cursor.execute('SELECT COUNT(*) FROM topics')
            count = cursor.fetchone()[0]
        else:
            cursor.execute('SELECT COUNT(*) FROM topics')
            count = cursor.fetchone()[0]
            
        if count == 0:
            self.insert_default_topics(cursor)
            conn.commit()
        
        # Check if test account exists, create if it doesn't
        self.create_test_account_if_not_exists(cursor)
        conn.commit()
        
        conn.close()
    
    def insert_default_topics(self, cursor):
        default_topics = [
            "Social media has a positive impact on society",
            "Remote work is better than office work", 
            "Artificial intelligence will benefit humanity more than it will harm it",
            "Video games have a positive impact on children",
            "Climate change is the most pressing issue of our time",
            "Free speech should have no limitations",
            "Technology makes us more isolated",
            "Education should be free for everyone",
            "Space exploration is worth the investment",
            "Universal Basic Income should be implemented globally"
        ]
        
        for topic in default_topics:
            if self.use_postgres:
                cursor.execute("INSERT INTO topics (topic_text) VALUES (%s)", (topic,))
            else:
                cursor.execute("INSERT INTO topics (topic_text) VALUES (?)", (topic,))
    
    def create_test_account_if_not_exists(self, cursor):
        """Create the test account with UserClass 2 if it doesn't exist"""
        # Check if test account already exists
        if self.use_postgres:
            cursor.execute("SELECT COUNT(*) FROM users WHERE username = %s", ('test',))
        else:
            cursor.execute("SELECT COUNT(*) FROM users WHERE username = ?", ('test',))
        
        count = cursor.fetchone()[0]
        
        if count == 0:
            # Create test account with password "passpass" and UserClass 2
            password_hash = hashlib.sha256('passpass'.encode()).hexdigest()
            if self.use_postgres:
                cursor.execute("INSERT INTO users (username, password_hash, user_class, mmr) VALUES (%s, %s, %s, %s)", 
                             ('test', password_hash, 2, 1500))
            else:
                cursor.execute("INSERT INTO users (username, password_hash, user_class, mmr) VALUES (?, ?, ?, ?)", 
                             ('test', password_hash, 2, 1500))
        
        # Create a second test account for testing matchmaking
        if self.use_postgres:
            cursor.execute("SELECT COUNT(*) FROM users WHERE username = %s", ('test2',))
        else:
            cursor.execute("SELECT COUNT(*) FROM users WHERE username = ?", ('test2',))
        
        count2 = cursor.fetchone()[0]
        
        if count2 == 0:
            # Create test2 account with password "passpass" and UserClass 0
            password_hash = hashlib.sha256('passpass'.encode()).hexdigest()
            if self.use_postgres:
                cursor.execute("INSERT INTO users (username, password_hash, user_class, mmr) VALUES (%s, %s, %s, %s)", 
                             ('test2', password_hash, 0, 1000))
            else:
                cursor.execute("INSERT INTO users (username, password_hash, user_class, mmr) VALUES (?, ?, ?, ?)", 
                             ('test2', password_hash, 0, 1000))
    
    def create_user(self, username, password, user_class=0):
        try:
            password_hash = hashlib.sha256(password.encode()).hexdigest()
            conn = self.get_connection()
            cursor = conn.cursor()
            
            if self.use_postgres:
                cursor.execute("INSERT INTO users (username, password_hash, user_class) VALUES (%s, %s, %s) RETURNING id", 
                             (username, password_hash, user_class))
                user_id = cursor.fetchone()[0]
            else:
                cursor.execute("INSERT INTO users (username, password_hash, user_class) VALUES (?, ?, ?)", 
                             (username, password_hash, user_class))
                user_id = cursor.lastrowid
                
            conn.commit()
            conn.close()
            return user_id
        except Exception as e:
            try:
                conn.close()
            except:
                pass
            if "unique" in str(e).lower() or "duplicate" in str(e).lower():
                return None
            return None
    
    def authenticate_user(self, username, password):
        try:
            password_hash = hashlib.sha256(password.encode()).hexdigest()
            conn = self.get_connection()
            cursor = conn.cursor()
            
            if self.use_postgres:
                cursor.execute("SELECT id, mmr, user_class FROM users WHERE username = %s AND password_hash = %s", 
                             (username, password_hash))
            else:
                cursor.execute("SELECT id, mmr, user_class FROM users WHERE username = ? AND password_hash = ?", 
                             (username, password_hash))
            
            result = cursor.fetchone()
            conn.close()
            
            if result:
                return {'id': result[0], 'username': username, 'mmr': result[1], 'user_class': result[2]}
            return None
        except Exception as e:
            try:
                conn.close()
            except:
                pass
            return None
    
    def get_user_by_id(self, user_id):
        conn = self.get_connection()
        cursor = conn.cursor()
        
        if self.use_postgres:
            cursor.execute("SELECT id, username, mmr, user_class FROM users WHERE id = %s", (user_id,))
        else:
            cursor.execute("SELECT id, username, mmr, user_class FROM users WHERE id = ?", (user_id,))
        
        result = cursor.fetchone()
        conn.close()
        
        if result:
            return {'id': result[0], 'username': result[1], 'mmr': result[2], 'user_class': result[3]}
        return None
    
    def update_user_mmr(self, user_id, new_mmr):
        conn = self.get_connection()
        cursor = conn.cursor()
        
        if self.use_postgres:
            cursor.execute("UPDATE users SET mmr = %s WHERE id = %s", (new_mmr, user_id))
        else:
            cursor.execute("UPDATE users SET mmr = ? WHERE id = ?", (new_mmr, user_id))
        
        conn.commit()
        conn.close()
    
    def get_random_topic(self):
        conn = self.get_connection()
        cursor = conn.cursor()
        
        if self.use_postgres:
            cursor.execute("SELECT topic_text FROM topics ORDER BY RANDOM() LIMIT 1")
        else:
            cursor.execute("SELECT topic_text FROM topics ORDER BY RANDOM() LIMIT 1")
        
        result = cursor.fetchone()
        conn.close()
        
        return result[0] if result else "The importance of education in society"
    
    def create_debate(self, user1_id, user2_id, topic):
        """Create a new debate and return the debate ID"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            if self.use_postgres:
                cursor.execute('''
                    INSERT INTO debates (user1_id, user2_id, topic, log, timestamp)
                    VALUES (%s, %s, %s, %s, %s) RETURNING id
                ''', (user1_id, user2_id, topic, '', datetime.now()))
                debate_id = cursor.fetchone()[0]
            else:
                cursor.execute('''
                    INSERT INTO debates (user1_id, user2_id, topic, log, timestamp)
                    VALUES (?, ?, ?, ?, ?)
                ''', (user1_id, user2_id, topic, '', datetime.now().isoformat()))
                debate_id = cursor.lastrowid
            
            conn.commit()
            conn.close()
            return debate_id
        except Exception as e:
            try:
                conn.close()
            except:
                pass
            print(f"Error creating debate: {e}")
            return None
    
    def save_debate(self, user1_id, user2_id, topic, log, winner=None):
        conn = self.get_connection()
        cursor = conn.cursor()
        
        if self.use_postgres:
            cursor.execute('''
                INSERT INTO debates (user1_id, user2_id, topic, log, winner, timestamp)
                VALUES (%s, %s, %s, %s, %s, %s)
            ''', (user1_id, user2_id, topic, log, winner, datetime.now()))
        else:
            cursor.execute('''
                INSERT INTO debates (user1_id, user2_id, topic, log, winner, timestamp)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (user1_id, user2_id, topic, log, winner, datetime.now().isoformat()))
        
        conn.commit()
        conn.close()
    
    def get_user_debates(self, user_id, limit=10):
        conn = self.get_connection()
        cursor = conn.cursor()
        
        if self.use_postgres:
            cursor.execute('''
                SELECT d.topic, d.winner, d.timestamp, u1.username as user1, u2.username as user2
                FROM debates d
                JOIN users u1 ON d.user1_id = u1.id
                JOIN users u2 ON d.user2_id = u2.id
                WHERE d.user1_id = %s OR d.user2_id = %s
                ORDER BY d.timestamp DESC
                LIMIT %s
            ''', (user_id, user_id, limit))
        else:
            cursor.execute('''
                SELECT d.topic, d.winner, d.timestamp, u1.username as user1, u2.username as user2
                FROM debates d
                JOIN users u1 ON d.user1_id = u1.id
                JOIN users u2 ON d.user2_id = u2.id
                WHERE d.user1_id = ? OR d.user2_id = ?
                ORDER BY d.timestamp DESC
                LIMIT ?
            ''', (user_id, user_id, limit))
        
        results = cursor.fetchall()
        conn.close()
        
        debates = []
        for row in results:
            debates.append({
                'topic': row[0],
                'winner': row[1],
                'timestamp': row[2],
                'user1': row[3],
                'user2': row[4]
            })
        
        return debates
    
    def get_debate_by_id(self, debate_id):
        """Get debate information by ID"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            if self.use_postgres:
                cursor.execute("SELECT id, user1_id, user2_id, topic, winner, timestamp FROM debates WHERE id = %s", (debate_id,))
            else:
                cursor.execute("SELECT id, user1_id, user2_id, topic, winner, timestamp FROM debates WHERE id = ?", (debate_id,))
            
            result = cursor.fetchone()
            conn.close()
            
            if result:
                return {
                    'id': result[0],
                    'user1_id': result[1],
                    'user2_id': result[2],
                    'topic': result[3],
                    'winner': result[4],
                    'timestamp': result[5]
                }
            return None
        except Exception as e:
            try:
                conn.close()
            except:
                pass
            print(f"Error getting debate by ID: {e}")
            return None
    
    # Admin methods
    def get_all_users(self):
        """Get all users for admin panel"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            cursor.execute('SELECT id, username, mmr, user_class FROM users ORDER BY id')
            
            if self.use_postgres:
                results = cursor.fetchall()
                users = []
                for result in results:
                    users.append({
                        'id': result['id'],
                        'username': result['username'],
                        'mmr': result['mmr'],
                        'user_class': result['user_class']
                    })
                return users
            else:
                results = cursor.fetchall()
                users = []
                for result in results:
                    users.append({
                        'id': result[0],
                        'username': result[1],
                        'mmr': result[2],
                        'user_class': result[3]
                    })
                return users
        except Exception as e:
            try:
                conn.close()
            except:
                pass
            print(f"Error getting all users: {e}")
            return []
        finally:
            try:
                conn.close()
            except:
                pass
    
    def get_all_debates(self):
        """Get all debates with user names for admin panel"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            if self.use_postgres:
                cursor.execute('''
                    SELECT d.id, d.user1_id, d.user2_id, d.topic, d.log, d.winner, d.timestamp,
                           u1.username as user1_name, u2.username as user2_name, uw.username as winner_name
                    FROM debates d
                    LEFT JOIN users u1 ON d.user1_id = u1.id
                    LEFT JOIN users u2 ON d.user2_id = u2.id
                    LEFT JOIN users uw ON d.winner = uw.id
                    ORDER BY d.timestamp DESC
                ''')
                
                results = cursor.fetchall()
                debates = []
                for result in results:
                    debates.append({
                        'id': result['id'],
                        'user1_id': result['user1_id'],
                        'user2_id': result['user2_id'],
                        'user1_name': result['user1_name'],
                        'user2_name': result['user2_name'],
                        'topic': result['topic'],
                        'log': result['log'],
                        'winner': result['winner'],
                        'winner_name': result['winner_name'],
                        'timestamp': result['timestamp']
                    })
                return debates
            else:
                cursor.execute('''
                    SELECT d.id, d.user1_id, d.user2_id, d.topic, d.log, d.winner, d.timestamp,
                           u1.username as user1_name, u2.username as user2_name, uw.username as winner_name
                    FROM debates d
                    LEFT JOIN users u1 ON d.user1_id = u1.id
                    LEFT JOIN users u2 ON d.user2_id = u2.id
                    LEFT JOIN users uw ON d.winner = uw.id
                    ORDER BY d.timestamp DESC
                ''')
                
                results = cursor.fetchall()
                debates = []
                for result in results:
                    debates.append({
                        'id': result[0],
                        'user1_id': result[1],
                        'user2_id': result[2],
                        'user1_name': result[7],
                        'user2_name': result[8],
                        'topic': result[3],
                        'log': result[4],
                        'winner': result[5],
                        'winner_name': result[9],
                        'timestamp': result[6]
                    })
                return debates
        except Exception as e:
            try:
                conn.close()
            except:
                pass
            print(f"Error getting all debates: {e}")
            return []
        finally:
            try:
                conn.close()
            except:
                pass
    
    def get_all_topics(self):
        """Get all topics for admin panel"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            cursor.execute('SELECT id, topic_text FROM topics ORDER BY id')
            
            if self.use_postgres:
                results = cursor.fetchall()
                topics = []
                for result in results:
                    topics.append({
                        'id': result['id'],
                        'topic_text': result['topic_text']
                    })
                return topics
            else:
                results = cursor.fetchall()
                topics = []
                for result in results:
                    topics.append({
                        'id': result[0],
                        'topic_text': result[1]
                    })
                return topics
        except Exception as e:
            try:
                conn.close()
            except:
                pass
            print(f"Error getting all topics: {e}")
            return []
        finally:
            try:
                conn.close()
            except:
                pass
    
    def get_topic_by_id(self, topic_id):
        """Get topic by ID for admin panel"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            if self.use_postgres:
                cursor.execute('SELECT id, topic_text FROM topics WHERE id = %s', (topic_id,))
                result = cursor.fetchone()
                if result:
                    return {
                        'id': result['id'],
                        'topic_text': result['topic_text']
                    }
            else:
                cursor.execute('SELECT id, topic_text FROM topics WHERE id = ?', (topic_id,))
                result = cursor.fetchone()
                if result:
                    return {
                        'id': result[0],
                        'topic_text': result[1]
                    }
            return None
        except Exception as e:
            try:
                conn.close()
            except:
                pass
            print(f"Error getting topic by ID: {e}")
            return None
        finally:
            try:
                conn.close()
            except:
                pass
    
    def update_user_admin(self, user_id, username=None, mmr=None, user_class=None):
        """Update user for admin panel"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            updates = []
            params = []
            
            if username is not None:
                updates.append('username = %s' if self.use_postgres else 'username = ?')
                params.append(username)
            if mmr is not None:
                updates.append('mmr = %s' if self.use_postgres else 'mmr = ?')
                params.append(mmr)
            if user_class is not None:
                updates.append('user_class = %s' if self.use_postgres else 'user_class = ?')
                params.append(user_class)
            
            if not updates:
                return False
            
            params.append(user_id)
            query = f"UPDATE users SET {', '.join(updates)} WHERE id = %s" if self.use_postgres else f"UPDATE users SET {', '.join(updates)} WHERE id = ?"
            
            cursor.execute(query, params)
            conn.commit()
            return cursor.rowcount > 0
        except Exception as e:
            try:
                conn.close()
            except:
                pass
            print(f"Error updating user: {e}")
            return False
        finally:
            try:
                conn.close()
            except:
                pass
    
    def update_topic(self, topic_id, topic_text):
        """Update topic for admin panel"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            if self.use_postgres:
                cursor.execute('UPDATE topics SET topic_text = %s WHERE id = %s', (topic_text, topic_id))
            else:
                cursor.execute('UPDATE topics SET topic_text = ? WHERE id = ?', (topic_text, topic_id))
            
            conn.commit()
            return cursor.rowcount > 0
        except Exception as e:
            try:
                conn.close()
            except:
                pass
            print(f"Error updating topic: {e}")
            return False
        finally:
            try:
                conn.close()
            except:
                pass
    
    def delete_user(self, user_id):
        """Delete user for admin panel"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            if self.use_postgres:
                cursor.execute('DELETE FROM users WHERE id = %s', (user_id,))
            else:
                cursor.execute('DELETE FROM users WHERE id = ?', (user_id,))
            
            conn.commit()
            return cursor.rowcount > 0
        except Exception as e:
            try:
                conn.close()
            except:
                pass
            print(f"Error deleting user: {e}")
            return False
        finally:
            try:
                conn.close()
            except:
                pass
    
    def delete_debate(self, debate_id):
        """Delete debate for admin panel"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            if self.use_postgres:
                cursor.execute('DELETE FROM debates WHERE id = %s', (debate_id,))
            else:
                cursor.execute('DELETE FROM debates WHERE id = ?', (debate_id,))
            
            conn.commit()
            return cursor.rowcount > 0
        except Exception as e:
            try:
                conn.close()
            except:
                pass
            print(f"Error deleting debate: {e}")
            return False
        finally:
            try:
                conn.close()
            except:
                pass
    
    def delete_topic(self, topic_id):
        """Delete topic for admin panel"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            if self.use_postgres:
                cursor.execute('DELETE FROM topics WHERE id = %s', (topic_id,))
            else:
                cursor.execute('DELETE FROM topics WHERE id = ?', (topic_id,))
            
            conn.commit()
            return cursor.rowcount > 0
        except Exception as e:
            try:
                conn.close()
            except:
                pass
            print(f"Error deleting topic: {e}")
            return False
        finally:
            try:
                conn.close()
            except:
                pass
