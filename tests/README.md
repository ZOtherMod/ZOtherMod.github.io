# Test Suite for DebatePlatform

This directory contains comprehensive tests for the debate platform functionality.

**Final Test Suite v1** - Created December 15, 2025

## Test Files

### Core Functionality Tests
- **`test_debate_session.py`** - Tests the DebateSession class and debate flow
- **`test_timer.py`** - Tests timer functionality for preparation and turn phases
- **`test_turn_timers.py`** - Comprehensive testing of turn-based timer mechanisms
- **`test_full_flow.py`** - End-to-end testing of complete debate workflow
- **`test_complete_flow.py`** - Another comprehensive flow test with detailed logging

### Database and User Tests
- **`test_user_class.py`** - Tests the new UserClass functionality and test account creation
- **`test_sql_direct.py`** - Direct SQL testing to isolate database functionality
- **`test_persistent.py`** - Tests persistent data storage and retrieval

### WebSocket and Integration Tests
- **`test_websocket_userclass.py`** - Tests UserClass functionality via WebSocket connections
- **`simple_test.py`** - Simple debugging test for basic functionality

### Frontend Tests
- **`test_userclass.html`** - HTML test page for testing UserClass functionality in browser

## Running Tests

### Python Backend Tests
```bash
# Run individual tests
python3 tests/test_user_class.py
python3 tests/test_timer.py
python3 tests/test_full_flow.py

# Or run from the backend directory
cd backend && python3 ../tests/test_debate_session.py
```

### WebSocket Tests
Make sure the backend server is running first:
```bash
cd backend && python3 app.py
```

Then in another terminal:
```bash
python3 tests/test_websocket_userclass.py
```

### Frontend Tests
Start both frontend and backend servers:
```bash
# Terminal 1: Backend
cd backend && python3 app.py

# Terminal 2: Frontend
cd frontend && python3 -m http.server 3000
```

Then open `http://localhost:3000/tests/test_userclass.html` in your browser.

## Test Coverage

These tests cover:
- ✅ Timer functionality (preparation and turn phases)
- ✅ Debate session management
- ✅ UserClass system with different access levels
- ✅ WebSocket communication
- ✅ Database operations (SQLite and PostgreSQL)
- ✅ Complete debate workflow from start to finish
- ✅ User authentication and account creation
- ✅ Matchmaking system
- ✅ Real-time messaging during debates

## Test Account

The system includes a preset test account:
- **Username**: `test`
- **Password**: `passpass`
- **UserClass**: `2` (elevated permissions)
- **MMR**: `1500`

Regular accounts created through the interface have UserClass `0`.
