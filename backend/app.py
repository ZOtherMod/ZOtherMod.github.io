#!/usr/bin/env python3
import asyncio
import json
import os
from datetime import datetime
from pathlib import Path

from database import Database
from websocket_manager import WebSocketManager, WebSocketHandler
from matchmaking import Matchmaker
from debate_logic import DebateManager

try:
    import websockets
    from websockets.exceptions import ConnectionClosed
except ImportError as e:
    print(f"Error: websockets library not properly installed: {e}")
    print("Please install it with: pip install websockets")
    exit(1)

class DebatePlatformServer:
    def __init__(self, host=None, port=None, debug=False):
        self.host = host if host is not None else os.getenv('HOST', 'localhost')
        
        if port is not None:
            self.port = int(port)
        elif os.getenv('PORT'):
            self.port = int(os.getenv('PORT'))
        else:
            self.port = 8765
            
        if os.getenv('PORT') and self.host == 'localhost':
            self.host = '0.0.0.0'
            
        self.debug = debug if debug is not None else os.getenv('DEBUG', 'False').lower() == 'true'
        
        self.database = Database()
        self.websocket_manager = WebSocketManager()
        self.debate_manager = DebateManager(self.websocket_manager, self.database)
        self.matchmaker = Matchmaker(self.websocket_manager, self.database)
        self.websocket_handler = WebSocketHandler(
            self.websocket_manager, self.matchmaker, self.debate_manager, self.database
        )
        
        self.running = False
        self.server = None
        
        print(f"Debate Platform Server initialized on {self.host}:{self.port}")

    async def start_server(self):
        try:
            print("Starting Debate Platform Server...")
            
            matchmaking_task = asyncio.create_task(
                self.matchmaker.start_matchmaking_service()
            )
            
            print(f"Starting WebSocket server on {self.host}:{self.port}")
            self.server = await websockets.serve(
                self.websocket_handler.handle_connection,
                self.host,
                self.port
            )
            
            self.running = True
            print(f"✓ WebSocket server running on ws://{self.host}:{self.port}")
            print("✓ Matchmaking service running")
            print("✓ Database initialized")
            
            await self.server.wait_closed()
                
        except Exception as e:
            print(f"Error starting server: {e}")
            raise
    
    async def stop_server(self):
        print("Stopping server...")
        
        self.running = False
        
        self.matchmaker.stop_matchmaking_service()
        
        if self.server:
            self.server.close()
            await self.server.wait_closed()
        
        print("Server stopped")
    
    def get_status(self):
        return {
            'running': self.running,
            'host': self.host,
            'port': self.port,
            'connected_users': self.websocket_manager.get_connection_count(),
            'active_debates': self.debate_manager.get_active_debates_count(),
            'queue_status': self.matchmaker.queue.get_queue_status()
        }

async def main():
    try:
        server = DebatePlatformServer()
        await server.start_server()
    except KeyboardInterrupt:
        print("\nShutdown complete")
        await server.stop_server()
    except Exception as e:
        print(f"Server error: {e}")
        try:
            await server.stop_server()
        except:
            pass

if __name__ == "__main__":
    print("Online Debate Platform Server")
    print("=" * 40)
    
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nShutdown complete")
    except Exception as e:
        print(f"Fatal error: {e}")
        exit(1)
