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
    const socket = new WebSocket('ws://127.0.0.1:8765'); // Replace with your WebSocket server URL

    // Handle WebSocket connection open
    socket.addEventListener('open', () => {
        console.log('WebSocket connection established');
        if (errorMessage) errorMessage.classList.add('hidden'); // Hide error if connection succeeds
        clearTimeout(connectionTimeout); // Clear failure detection timeout
    });
	
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
    }, 2000); // Wait 3 seconds before assuming failure

    // Try Again button click event
    tryAgainButton.addEventListener('click', () => {
        window.location.reload(); // Refresh the page
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
			displayUserEmail(emailInput.value);
			enableFilesMenu();
			alert(`Logged in. Welcome! (${emailInput.value})`);
			clearEmailPw();
		}
		else if (response_code == 'OUTP') {
			let runOutputData = JSON.parse(data[0]);
			runOutput = runOutputData['output'];
			updateOutput(runOutput);
		}
		else if (response_code == 'ERRR') {
			clearEmailPw();
			errorCode = data[0];
			alert(`Error: ${errors[errorCode]}`);
		}
		
    });
	
	let errors = {
		"001": "General Error",
		"101": "Login Failed",
		"102": "User already exists"
	};

    // Function to send code to the server
    function sendCodeToServer() {
        const code = codeInput.value;
        if (code.trim() === '') {
            alert('Please write some code before running.');
            return;
        }
		
		// Clear output window content
		clearOutput();
		
		const toSend = `EXEC~${JSON.stringify({ code })}`
        socket.send(toSend);
    }

    // Run button click event
    runBtn.addEventListener('click', sendCodeToServer);
	
	// Initialize output window
	output.srcdoc = `
        <html>
            <head>
                <style>
                    body {
                        background-color: #1e1e1e;
                        color: #e0e0e0;
                        font-family: 'Iosevka', 'Consolas', 'Courier New', monospace;
                        font-size: 16px;
                        margin: 0;
                        padding: 15px;
                    }
                    pre {
                        margin: 0;
                        white-space: pre-wrap;
                    }
                </style>
            </head>
            <body class="iframe-styles">
                <pre id="pre-text"></pre>
            </body>
        </html>
    `;
    
    // Wait for iframe to load
    output.onload = function() {
        // Now it's ready for updates
        console.log("Output iframe initialized");
    };

	// Function to append text to output
	function updateOutput(outputText) {
		if (output.contentDocument) {
			const preElement = output.contentDocument.getElementById("pre-text");
			if (preElement) {
				preElement.textContent += outputText;
			}
		}
	}
	
	// Function to clear the output window
	function clearOutput() {
		if (output.contentDocument) {
			const preElement = output.contentDocument.getElementById("pre-text");
			if (preElement) {
				preElement.textContent = ""; // Clear the content
			}
		}
	}
	
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
	
	 // Handle tab key for indentation
    codeInput.addEventListener('keydown', function(e) {
        if (e.key === 'Tab') {
            e.preventDefault(); // Prevent focus moving to next element
            
            // Get cursor position
            const start = this.selectionStart;
            const end = this.selectionEnd;
            
            // Insert 4 spaces at cursor position
            this.value = this.value.substring(0, start) + '    ' + this.value.substring(end);
            
            // Move cursor after the inserted tab
            this.selectionStart = this.selectionEnd = start + 4;
            
            // Update line numbers
            updateLineNumbers();
        }
    });
    
    // Auto-indent on new line (Enter key)
    codeInput.addEventListener('keydown', function(e) {
        if (e.key === 'Enter') {
            e.preventDefault();
            
            const start = this.selectionStart;
            const end = this.selectionEnd;
            
            // Get current line's indentation
            const currentLine = this.value.substring(0, start).split('\n').pop();
            const match = currentLine.match(/^(\s+)/);
            const indent = match ? match[1] : '';
            
            // Check if line ends with a colon (Python blocks)
            const endsWithColon = currentLine.trim().endsWith(':');
            const newIndent = endsWithColon ? indent + '    ' : indent;
            
            // Insert new line with proper indentation
            this.value = this.value.substring(0, start) + '\n' + newIndent + this.value.substring(end);
            
            // Move cursor after indentation on new line
            this.selectionStart = this.selectionEnd = start + 1 + newIndent.length;
            
            // Update line numbers
            updateLineNumbers();
        }
    });

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
	
	// Function to replace login button with user email display
    function displayUserEmail(email) {
        const authBtn = document.getElementById('auth-btn');
        if (!authBtn) return;
        
        // Get current dimensions and position of the auth button
        const authBtnRect = authBtn.getBoundingClientRect();
        const minWidth = authBtnRect.width;
        const height = authBtnRect.height;
        
        // Create user email display element
        const userEmailDisplay = document.createElement('div');
        userEmailDisplay.id = 'user-email-display';
        userEmailDisplay.className = 'user-email-display';
        
        // Don't set fixed width - let it expand naturally
        userEmailDisplay.style.minWidth = `${minWidth}px`;
        userEmailDisplay.style.height = `${height}px`;
        userEmailDisplay.style.maxWidth = '300px'; // Set a maximum width to prevent excessive stretching
        
        // Add email text with user icon
        userEmailDisplay.innerHTML = `<i class="fas fa-user"></i> ${email}`;
        
        // Replace the auth button with our new element
        authBtn.parentNode.replaceChild(userEmailDisplay, authBtn);
        
        console.log(`Replaced login button with email: ${email}`);
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
	
	// Function to enable the menu button
    function enableFilesMenu() {
        if (menuBtn) {
            menuBtn.removeAttribute('disabled');
            console.log('Files menu button enabled');
        }
    }
	
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
	
	// Initial setup of existing DOM elements
    setupFolderToggling();
	
	// Function to add event listeners to folder headers
    function setupFolderToggling() {
        // Get all folder headers
        const folderHeaders = document.querySelectorAll('.folder-header');
        
        // Add click event to each folder header
        folderHeaders.forEach(header => {
            // Remove any existing listeners first to prevent duplicates
            const newHeader = header.cloneNode(true);
            header.parentNode.replaceChild(newHeader, header);
            
            newHeader.addEventListener('click', function(e) {
                e.stopPropagation(); // Prevent event bubbling
                
                // Toggle collapsed state
                this.classList.toggle('collapsed');
                
                // Find the corresponding folder contents
                const folderContents = this.parentNode.querySelector('.folder-contents');
                if (folderContents) {
                    folderContents.classList.toggle('hidden');
                }
                
                // Change folder icon
                const folderIcon = this.querySelector('.fa-folder, .fa-folder-open');
                if (folderIcon) {
                    if (this.classList.contains('collapsed')) {
                        folderIcon.className = 'fas fa-folder';
                    } else {
                        folderIcon.className = 'fas fa-folder-open';
                    }
                }
                
                // Change chevron direction
                const chevron = this.querySelector('.folder-toggle');
                if (chevron) {
                    chevron.style.transform = this.classList.contains('collapsed') ? 
                        'rotate(-90deg)' : 'rotate(0deg)';
                }
            });
        });
    }

    // Function to create a dynamic file tree from the fileStructure array
    function populateFileTree() {
        const rootContents = document.querySelector('.root-folder > .folder-contents');
        if (!rootContents) return;
        
        // Clear existing content
        rootContents.innerHTML = '';
        
        // Add file structure
        fileStructure.forEach(item => {
            if (item.type === 'folder') {
                const folderItem = createFolderItem(item);
                rootContents.appendChild(folderItem);
            } else {
                const fileItem = createFileItem(item);
                rootContents.appendChild(fileItem);
            }
        });
        
        // Setup folder toggling for newly created elements
        setupFolderToggling();
    }
    
    // Function to create a folder item
    function createFolderItem(folder) {
        const folderItem = document.createElement('div');
        folderItem.className = 'folder-item';
        
        const folderHeader = document.createElement('div');
        folderHeader.className = 'folder-header collapsed';
        
        const folderIcon = document.createElement('i');
        folderIcon.className = 'fas fa-folder';
        
        const folderName = document.createElement('span');
        folderName.className = 'folder-name';
        folderName.textContent = folder.name;
        
        const folderToggle = document.createElement('i');
        folderToggle.className = 'fas fa-chevron-down folder-toggle';
        folderToggle.style.transform = 'rotate(-90deg)';
        
        folderHeader.appendChild(folderIcon);
        folderHeader.appendChild(folderName);
        folderHeader.appendChild(folderToggle);
        
        const folderContents = document.createElement('div');
        folderContents.className = 'folder-contents hidden';
        
        // Add children if they exist
        if (folder.children && folder.children.length > 0) {
            folder.children.forEach(child => {
                if (child.type === 'folder') {
                    folderContents.appendChild(createFolderItem(child));
                } else {
                    folderContents.appendChild(createFileItem(child));
                }
            });
        }
        
        folderItem.appendChild(folderHeader);
        folderItem.appendChild(folderContents);
        
        return folderItem;
    }
    
    // Function to create a file item
    function createFileItem(file) {
        const fileItem = document.createElement('div');
        fileItem.className = 'file-item';
        
        const fileIcon = document.createElement('i');
        fileIcon.className = getFileIcon(file.extension);
        
        const fileName = document.createElement('span');
        fileName.className = 'file-name';
        fileName.textContent = file.name;
        
        fileItem.appendChild(fileIcon);
        fileItem.appendChild(fileName);
        
        return fileItem;
    }
    
    // Get file icon based on extension
    function getFileIcon(extension) {
        switch(extension) {
            case 'html': return 'fas fa-file-code html-icon';
            case 'css': return 'fas fa-file-code css-icon';
            case 'js': return 'fas fa-file-code js-icon';
            case 'py': return 'fas fa-file-code py-icon';
            case 'json': return 'fas fa-file-code json-icon';
            case 'csv': return 'fas fa-file-csv';
            case 'txt': return 'fas fa-file-alt';
            default: return 'fas fa-file';
        }
    }
    
    // Add event listener to menu button to also repopulate the file tree
    if (menuBtn) {
        menuBtn.addEventListener('click', function() {
            // Populate the sidebar with files
            populateFileTree();
        });
    }
	
	// Sample file structure (in a real app, this would come from the server)
	const fileStructure = [
		{
			type: 'folder',
			name: 'Project 1',
			children: [
				{ type: 'file', name: 'index.html', extension: 'html' },
				{ type: 'file', name: 'styles.css', extension: 'css' },
				{ type: 'file', name: 'script.js', extension: 'js' }
			]
		},
		{
			type: 'folder',
			name: 'Project 2',
			children: [
				{ type: 'file', name: 'main.py', extension: 'py' },
				{ 
					type: 'folder', 
					name: 'data',
					children: [
						{ type: 'file', name: 'data.csv', extension: 'csv' },
						{ type: 'file', name: 'config.json', extension: 'json' }
					]
				}
			]
		},
		{ type: 'file', name: 'notes.txt', extension: 'txt' }
	];
});