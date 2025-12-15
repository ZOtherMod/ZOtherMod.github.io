let appState = {
    websocket: null,
    currentUser: null,
    currentDebate: null,
    reconnectAttempts: 0,
    maxReconnectAttempts: 5,
    reconnectDelay: 2000,
    isConnected: false,
    isAuthenticated: false,
    currentUserId: null,
    connectionState: 'disconnected' // disconnected, connecting, connected, authenticating, authenticated, waiting_opponent, ready
};

// Connection Overlay Management
function showConnectionOverlay() {
    const overlay = document.getElementById('connectionOverlay');
    if (overlay) {
        overlay.classList.remove('hidden');
    }
}

function hideConnectionOverlay() {
    const overlay = document.getElementById('connectionOverlay');
    if (overlay) {
        overlay.classList.add('hidden');
    }
}

function updateConnectionStep(step, state, text = null) {
    const stepElement = document.getElementById(step);
    if (stepElement) {
        // Remove all state classes
        stepElement.classList.remove('pending', 'active', 'completed', 'error');
        // Add new state
        stepElement.classList.add(state);
        
        // Update text if provided
        if (text) {
            const stepText = stepElement.querySelector('.step-text');
            if (stepText) stepText.textContent = text;
        }
    }
}

function updateConnectionTitle(title) {
    const titleElement = document.getElementById('connectionTitle');
    if (titleElement) titleElement.textContent = title;
}

function updateConnectionStatus(status) {
    const statusElement = document.getElementById('connectionStatus');
    if (statusElement) statusElement.textContent = status;
}

function setConnectionState(newState) {
    appState.connectionState = newState;
    console.log('Connection state changed to:', newState);
    
    // Reset all steps to pending
    updateConnectionStep('step1', 'pending');
    updateConnectionStep('step2', 'pending');
    updateConnectionStep('step3', 'pending');
    
    switch (newState) {
        case 'disconnected':
            showConnectionOverlay();
            updateConnectionTitle('Connection Lost');
            updateConnectionStatus('Attempting to reconnect...');
            updateConnectionStep('step1', 'error');
            break;
            
        case 'connecting':
            showConnectionOverlay();
            updateConnectionTitle('Connecting to Server...');
            updateConnectionStatus('Establishing WebSocket connection');
            updateConnectionStep('step1', 'active');
            break;
            
        case 'connected':
            updateConnectionStep('step1', 'completed');
            updateConnectionStep('step2', 'active');
            updateConnectionTitle('Authenticating...');
            updateConnectionStatus('Verifying user credentials');
            break;
            
        case 'authenticated':
            updateConnectionStep('step1', 'completed');
            updateConnectionStep('step2', 'completed');
            updateConnectionStep('step3', 'active');
            updateConnectionTitle('Waiting for Opponent...');
            updateConnectionStatus('Looking for another player to start the debate');
            break;
            
        case 'ready':
            updateConnectionStep('step1', 'completed');
            updateConnectionStep('step2', 'completed');
            updateConnectionStep('step3', 'completed');
            updateConnectionTitle('Ready to Begin!');
            updateConnectionStatus('Both players connected. Starting debate...');
            
            // Hide overlay after a brief moment
            setTimeout(() => {
                hideConnectionOverlay();
            }, 1500);
            break;
    }
}

function connectWebSocket() {
    console.log('connectWebSocket called');
    setConnectionState('connecting');
    
    const isLocalhost = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1';
    
    let wsUrl;
    if (isLocalhost) {
        wsUrl = window.CONFIG?.LOCAL_WEBSOCKET_URL || 'ws://localhost:8765';
    } else {
        wsUrl = window.CONFIG?.WEBSOCKET_URL || 'wss://debatesite.onrender.com';
    }
    
    try {
        console.log('Creating WebSocket connection to:', wsUrl);
        appState.websocket = new WebSocket(wsUrl);
        
        appState.websocket.onopen = handleWebSocketOpen;
        appState.websocket.onmessage = handleWebSocketMessage;
        appState.websocket.onclose = handleWebSocketClose;
        appState.websocket.onerror = handleWebSocketError;
        
    } catch (error) {
        console.error('WebSocket connection failed:', error);
        setConnectionState('disconnected');
    }
}

function handleWebSocketOpen() {
    console.log('WebSocket connected successfully');
    appState.isConnected = true;
    appState.reconnectAttempts = 0;
    setConnectionState('connected');
    
    // Auto-authenticate with test user for debugging
    setTimeout(() => {
        authenticateTestUser();
    }, 500);
}

function handleWebSocketMessage(event) {
    try {
        const data = JSON.parse(event.data);
        console.log('Received WebSocket message:', data);
        
        switch (data.type) {
            case 'auth_response':
                handleAuthResponse(data);
                break;
            case 'account_creation_response':
                handleAccountCreationResponse(data);
                break;
            case 'queue_joined':
                handleQueueJoined(data);
                break;
            case 'match_found':
                handleMatchFound(data);
                break;
            case 'start_debate_response':
                handleStartDebateResponse(data);
                break;
            case 'debate_initialized':
                handleDebateInitialized(data);
                break;
            case 'debate_started':
                handleDebateStarted(data);
                break;
            case 'connection_status':
                handleConnectionStatus(data);
                break;
            case 'prep_timer_start':
            case 'prep_timer':
                handlePrepTimer(data);
                break;
            case 'debate_phase_start':
                handleDebatePhaseStart(data);
                break;
            case 'your_turn':
                handleYourTurn(data);
                break;
            case 'opponent_turn':
                handleOpponentTurn(data);
                break;
            case 'turn_timer':
                handleTurnTimer(data);
                break;
            case 'message':
                handleDebateMessage(data);
                break;
            case 'debate_ended':
                handleDebateEnded(data);
                break;
            case 'error':
                showMessage(data.message, 'error');
                break;
            case 'admin_data_response':
                handleAdminDataResponse(data);
                break;
            case 'admin_item_response':
                handleAdminItemResponse(data);
                break;
            case 'admin_update_response':
                handleAdminUpdateResponse(data);
                break;
            case 'admin_delete_response':
                handleAdminDeleteResponse(data);
                break;
            case 'pong':

                break;
            default:
                console.log('Unknown message type:', data.type);
        }
    } catch (error) {
        console.error('Error parsing WebSocket message:', error);
    }
}

function handleWebSocketClose() {
    console.log('WebSocket connection closed');
    appState.isConnected = false;
    updateConnectionStatus('Disconnected');
    

    if (appState.reconnectAttempts < appState.maxReconnectAttempts) {
        appState.reconnectAttempts++;
        console.log(`Reconnect attempt ${appState.reconnectAttempts}/${appState.maxReconnectAttempts}`);
        updateConnectionStatus(`Reconnecting (${appState.reconnectAttempts})...`);
        
        setTimeout(() => {
            connectWebSocket();
        }, appState.reconnectDelay);
    } else {
        updateConnectionStatus('Connection lost');
        showMessage('Connection lost. Please refresh the page.', 'error');
    }
}

function handleWebSocketError(error) {
    console.error('WebSocket error:', error);
    updateConnectionStatus('Connection error');
    
    // Show error in debug status if available
    const debugStatus = document.getElementById('debugStatus');
    if (debugStatus) {
        debugStatus.textContent = 'WebSocket connection error';
        debugStatus.style.color = 'red';
    }
}

function sendWebSocketMessage(message) {
    if (appState.websocket && appState.websocket.readyState === WebSocket.OPEN) {
        appState.websocket.send(JSON.stringify(message));
        return true;
    } else {
        console.error('WebSocket not connected');
        showMessage('Not connected to server', 'error');
        return false;
    }
}


function updateConnectionStatus(text, isOnline = false) {
    const indicator = document.getElementById('connectionIndicator');
    const statusText = document.getElementById('connectionText');
    
    if (indicator && statusText) {
        indicator.className = `status-indicator ${isOnline ? 'online' : 'offline'}`;
        statusText.textContent = text;
    }
}

function showMessage(message, type = 'info') {
    const container = document.getElementById('messageContainer');
    const messageText = document.getElementById('messageText');
    
    if (container && messageText) {
        messageText.textContent = message;
        messageText.className = `message ${type}`;
        container.classList.remove('hidden');
        
        setTimeout(() => {
            container.classList.add('hidden');
        }, 5000);
    }
}

function hideMessage() {
    const container = document.getElementById('messageContainer');
    if (container) {
        container.classList.add('hidden');
    }
}

function showElement(elementId) {
    const element = document.getElementById(elementId);
    if (element) {
        element.classList.remove('hidden');
    }
}

function hideElement(elementId) {
    const element = document.getElementById(elementId);
    if (element) {
        element.classList.add('hidden');
    }
}

function setElementText(elementId, text) {
    const element = document.getElementById(elementId);
    if (element) {
        element.textContent = text;
    }
}


function handleAuthResponse(data) {
    if (data.success) {
        appState.currentUser = {
            id: data.user_id,
            username: data.username,
            mmr: data.mmr,
            user_class: data.user_class || 0
        };
        appState.isAuthenticated = true;
        appState.currentUserId = data.user_id;

        localStorage.setItem('debateUser', JSON.stringify(appState.currentUser));
        
        console.log('Authentication successful, user ID:', data.user_id);
        setConnectionState('authenticated');
        
        // If we're on the debate page, start debate process
        if (window.location.pathname.includes('debate.html')) {
            // Start the debate (this will trigger the ping system)
            setTimeout(() => {
                startDebateProcess();
            }, 1000);
        } else {
            showMessage('Login successful!', 'success');
            setTimeout(() => {
                window.location.href = 'matchmaking.html';
            }, 1000);
        }
    } else {
        console.error('Authentication failed:', data.error);
        setConnectionState('disconnected');
        showMessage(data.error, 'error');
    }
}

function authenticateTestUser() {
    console.log('Auto-authenticating test user...');
    
    sendWebSocketMessage({
        type: 'authenticate',
        username: 'test',
        password: 'testpass'
    });
}

function startDebateProcess() {
    console.log('Starting debate process for authenticated user...');
    
    if (!appState.currentUserId) {
        console.error('No current user ID available');
        return;
    }
    
    sendWebSocketMessage({
        type: 'start_debate',
        user_id: appState.currentUserId,
        debate_id: 1
    });
}

function handleAccountCreationResponse(data) {
    if (data.success) {
        showMessage('Account created successfully! You can now login.', 'success');
        

        setTimeout(() => {
            showLoginForm();
        }, 1500);
    } else {
        showMessage(data.error, 'error');
    }
}


function initializeLoginPage() {
    connectWebSocket();
    

    const showCreateAccountBtn = document.getElementById('showCreateAccount');
    const showLoginBtn = document.getElementById('showLogin');
    
    if (showCreateAccountBtn) {
        showCreateAccountBtn.addEventListener('click', (e) => {
            e.preventDefault();
            showCreateAccountForm();
        });
    }
    
    if (showLoginBtn) {
        showLoginBtn.addEventListener('click', (e) => {
            e.preventDefault();
            showLoginForm();
        });
    }
    

    const loginForm = document.getElementById('loginFormElement');
    const createAccountForm = document.getElementById('createAccountFormElement');
    
    if (loginForm) {
        loginForm.addEventListener('submit', handleLoginSubmit);
    }
    
    if (createAccountForm) {
        createAccountForm.addEventListener('submit', handleCreateAccountSubmit);
    }
}

function showLoginForm() {
    hideElement('createAccountForm');
    showElement('loginForm');
}

function showCreateAccountForm() {
    hideElement('loginForm');
    showElement('createAccountForm');
}

function handleLoginSubmit(e) {
    e.preventDefault();
    
    const username = document.getElementById('loginUsername').value;
    const password = document.getElementById('loginPassword').value;
    
    if (!username || !password) {
        showMessage('Please enter both username and password', 'error');
        return;
    }
    
    sendWebSocketMessage({
        type: 'authenticate',
        username: username,
        password: password
    });
}

function handleCreateAccountSubmit(e) {
    e.preventDefault();
    
    const username = document.getElementById('createUsername').value;
    const password = document.getElementById('createPassword').value;
    const confirmPassword = document.getElementById('confirmPassword').value;
    
    if (!username || !password || !confirmPassword) {
        showMessage('Please fill in all fields', 'error');
        return;
    }
    
    if (password !== confirmPassword) {
        showMessage('Passwords do not match', 'error');
        return;
    }
    
    sendWebSocketMessage({
        type: 'create_account',
        username: username,
        password: password
    });
}


function initializeMatchmakingPage() {

    const userData = localStorage.getItem('debateUser');
    if (!userData) {
        window.location.href = 'login.html';
        return;
    }
    
    appState.currentUser = JSON.parse(userData);
    

    setElementText('usernameDisplay', `Welcome, ${appState.currentUser.username}`);
    setElementText('mmrDisplay', `MMR: ${appState.currentUser.mmr}`);
    
    connectWebSocket();
    
    // Show admin button if user has admin privileges
    const adminBtn = document.getElementById('adminButton');
    if (adminBtn) {
        if (appState.currentUser.user_class > 0) {
            showElement('adminButton');
            adminBtn.addEventListener('click', () => {
                window.location.href = 'admin.html';
            });
        } else {
            hideElement('adminButton');
        }
    }

    const logoutBtn = document.getElementById('logoutButton');
    if (logoutBtn) {
        logoutBtn.addEventListener('click', handleLogout);
    }
    

    const startBtn = document.getElementById('startMatchmakingButton');
    const stopBtn = document.getElementById('stopMatchmakingButton');
    
    if (startBtn) {
        startBtn.addEventListener('click', startMatchmaking);
    }
    
    if (stopBtn) {
        stopBtn.addEventListener('click', stopMatchmaking);
    }
    

    const proceedBtn = document.getElementById('proceedToDebateButton');
    if (proceedBtn) {
        proceedBtn.addEventListener('click', proceedToDebate);
    }
}

function handleLogout() {
    localStorage.removeItem('debateUser');
    if (appState.websocket) {
        appState.websocket.close();
    }
    window.location.href = 'login.html';
}

function startMatchmaking() {
    if (!appState.currentUser) return;
    
    sendWebSocketMessage({
        type: 'join_matchmaking',
        user_id: appState.currentUser.id
    });
    
    hideElement('startMatchmakingButton');
    showElement('stopMatchmakingButton');
    showElement('statusContainer');
}

function stopMatchmaking() {
    if (!appState.currentUser) return;
    
    sendWebSocketMessage({
        type: 'leave_matchmaking',
        user_id: appState.currentUser.id
    });
    
    showElement('startMatchmakingButton');
    hideElement('stopMatchmakingButton');
    hideElement('statusContainer');
    hideElement('matchFoundContainer');
}

function handleQueueJoined(data) {
    setElementText('statusText', 'Searching for opponent...');
    if (data.queue_status) {
        setElementText('queueStatus', `Players in queue: ${data.queue_status.queue_size}`);
    }
}

function handleMatchFound(data) {
    appState.currentDebate = {
        id: data.debate_id,
        topic: data.topic,
        opponent: data.opponent
    };
    

    localStorage.setItem('currentDebate', JSON.stringify(appState.currentDebate));
    
    hideElement('statusContainer');
    showElement('matchFoundContainer');
    
    setElementText('opponentUsername', data.opponent.username);
    setElementText('opponentMMR', data.opponent.mmr);
    setElementText('debateTopic', data.topic);
    
    showMessage('Match found! Entering debate room in 3 seconds...', 'success');
    
    // Auto-transition to debate room after 3 seconds
    setTimeout(() => {
        proceedToDebate();
    }, 3000);
}

function proceedToDebate() {
    window.location.href = 'debate.html';
}


function initializeDebatePage() {
    console.log('Initializing debate page with connection overlay...');
    
    // Start with disconnected state to show overlay
    setConnectionState('disconnected');
    
    // Set some basic info
    setElementText('usernameDisplay', 'User');
    setElementText('topicText', 'Loading...');
    
    // Start connection process
    console.log('Starting WebSocket connection...');
    connectWebSocket();
    

    const submitBtn = document.getElementById('submitArgumentButton');
    const clearBtn = document.getElementById('clearArgumentButton');
    const argumentInput = document.getElementById('argumentInput');
    
    if (submitBtn) {
        submitBtn.addEventListener('click', submitArgument);
    }
    
    if (clearBtn) {
        clearBtn.addEventListener('click', clearArgument);
    }
    
    if (argumentInput) {
        argumentInput.addEventListener('input', updateCharacterCount);
    }
    
    // Debug buttons for testing
    const debugBtn = document.getElementById('debugStartButton');
    const debugConnectBtn = document.getElementById('debugConnectButton');
    const debugManualConnectBtn = document.getElementById('debugManualConnectButton');
    const debugStatus = document.getElementById('debugStatus');
    
    if (debugBtn) {
        debugBtn.addEventListener('click', () => {
            console.log('Simulating debate start...');
            if (debugStatus) debugStatus.textContent = 'Testing debate start simulation...';
            
            // Simulate the debate_started message
            handleDebateStarted({
                your_side: 'Proposition',
                opponent_side: 'Negation'
            });
            
            // Start the preparation timer
            handlePrepTimer({
                type: 'prep_timer_start'
            });
            
            // Simulate countdown
            let timeLeft = 180; // 3 minutes
            const countdownInterval = setInterval(() => {
                timeLeft--;
                const minutes = Math.floor(timeLeft / 60);
                const seconds = timeLeft % 60;
                
                handlePrepTimer({
                    display: `${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`,
                    remaining_seconds: timeLeft
                });
                
                if (timeLeft <= 0) {
                    clearInterval(countdownInterval);
                    if (debugStatus) debugStatus.textContent = 'Countdown completed!';
                }
            }, 1000);
        });
    }
    
    if (debugConnectBtn) {
        debugConnectBtn.addEventListener('click', () => {
            console.log('Testing WebSocket connection...');
            if (debugStatus) debugStatus.textContent = 'Testing WebSocket connection...';
            
            if (appState.websocket) {
                const state = appState.websocket.readyState;
                const states = ['CONNECTING', 'OPEN', 'CLOSING', 'CLOSED'];
                if (debugStatus) {
                    debugStatus.textContent = `WebSocket state: ${states[state]}`;
                    if (state === WebSocket.OPEN) {
                        debugStatus.textContent += ' - Connection working!';
                        
                        // Test sending a message
                        sendWebSocketMessage({
                            type: 'start_debate',
                            user_id: appState.currentUser?.id || 1,
                            debate_id: appState.currentDebate?.id || 1
                        });
                    } else if (state === WebSocket.CLOSED || state === WebSocket.CLOSING) {
                        debugStatus.textContent += ' - Reconnecting...';
                        connectWebSocket();
                    }
                }
            } else {
                if (debugStatus) debugStatus.textContent = 'No WebSocket found - creating new connection...';
                connectWebSocket();
                
                // Check again after a delay
                setTimeout(() => {
                    if (appState.websocket) {
                        const state = appState.websocket.readyState;
                        const states = ['CONNECTING', 'OPEN', 'CLOSING', 'CLOSED'];
                        if (debugStatus) debugStatus.textContent = `New connection state: ${states[state]}`;
                    }
                }, 2000);
            }
        });
    }
    
    if (debugManualConnectBtn) {
        debugManualConnectBtn.addEventListener('click', () => {
            alert('Manual connect button clicked!'); // Debug
            console.log('Manual WebSocket connection attempt...');
            if (debugStatus) debugStatus.textContent = 'Manually connecting to ws://localhost:8765...';
            
            try {
                // Force create WebSocket connection directly
                appState.websocket = new WebSocket('ws://localhost:8765');
                
                appState.websocket.onopen = function() {
                    console.log('Manual WebSocket connection opened!');
                    if (debugStatus) {
                        debugStatus.textContent = 'Manual connection opened, authenticating...';
                        debugStatus.style.color = 'orange';
                    }
                    
                    // Auto-authenticate with test user
                    console.log('🔧 DEBUG: Auto-authenticating with test user');
                    const authMessage = {
                        type: 'authenticate',
                        username: 'test',
                        password: 'testpass'
                    };
                    appState.websocket.send(JSON.stringify(authMessage));
                    console.log('🔧 DEBUG: Auth message sent:', authMessage);
                };
                
                appState.websocket.onmessage = function(event) {
                    console.log('Manual WebSocket received:', event.data);
                    
                    try {
                        const data = JSON.parse(event.data);
                        
                        if (data.type === 'auth_response') {
                            if (data.success) {
                                console.log('✅ DEBUG: Authentication successful!', data);
                                appState.currentUserId = data.user_id;
                                appState.isAuthenticated = true;
                                if (debugStatus) {
                                    debugStatus.textContent = `Authenticated as user ID: ${data.user_id}`;
                                    debugStatus.style.color = 'green';
                                }
                                
                                // Now we can test start_debate
                                setTimeout(() => {
                                    console.log('🔧 DEBUG: Testing start_debate message');
                                    const startDebateMessage = {
                                        type: 'start_debate',
                                        user_id: data.user_id,
                                        debate_id: 1
                                    };
                                    appState.websocket.send(JSON.stringify(startDebateMessage));
                                    console.log('🔧 DEBUG: Start debate message sent:', startDebateMessage);
                                }, 1000);
                            } else {
                                console.error('❌ DEBUG: Authentication failed:', data.error);
                                if (debugStatus) {
                                    debugStatus.textContent = `Authentication failed: ${data.error}`;
                                    debugStatus.style.color = 'red';
                                }
                            }
                        }
                        
                        if (data.type === 'debate_started') {
                            console.log('🎉 DEBUG: Received debate_started!', data);
                            if (debugStatus) {
                                debugStatus.textContent = `Debate started: ${data.topic}`;
                                debugStatus.style.color = 'blue';
                            }
                            handleDebateStarted(data);
                        }
                        
                        // Handle all other message types through normal handler
                        handleWebSocketMessage(event);
                        
                    } catch (e) {
                        console.error('❌ DEBUG: Error parsing message:', e);
                    }
                };
                
                appState.websocket.onerror = function(error) {
                    console.error('Manual WebSocket error:', error);
                    if (debugStatus) {
                        debugStatus.textContent = 'Manual connection failed!';
                        debugStatus.style.color = 'red';
                    }
                };
                
                appState.websocket.onclose = function() {
                    console.log('Manual WebSocket connection closed');
                    appState.isAuthenticated = false;
                    appState.currentUserId = null;
                };
                
            } catch (error) {
                console.error('Manual WebSocket creation failed:', error);
                if (debugStatus) {
                    debugStatus.textContent = 'Manual connection error: ' + error.message;
                    debugStatus.style.color = 'red';
                }
            }
        });
    }
}

function handleStartDebateResponse(data) {
    console.log('Start debate response:', data);
    if (data.success) {
        console.log('Debate session started successfully');
        showMessage('Debate session started!', 'success');
    } else {
        console.error('Failed to start debate:', data.error);
        showMessage(`Failed to start debate: ${data.error}`, 'error');
    }
}

function handleDebateInitialized(data) {
    console.log('Debate initialized:', data);
    
    // Store debate info
    appState.currentDebate = {
        id: data.debate_id,
        topic: data.topic,
        yourSide: data.your_side,
        opponentSide: data.opponent_side,
        prepTime: data.prep_time_minutes,
        phase: 'waiting_for_opponent'
    };
    
    // Update UI elements  
    setElementText('debateTopic', data.topic);
    
    // Update side display
    const yourSideElement = document.getElementById('yourSide');
    const opponentSideElement = document.getElementById('opponentSide');
    
    if (yourSideElement) {
        setElementText('yourSide', data.your_side);
    }
    if (opponentSideElement) {
        setElementText('opponentSide', data.opponent_side);
    }
    
    // We're already authenticated, so we're waiting for opponent
    setConnectionState('authenticated');
    
    // Start auto-pinging
    startAutoPing();
    
    console.log(`Debate initialized: "${data.topic}". You are arguing for the ${data.your_side}. Waiting for opponent...`);
}

function handleConnectionStatus(data) {
    console.log('Connection status:', data);
    
    const statusElement = document.getElementById('turnStatus');
    const phaseElement = document.getElementById('debatePhase');
    
    if (data.status) {
        if (statusElement) {
            setElementText('turnStatus', data.status);
        }
        
        // Update phase based on status
        if (data.status.includes('Connecting')) {
            if (phaseElement) setElementText('debatePhase', 'Connecting');
        } else if (data.status.includes('Waiting for opponent')) {
            if (phaseElement) setElementText('debatePhase', 'Waiting for Opponent');
        } else if (data.status.includes('Both players connected')) {
            if (phaseElement) setElementText('debatePhase', 'Starting');
        }
    }
}

function handleDebateStarted(data) {
    console.log('Debate started:', data);
    
    // Both players are ready - transition to debate mode
    setConnectionState('ready');
    
    // Store and display user's side
    if (appState.currentDebate) {
        appState.currentDebate.yourSide = data.your_side;
        appState.currentDebate.opponentSide = data.opponent_side;
        appState.currentDebate.phase = 'preparation';
    }
    
    // Update UI elements
    setElementText('debatePhase', 'Preparation');
    
    // Update side display if elements exist
    const yourSideElement = document.getElementById('yourSide');
    const opponentSideElement = document.getElementById('opponentSide');
    
    if (yourSideElement) {
        setElementText('yourSide', data.your_side);
    }
    if (opponentSideElement) {
        setElementText('opponentSide', data.opponent_side);
    }
    
    addSystemMessage(`Debate started! You are arguing for the ${data.your_side}. Preparation time begins now.`);
    
    // Stop auto-pinging since debate has started
    stopAutoPing();
}

let autoPingInterval = null;

function startAutoPing() {
    // Clear any existing interval
    stopAutoPing();
    
    console.log('Starting auto-ping for debate readiness');
    
    // Send initial ping immediately
    sendPingReady();
    
    // Then ping every 3 seconds
    autoPingInterval = setInterval(() => {
        sendPingReady();
    }, 3000);
}

function stopAutoPing() {
    if (autoPingInterval) {
        console.log('Stopping auto-ping');
        clearInterval(autoPingInterval);
        autoPingInterval = null;
    }
}

function sendPingReady() {
    if (!appState.currentDebate || !appState.currentUserId) {
        console.log('No active debate or user ID, skipping ping');
        return;
    }
    
    console.log('Sending ping ready for debate', appState.currentDebate.id);
    
    sendWebSocketMessage({
        type: 'ping_ready',
        user_id: appState.currentUserId,
        debate_id: appState.currentDebate.id
    });
}

function handlePrepTimer(data) {
    console.log('Prep timer update:', data);
    
    if (data.type === 'prep_timer_start') {
        setElementText('timerLabel', 'Preparation Time');
        const turnStatusElement = document.getElementById('turnStatus');
        if (turnStatusElement) {
            setElementText('turnStatus', 'Preparation phase - get ready for the debate!');
        }
    }
    
    if (data.display) {
        console.log('Setting timer display to:', data.display);
        setElementText('timerDisplay', data.display);
        
        // Update progress bar
        const totalTime = 3 * 60; // 3 minutes in seconds
        const remaining = data.remaining_seconds || 0;
        const progress = ((totalTime - remaining) / totalTime) * 100;
        
        const timerBar = document.getElementById('timerBar');
        if (timerBar) {
            timerBar.style.width = `${progress}%`;
        }
    }
}

function handleDebatePhaseStart(data) {
    setElementText('debatePhase', 'Debate');
    addSystemMessage('Preparation time is over. The debate begins!');
}

function handleYourTurn(data) {
    const sideInfo = data.your_side ? ` (${data.your_side})` : '';
    setElementText('timerLabel', `Your Turn (${data.turn_number})${sideInfo}`);
    setElementText('turnStatus', `It's your turn! Present your ${data.your_side || 'argument'}.`);
    
    showElement('argumentInputContainer');
    hideElement('waitingMessage');
    
    const input = document.getElementById('argumentInput');
    if (input) {
        input.focus();
    }
}

function handleOpponentTurn(data) {
    const opponentSideInfo = data.opponent_side ? ` (${data.opponent_side})` : '';
    setElementText('timerLabel', `Opponent's Turn (${data.turn_number})${opponentSideInfo}`);
    setElementText('turnStatus', `Waiting for opponent's ${data.opponent_side || 'argument'}...`);
    
    hideElement('argumentInputContainer');
    showElement('waitingMessage');
}

function handleTurnTimer(data) {
    if (data.display) {
        setElementText('timerDisplay', data.display);
        
        // Update progress bar
        const totalTime = 2 * 60; // 2 minutes in seconds
        const remaining = data.remaining_seconds || 0;
        const progress = ((totalTime - remaining) / totalTime) * 100;
        
        const timerBar = document.getElementById('timerBar');
        if (timerBar) {
            timerBar.style.width = `${progress}%`;
        }
    }
}

function handleDebateMessage(data) {
    const isCurrentUser = data.sender_id === appState.currentUser.id;
    const messageClass = isCurrentUser ? 'user' : 'opponent';
    
    addDebateMessage(
        data.sender_username,
        data.content,
        messageClass,
        data.timestamp,
        data.turn_number
    );
}

function handleDebateEnded(data) {
    setElementText('debatePhase', 'Finished');
    addSystemMessage('Debate has ended!');
    
    // Store final debate data
    localStorage.setItem('finalDebateData', JSON.stringify(data));
    
    // Redirect to end page
    setTimeout(() => {
        window.location.href = 'end.html';
    }, 2000);
}

function addSystemMessage(content) {
    const log = document.getElementById('debateLog');
    if (!log) return;
    
    const messageDiv = document.createElement('div');
    messageDiv.className = 'log-message system';
    messageDiv.innerHTML = `
        <div class="message-content">${content}</div>
    `;
    
    log.appendChild(messageDiv);
    log.scrollTop = log.scrollHeight;
}

function addDebateMessage(sender, content, type, timestamp, turnNumber) {
    const log = document.getElementById('debateLog');
    if (!log) return;
    
    const time = new Date(timestamp).toLocaleTimeString();
    
    const messageDiv = document.createElement('div');
    messageDiv.className = `log-message ${type}`;
    messageDiv.innerHTML = `
        <div class="message-header">
            <span>${sender} (Turn ${turnNumber})</span>
            <span class="message-timestamp">${time}</span>
        </div>
        <div class="message-content">${content}</div>
    `;
    
    log.appendChild(messageDiv);
    log.scrollTop = log.scrollHeight;
}

function submitArgument() {
    const input = document.getElementById('argumentInput');
    const content = input.value.trim();
    
    if (!content) {
        showMessage('Please enter an argument', 'error');
        return;
    }
    
    if (!appState.currentUser) return;
    
    sendWebSocketMessage({
        type: 'debate_message',
        user_id: appState.currentUser.id,
        content: content
    });
    
    // Clear input
    input.value = '';
    updateCharacterCount();
    
    // Disable input until next turn
    hideElement('argumentInputContainer');
    showElement('waitingMessage');
}

function clearArgument() {
    const input = document.getElementById('argumentInput');
    if (input) {
        input.value = '';
        updateCharacterCount();
    }
}

function updateCharacterCount() {
    const input = document.getElementById('argumentInput');
    const counter = document.getElementById('characterCount');
    const submitBtn = document.getElementById('submitArgumentButton');
    
    if (input && counter) {
        const length = input.value.length;
        counter.textContent = `${length}/1000`;
        
        if (submitBtn) {
            submitBtn.disabled = length === 0;
        }
    }
}

// End Page Functions
function initializeEndPage() {
    // Load user and final debate data
    const userData = localStorage.getItem('debateUser');
    const finalData = localStorage.getItem('finalDebateData');
    
    if (!userData) {
        window.location.href = 'login.html';
        return;
    }
    
    appState.currentUser = JSON.parse(userData);
    
    setElementText('usernameDisplay', appState.currentUser.username);
    
    if (finalData) {
        const debateData = JSON.parse(finalData);
        displayFinalDebateData(debateData);
    }
    
    // Return to lobby button
    const returnBtn = document.getElementById('returnToLobbyButton');
    if (returnBtn) {
        returnBtn.addEventListener('click', () => {
            // Clean up stored data
            localStorage.removeItem('currentDebate');
            localStorage.removeItem('finalDebateData');
            window.location.href = 'matchmaking.html';
        });
    }
    
    // Download log button
    const downloadBtn = document.getElementById('downloadLogButton');
    if (downloadBtn) {
        downloadBtn.addEventListener('click', downloadDebateLog);
    }
}

function displayFinalDebateData(data) {
    // Display topic
    setElementText('finalTopic', data.topic);
    
    // Display debate log
    const log = document.getElementById('finalDebateLog');
    if (log && data.final_log) {
        log.innerHTML = '';
        
        data.final_log.forEach(message => {
            const isCurrentUser = message.sender_id === appState.currentUser.id;
            const messageClass = isCurrentUser ? 'user' : 'opponent';
            
            const messageDiv = document.createElement('div');
            messageDiv.className = `log-message ${messageClass}`;
            
            const time = new Date(message.timestamp).toLocaleTimeString();
            
            messageDiv.innerHTML = `
                <div class="message-header">
                    <span>${message.sender_username} (Turn ${message.turn_number})</span>
                    <span class="message-timestamp">${time}</span>
                </div>
                <div class="message-content">${message.content}</div>
            `;
            
            log.appendChild(messageDiv);
        });
    }
    
    // Calculate and display statistics
    if (data.final_log) {
        const totalArgs = data.final_log.length;
        const userArgs = data.final_log.filter(msg => msg.sender_id === appState.currentUser.id).length;
        const opponentArgs = totalArgs - userArgs;
        
        setElementText('totalArguments', totalArgs);
        setElementText('userArguments', userArgs);
        setElementText('opponentArguments', opponentArgs);
        
        // Calculate duration (mock - would need timestamps from debate start/end)
        setElementText('debateDuration', 'Approximately 15 minutes');
    }
    
    // Set participant names (mock - would need from debate data)
    const debateData = JSON.parse(localStorage.getItem('currentDebate') || '{}');
    if (debateData.opponent) {
        setElementText('participant1', appState.currentUser.username);
        setElementText('participant2', debateData.opponent.username);
    }
}

function downloadDebateLog() {
    const finalData = localStorage.getItem('finalDebateData');
    if (!finalData) {
        showMessage('No debate data available', 'error');
        return;
    }
    
    const data = JSON.parse(finalData);
    
    // Create downloadable content
    let content = `Debate Log\n`;
    content += `Topic: ${data.topic}\n`;
    content += `Date: ${new Date().toLocaleDateString()}\n`;
    content += `\n`;
    
    if (data.final_log) {
        data.final_log.forEach(message => {
            const time = new Date(message.timestamp).toLocaleTimeString();
            content += `[${time}] ${message.sender_username} (Turn ${message.turn_number}):\n`;
            content += `${message.content}\n\n`;
        });
    }
    
    // Create and trigger download
    const blob = new Blob([content], { type: 'text/plain' });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `debate-log-${Date.now()}.txt`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    window.URL.revokeObjectURL(url);
    
    showMessage('Debate log downloaded', 'success');
}

// Admin Panel Functions
function initializeAdminPage() {
    // Check authentication and admin privileges
    const userData = localStorage.getItem('debateUser');
    if (!userData) {
        window.location.href = 'login.html';
        return;
    }
    
    appState.currentUser = JSON.parse(userData);
    
    // Check admin privileges
    if (appState.currentUser.user_class <= 0) {
        showMessage('Access denied. Admin privileges required.', 'error');
        setTimeout(() => {
            window.location.href = 'matchmaking.html';
        }, 2000);
        return;
    }
    
    // Set up user display
    setElementText('usernameDisplay', `Admin: ${appState.currentUser.username}`);
    
    // Connect to WebSocket
    connectWebSocket();
    
    // Set up event handlers
    setupAdminEventHandlers();
    
    // Initialize with users tab
    switchAdminTab('users');
}

function setupAdminEventHandlers() {
    // Tab switching
    const usersTab = document.getElementById('usersTab');
    const debatesTab = document.getElementById('debatesTab');
    const topicsTab = document.getElementById('topicsTab');
    
    if (usersTab) usersTab.addEventListener('click', () => switchAdminTab('users'));
    if (debatesTab) debatesTab.addEventListener('click', () => switchAdminTab('debates'));
    if (topicsTab) topicsTab.addEventListener('click', () => switchAdminTab('topics'));
    
    // Refresh buttons
    const refreshUsersBtn = document.getElementById('refreshUsersButton');
    const refreshDebatesBtn = document.getElementById('refreshDebatesButton');
    const refreshTopicsBtn = document.getElementById('refreshTopicsButton');
    
    if (refreshUsersBtn) refreshUsersBtn.addEventListener('click', () => loadAdminData('users'));
    if (refreshDebatesBtn) refreshDebatesBtn.addEventListener('click', () => loadAdminData('debates'));
    if (refreshTopicsBtn) refreshTopicsBtn.addEventListener('click', () => loadAdminData('topics'));
    
    // Navigation buttons
    const returnBtn = document.getElementById('returnToMatchmakingButton');
    const logoutBtn = document.getElementById('logoutButton');
    
    if (returnBtn) {
        returnBtn.addEventListener('click', () => {
            window.location.href = 'matchmaking.html';
        });
    }
    
    if (logoutBtn) {
        logoutBtn.addEventListener('click', handleLogout);
    }
    
    // Modal handling
    const closeModalBtn = document.getElementById('closeModalButton');
    const cancelEditBtn = document.getElementById('cancelEditButton');
    const editForm = document.getElementById('editForm');
    
    if (closeModalBtn) closeModalBtn.addEventListener('click', hideEditModal);
    if (cancelEditBtn) cancelEditBtn.addEventListener('click', hideEditModal);
    if (editForm) editForm.addEventListener('submit', handleEditSubmit);
}

function switchAdminTab(tab) {
    // Remove active class from all tabs and sections
    document.querySelectorAll('.tab-button').forEach(btn => btn.classList.remove('active'));
    document.querySelectorAll('.admin-tab-content').forEach(section => section.classList.remove('active'));
    
    // Add active class to selected tab and section
    const tabButton = document.getElementById(`${tab}Tab`);
    const tabSection = document.getElementById(`${tab}Section`);
    
    if (tabButton) tabButton.classList.add('active');
    if (tabSection) tabSection.classList.add('active');
    
    // Load data for the selected tab
    loadAdminData(tab);
}

function loadAdminData(type) {
    if (!appState.websocket || appState.websocket.readyState !== WebSocket.OPEN) {
        showMessage('WebSocket connection required', 'error');
        return;
    }
    
    sendWebSocketMessage({
        type: 'admin_get_data',
        data_type: type,
        user_id: appState.currentUser.id
    });
}

function displayAdminData(type, data) {
    switch(type) {
        case 'users':
            displayUsersTable(data);
            break;
        case 'debates':
            displayDebatesTable(data);
            break;
        case 'topics':
            displayTopicsTable(data);
            break;
    }
}

function displayUsersTable(users) {
    const tbody = document.getElementById('usersTableBody');
    if (!tbody) return;
    
    if (!users || users.length === 0) {
        tbody.innerHTML = '<tr><td colspan="5" class="loading">No users found</td></tr>';
        return;
    }
    
    tbody.innerHTML = users.map(user => `
        <tr>
            <td>${user.id}</td>
            <td>${user.username}</td>
            <td>${user.mmr}</td>
            <td>${user.user_class}</td>
            <td>
                <button class="action-button edit" onclick="editUser(${user.id})">Edit</button>
                <button class="action-button delete" onclick="deleteUser(${user.id})">Delete</button>
            </td>
        </tr>
    `).join('');
}

function displayDebatesTable(debates) {
    const tbody = document.getElementById('debatesTableBody');
    if (!tbody) return;
    
    if (!debates || debates.length === 0) {
        tbody.innerHTML = '<tr><td colspan="7" class="loading">No debates found</td></tr>';
        return;
    }
    
    tbody.innerHTML = debates.map(debate => `
        <tr>
            <td>${debate.id}</td>
            <td>${debate.user1_name || debate.user1_id}</td>
            <td>${debate.user2_name || debate.user2_id}</td>
            <td>${debate.topic.substring(0, 50)}${debate.topic.length > 50 ? '...' : ''}</td>
            <td>${debate.winner_name || debate.winner || 'N/A'}</td>
            <td>${new Date(debate.timestamp).toLocaleString()}</td>
            <td>
                <button class="action-button edit" onclick="viewDebate(${debate.id})">View</button>
                <button class="action-button delete" onclick="deleteDebate(${debate.id})">Delete</button>
            </td>
        </tr>
    `).join('');
}

function displayTopicsTable(topics) {
    const tbody = document.getElementById('topicsTableBody');
    if (!tbody) return;
    
    if (!topics || topics.length === 0) {
        tbody.innerHTML = '<tr><td colspan="3" class="loading">No topics found</td></tr>';
        return;
    }
    
    tbody.innerHTML = topics.map(topic => `
        <tr>
            <td>${topic.id}</td>
            <td>${topic.topic_text}</td>
            <td>
                <button class="action-button edit" onclick="editTopic(${topic.id})">Edit</button>
                <button class="action-button delete" onclick="deleteTopic(${topic.id})">Delete</button>
            </td>
        </tr>
    `).join('');
}

function editUser(userId) {
    sendWebSocketMessage({
        type: 'admin_get_item',
        data_type: 'user',
        item_id: userId,
        user_id: appState.currentUser.id
    });
}

function deleteUser(userId) {
    if (confirm('Are you sure you want to delete this user? This action cannot be undone.')) {
        sendWebSocketMessage({
            type: 'admin_delete_item',
            data_type: 'user',
            item_id: userId,
            user_id: appState.currentUser.id
        });
    }
}

function editTopic(topicId) {
    sendWebSocketMessage({
        type: 'admin_get_item',
        data_type: 'topic',
        item_id: topicId,
        user_id: appState.currentUser.id
    });
}

function deleteTopic(topicId) {
    if (confirm('Are you sure you want to delete this topic?')) {
        sendWebSocketMessage({
            type: 'admin_delete_item',
            data_type: 'topic',
            item_id: topicId,
            user_id: appState.currentUser.id
        });
    }
}

function viewDebate(debateId) {
    sendWebSocketMessage({
        type: 'admin_get_item',
        data_type: 'debate',
        item_id: debateId,
        user_id: appState.currentUser.id
    });
}

function deleteDebate(debateId) {
    if (confirm('Are you sure you want to delete this debate record?')) {
        sendWebSocketMessage({
            type: 'admin_delete_item',
            data_type: 'debate',
            item_id: debateId,
            user_id: appState.currentUser.id
        });
    }
}

function showEditModal(type, item) {
    const modal = document.getElementById('editModal');
    const modalTitle = document.getElementById('modalTitle');
    const formFields = document.getElementById('formFields');
    
    if (!modal || !modalTitle || !formFields) return;
    
    // Set title
    modalTitle.textContent = `Edit ${type.charAt(0).toUpperCase() + type.slice(1)}`;
    
    // Clear and populate form fields
    formFields.innerHTML = '';
    
    switch(type) {
        case 'user':
            formFields.innerHTML = `
                <div class="form-field">
                    <label for="editUsername">Username:</label>
                    <input type="text" id="editUsername" value="${item.username}" required>
                </div>
                <div class="form-field">
                    <label for="editMMR">MMR:</label>
                    <input type="number" id="editMMR" value="${item.mmr}" required>
                </div>
                <div class="form-field">
                    <label for="editUserClass">User Class:</label>
                    <input type="number" id="editUserClass" value="${item.user_class}" required>
                </div>
                <input type="hidden" id="editItemId" value="${item.id}">
                <input type="hidden" id="editItemType" value="user">
            `;
            break;
        case 'topic':
            formFields.innerHTML = `
                <div class="form-field">
                    <label for="editTopicText">Topic Text:</label>
                    <textarea id="editTopicText" rows="4" required>${item.topic_text}</textarea>
                </div>
                <input type="hidden" id="editItemId" value="${item.id}">
                <input type="hidden" id="editItemType" value="topic">
            `;
            break;
        case 'debate':
            formFields.innerHTML = `
                <div class="form-field">
                    <label>Debate ID:</label>
                    <input type="text" value="${item.id}" disabled>
                </div>
                <div class="form-field">
                    <label>Topic:</label>
                    <textarea rows="3" disabled>${item.topic}</textarea>
                </div>
                <div class="form-field">
                    <label>Log:</label>
                    <textarea rows="10" disabled>${item.log}</textarea>
                </div>
                <div class="form-field">
                    <label>Winner:</label>
                    <input type="text" value="${item.winner_name || item.winner || 'N/A'}" disabled>
                </div>
                <div class="form-field">
                    <label>Timestamp:</label>
                    <input type="text" value="${new Date(item.timestamp).toLocaleString()}" disabled>
                </div>
            `;
            // Hide save button for read-only debate view
            const saveBtn = modal.querySelector('button[type="submit"]');
            if (saveBtn) saveBtn.style.display = 'none';
            break;
    }
    
    // Show modal
    modal.classList.remove('hidden');
    modal.classList.add('active');
}

function hideEditModal() {
    const modal = document.getElementById('editModal');
    if (modal) {
        modal.classList.add('hidden');
        modal.classList.remove('active');
    }
}

function handleEditSubmit(e) {
    e.preventDefault();
    
    const itemType = document.getElementById('editItemType')?.value;
    const itemId = document.getElementById('editItemId')?.value;
    
    if (!itemType || !itemId) return;
    
    let updateData = { id: itemId };
    
    switch(itemType) {
        case 'user':
            updateData.username = document.getElementById('editUsername')?.value;
            updateData.mmr = parseInt(document.getElementById('editMMR')?.value);
            updateData.user_class = parseInt(document.getElementById('editUserClass')?.value);
            break;
        case 'topic':
            updateData.topic_text = document.getElementById('editTopicText')?.value;
            break;
    }
    
    sendWebSocketMessage({
        type: 'admin_update_item',
        data_type: itemType,
        item_data: updateData,
        user_id: appState.currentUser.id
    });
    
    hideEditModal();
}

// Admin WebSocket message handlers
function handleAdminDataResponse(data) {
    if (data.success) {
        displayAdminData(data.data_type, data.data);
    } else {
        showMessage(data.error || 'Failed to load data', 'error');
    }
}

function handleAdminItemResponse(data) {
    if (data.success) {
        showEditModal(data.data_type, data.item);
    } else {
        showMessage(data.error || 'Failed to load item', 'error');
    }
}

function handleAdminUpdateResponse(data) {
    if (data.success) {
        showMessage('Item updated successfully', 'success');
        // Refresh the current tab data
        const activeTab = document.querySelector('.tab-button.active');
        if (activeTab) {
            const tabType = activeTab.id.replace('Tab', '');
            loadAdminData(tabType);
        }
    } else {
        showMessage(data.error || 'Failed to update item', 'error');
    }
}

function handleAdminDeleteResponse(data) {
    if (data.success) {
        showMessage('Item deleted successfully', 'success');
        // Refresh the current tab data
        const activeTab = document.querySelector('.tab-button.active');
        if (activeTab) {
            const tabType = activeTab.id.replace('Tab', '');
            loadAdminData(tabType);
        }
    } else {
        showMessage(data.error || 'Failed to delete item', 'error');
    }
}

// Initialize based on page
document.addEventListener('DOMContentLoaded', () => {
    // Detect which page we're on and initialize accordingly
    const path = window.location.pathname;
    
    if (path.includes('login.html') || path === '/' || path.endsWith('/')) {
        initializeLoginPage();
    } else if (path.includes('matchmaking.html')) {
        initializeMatchmakingPage();
    } else if (path.includes('debate.html')) {
        initializeDebatePage();
    } else if (path.includes('end.html')) {
        initializeEndPage();
    }
});
