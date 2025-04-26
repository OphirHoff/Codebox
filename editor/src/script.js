document.addEventListener('DOMContentLoaded', function () {
    const codeInput = document.getElementById('gravity-code');
    const output = document.getElementById('output');
    const runBtn = document.getElementById('run-btn');
    const increaseFontBtn = document.getElementById('increase-font');
    const decreaseFontBtn = document.getElementById('decrease-font');
    const fullscreenBtn = document.getElementById('fullscreen-btn');
    const exitFullscreenBtn = document.getElementById('exit-fullscreen-btn');
    const lineNumbers = document.getElementById('line-numbers');
    const loadingContainer = document.getElementById('loading-container');
    const codeEditor = document.querySelector('.code-editor');
    const errorMessage = document.getElementById('error-message');
    const tryAgainButton = document.getElementById('try-again-button');
    const authBtn = document.getElementById('auth-btn');
    const authModal = document.getElementById('auth-modal');
    const authForm = document.getElementById('auth-form');
	const menuBtn = document.getElementById('menu-btn');
	const sidebar = document.getElementById('sidebar');
	const closeSidebarBtn = document.getElementById('close-sidebar-btn');
	const sidebarOverlay = document.getElementById('sidebar-overlay');
    const loginBtn = document.querySelector('.login-btn');
    const registerBtn = document.querySelector('.register-btn');
    const emailInput = document.getElementById('email');
    const passwordInput = document.getElementById('password');

    // Simulate loading sequence
    setTimeout(() => {
        loadingContainer.classList.add('hidden');
        document.body.style.overflow = 'auto';
    }, 1300);

    // WebSocket connection
    const socket = new WebSocket('ws://localhost:8765'); // Replace with your WebSocket server URL

    // Handle WebSocket connection open
    socket.addEventListener('open', () => {
        console.log('WebSocket connection established');
        if (errorMessage) errorMessage.classList.add('hidden'); // Hide error if connection succeeds
        clearTimeout(connectionTimeout); // Clear failure detection timeout
    });

    // Handle WebSocket messages (server responses)
    socket.addEventListener('message', (event) => {
		
		msg = event.data;
		console.log(`Received: ${msg}`);
		
		fields = msg.split('~');
		response_code = fields[0];
		data = fields.slice(1);
		
		if (response_code == 'REGR') {
			alert('Registered successfuly!');
			clearEmailPw();
		}
		else if (response_code == 'LOGR') {
			alert(`Logged in. Welcome! (${emailInput.value})`);
			clearEmailPw();
		}
		else if (response_code == 'ERRR') {
			clearEmailPw();
			errorCode = data[0];
			alert(`Error: ${errors[errorCode]}`);
		}
		
    });
	
	let errors = {
		"001": "General Error",
		"102": "User already exists"
	};

    // Handle WebSocket errors
    socket.addEventListener('error', () => {
        console.error('WebSocket error occurred');
        showError();
    });

    // Handle WebSocket connection close
    socket.addEventListener('close', (event) => {
        console.warn('WebSocket connection closed:', event);
        showError();
    });

    // Function to show error message
    function showError() {
        if (errorMessage) {
            console.warn('Displaying error message.');
            errorMessage.classList.remove('hidden'); // Show error message
            errorMessage.style.display = 'block'; // Ensure it's visible
        } else {
            console.warn('Error message element not found.');
        }
    }

    // Detect if the WebSocket connection fails silently
    const connectionTimeout = setTimeout(() => {
        if (socket.readyState !== WebSocket.OPEN) {
            console.warn('WebSocket connection failed (timeout)');
            showError();
        }
    }, 1300); // Wait 3 seconds before assuming failure

    // Try Again button click event
    tryAgainButton.addEventListener('click', () => {
        window.location.reload(); // Refresh the page
    });

    // Function to send code to the server
    function sendCodeToServer() {
        const code = codeInput.value;
        if (code.trim() === '') {
            alert('Please write some code before running.');
            return;
        }
        socket.send(JSON.stringify({ code }));
    }

    // Run button click event
    runBtn.addEventListener('click', sendCodeToServer);

    // Font size controls
    let fontSize = 18;
    const minFontSize = 12;
    const maxFontSize = 24;

    increaseFontBtn.addEventListener('click', () => {
        if (fontSize < maxFontSize) {
            fontSize += 2;
            codeInput.style.fontSize = `${fontSize}px`;
            updateLineNumbers();
        }
    });

    decreaseFontBtn.addEventListener('click', () => {
        if (fontSize > minFontSize) {
            fontSize -= 2;
            codeInput.style.fontSize = `${fontSize}px`;
            updateLineNumbers();
        }
    });

    // Full-screen button click event
    fullscreenBtn.addEventListener('click', () => {
        codeEditor.classList.add('fullscreen');
        fullscreenBtn.style.display = 'none';
        exitFullscreenBtn.style.display = 'block';
    });

    // Exit full-screen button click event
    exitFullscreenBtn.addEventListener('click', () => {
        codeEditor.classList.remove('fullscreen');
        exitFullscreenBtn.style.display = 'none';
        fullscreenBtn.style.display = 'inline-flex';
    });

    // Update line numbers
    function updateLineNumbers() {
        const lines = codeInput.value.split('\n').length;
        lineNumbers.innerHTML = Array.from({ length: lines }, (_, i) => i + 1).join('<br>');
    }

    // Throttle the updateLineNumbers function
    let isThrottled = false;
    codeInput.addEventListener('input', () => {
        if (!isThrottled) {
            updateLineNumbers();
            isThrottled = true;
            setTimeout(() => {
                isThrottled = false;
            }, 100);
        }
    });
	
	// Clear email & password input fields
	function clearEmailPw() {
		emailInput.value = '';
		passwordInput.value = '';
	}

    // Initial update
    updateLineNumbers();

    // Auth modal functionality
    authBtn.addEventListener('click', () => {
        authModal.classList.remove('hidden');
    });

    authModal.addEventListener('click', (e) => {
        if (e.target === authModal) {
            authModal.classList.add('hidden');
        }
    });

    authForm.addEventListener('submit', (e) => {
        e.preventDefault();
        const email = emailInput.value;
        const password = passwordInput.value;
    
        // Validate inputs
		if (!email || !password) {
			alert('Please enter both email and password');
			return;
		}
		
		// Create the login message in the required format
		const loginMessage = `LOGN~${email}~${password}`;
		
		// Send to server through the existing WebSocket
		if (socket && socket.readyState === WebSocket.OPEN) {
			socket.send(loginMessage);
			
			console.log('Login data sent:', loginMessage);
			authModal.classList.add('hidden');
		} else {
			console.error('WebSocket not connected');
			alert('Unable to login: Server connection not available');
		}
    });

    // Event listener for the Register button
    registerBtn.addEventListener('click', (e) => {
		e.preventDefault(); // Prevent form submission
		
		const email = emailInput.value;
		
		const password = passwordInput.value;
		
		// Validate inputs
		if (!email || !password) {
			alert('Please enter both email and password');
			return;
		}
		
		// Create the registration message in the required format
		const registrationMessage = `REGI~${email}~${password}`;
		
		// Send to server through the existing WebSocket
		if (socket && socket.readyState === WebSocket.OPEN) {
			socket.send(registrationMessage);
			console.log('Registration data sent:', registrationMessage);
		} else {
			console.error('WebSocket not connected');
			alert('Unable to register: Server connection not available');
		}
    });
	
	// Open sidebar when menu button is clicked
	menuBtn.addEventListener('click', () => {
		sidebar.classList.add('open');
		sidebarOverlay.classList.remove('hidden');
		document.body.style.overflow = 'hidden'; // Prevent scrolling when sidebar is open
	});

	// Close sidebar function
	function closeSidebar() {
		sidebar.classList.remove('open');
		sidebarOverlay.classList.add('hidden');
		document.body.style.overflow = 'auto'; // Re-enable scrolling
	}

	// Close sidebar when close button is clicked
	closeSidebarBtn.addEventListener('click', closeSidebar);

	// Close sidebar when clicking outside
	sidebarOverlay.addEventListener('click', closeSidebar);
});