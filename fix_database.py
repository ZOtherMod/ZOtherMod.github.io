#!/usr/bin/env python3
import sqlite3
import hashlib

def setup_debate_database():
    conn = sqlite3.connect('database/app.db')
    cursor = conn.cursor()
    
    print("Setting up proper two-user debate...")
    
    # Check current state
    cursor.execute("SELECT id, user1_id, user2_id, topic FROM debates WHERE id = 1")
    current_debate = cursor.fetchone()
    print(f"Current debate: {current_debate}")
    
    # Fix the debate to have two different users
    cursor.execute("UPDATE debates SET user2_id = 2 WHERE id = 1")
    
    # Verify the fix
    cursor.execute("SELECT id, user1_id, user2_id, topic FROM debates WHERE id = 1")
    fixed_debate = cursor.fetchone()
    print(f"Fixed debate: {fixed_debate}")
    
    # Check users
    cursor.execute("SELECT id, username FROM users")
    users = cursor.fetchall()
    print(f"Available users: {users}")
    
    conn.commit()
    conn.close()
    print("Database setup complete!")

if __name__ == "__main__":
    setup_debate_database()
