let appState = {
    websocket: null,
    currentUser: null,
    currentDebate: null,
    reconnectAttempts: 0,
    maxReconnectAttempts: 5,
    reconnectDelay: 2000,
    isConnected: false
};

function connectWebSocket() {
    const isLocalhost = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1';
    
    let wsUrl;
    if (isLocalhost) {
        wsUrl = window.CONFIG.LOCAL_WEBSOCKET_URL;
    } else {
        wsUrl = window.CONFIG.WEBSOCKET_URL;
        console.log('Connecting to production WebSocket:', wsUrl);
    }
    
    try {
        appState.websocket = new WebSocket(wsUrl);
        
        appState.websocket.onopen = handleWebSocketOpen;
        appState.websocket.onmessage = handleWebSocketMessage;
        appState.websocket.onclose = handleWebSocketClose;
        appState.websocket.onerror = handleWebSocketError;
        
        updateConnectionStatus('Connecting...');
    } catch (error) {
        console.error('WebSocket connection failed:', error);
        updateConnectionStatus('Connection failed');
    }
}

function handleWebSocketOpen() {
    console.log('WebSocket connected');
    appState.isConnected = true;
    appState.reconnectAttempts = 0;
    updateConnectionStatus('Connected', true);
}

function handleWebSocketMessage(event) {
    try {
        const data = JSON.parse(event.data);
        console.log('Received message:', data);
        
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
            case 'debate_started':
                handleDebateStarted(data);
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
        

        localStorage.setItem('debateUser', JSON.stringify(appState.currentUser));
        
        showMessage('Login successful!', 'success');
        

        setTimeout(() => {
            window.location.href = 'matchmaking.html';
        }, 1000);
    } else {
        showMessage(data.error, 'error');
    }
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
    
    showMessage('Match found!', 'success');
}

function proceedToDebate() {
    window.location.href = 'debate.html';
}


function initializeDebatePage() {

    const userData = localStorage.getItem('debateUser');
    const debateData = localStorage.getItem('currentDebate');
    
    if (!userData || !debateData) {
        window.location.href = 'login.html';
        return;
    }
    
    appState.currentUser = JSON.parse(userData);
    appState.currentDebate = JSON.parse(debateData);
    

    setElementText('usernameDisplay', appState.currentUser.username);
    setElementText('topicText', appState.currentDebate.topic);
    setElementText('opponentUsername', appState.currentDebate.opponent.username);
    setElementText('opponentMMR', `MMR: ${appState.currentDebate.opponent.mmr}`);
    
    connectWebSocket();
    
    // Start the debate session once connected
    setTimeout(() => {
        if (appState.ws && appState.ws.readyState === WebSocket.OPEN) {
            sendMessage({
                type: 'start_debate',
                user_id: appState.currentUser.id,
                debate_id: appState.currentDebate.id
            });
        }
    }, 1000); // Wait 1 second for WebSocket to connect
    

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
}

function handleStartDebateResponse(data) {
    if (data.success) {
        console.log('Debate session started successfully');
    } else {
        showMessage(`Failed to start debate: ${data.error}`, 'error');
    }
}

function handleDebateStarted(data) {
    setElementText('debatePhase', 'Preparation');
    
    // Store and display user's side
    appState.currentDebate.yourSide = data.your_side;
    appState.currentDebate.opponentSide = data.opponent_side;
    
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
}

function handlePrepTimer(data) {
    if (data.type === 'prep_timer_start') {
        setElementText('timerLabel', 'Preparation Time');
        setElementText('turnStatus', 'Preparation phase - get ready for the debate!');
    }
    
    if (data.display) {
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
