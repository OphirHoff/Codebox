document.addEventListener('DOMContentLoaded', function () {
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
	const newFileBtn = document.getElementById('new-file-btn');
    const newFolderBtn = document.getElementById('new-folder-btn');
    const createModal = document.getElementById('create-modal');
    const createModalTitle = document.getElementById('create-modal-title');
    const createModalIcon = document.getElementById('create-modal-icon');
    const createModalText = document.getElementById('create-modal-text');
    const createNameInput = document.getElementById('create-name-input');
    const cancelCreateBtn = document.getElementById('cancel-create-btn');
    const confirmCreateBtn = document.getElementById('confirm-create-btn');
	const contextMenu = document.getElementById('context-menu');
    const deleteFileBtn = document.getElementById('delete-file-btn');
    const renameFileBtn = document.getElementById('rename-file-btn');
    const downloadFileBtn = document.getElementById('download-file-btn');
    let currentContextMenuFile = null; // To store the file element that was right-clicked
	let monacoEditor;
	
	require.config({ paths: { 'vs': 'https://cdnjs.cloudflare.com/ajax/libs/monaco-editor/0.44.0/min/vs' } });

	require(['vs/editor/editor.main'], function () {
		monacoEditor = monaco.editor.create(document.getElementById('editor'), {
			value: `# This is Codebox!\n# Write, Run & Save your Python code here\n# (c) Ophir Hoffman. All rights reserved.\n\nprint("Welcome to Codebox!")`,
			language: 'python',
			theme: 'vs-dark',
			fontSize: fontSize
		});
	});
	
	// Auto-resize editor when window size changes
	window.addEventListener('resize', () => {
		if (monacoEditor) {
			monacoEditor.layout();
		}
	});
	
	// Set editor read-only
	function disableEditor() {
		monacoEditor.updateOptions({ readOnly: true });
	}
	
	// Set editor enabled
	function enableEditor() {
		monacoEditor.updateOptions({ readOnly: false });
	}
	
    // Simulate loading sequence
    setTimeout(() => {
        loadingContainer.classList.add('hidden');
        document.body.style.overflow = 'auto';
    }, 1300);

    // WebSocket connection
    const socket = new WebSocket('wss://icodebox.duckdns.org:8765'); // Replace with your WebSocket server URL

    // Handle WebSocket connection open
    socket.addEventListener('open', () => {
        console.log('WebSocket connection established');
        if (errorMessage) errorMessage.classList.add('hidden'); // Hide error if connection succeeds
        clearTimeout(connectionTimeout); // Clear failure detection timeout
		
		// Initialize input handling
		initializeInputHandling(socket);
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
			fileStructure = JSON.parse(data[0])
			alert(`Logged in. Welcome! (${emailInput.value})`);
			clearEmailPw();
		}
		else if (response_code == 'CRER') {
			showNotification("Storage updated", 'success');
		}
		else if (response_code == 'FILC') {
			let fileContent = atob(data[0]);
			monacoEditor.setValue(fileContent);
			enableEditor();
			fileContentChanged = false;
		}
		else if (response_code == 'SAVR') {
			showNotification("File was saved successfully!", 'success');
			enableSaveButton();
		}
		else if (response_code == 'DELR') {
			showNotification("File was deleted successfully!", 'success');
		}
		else if (response_code == 'OUTP') {
			// Decode (bsae64) output
			let outputLine = atob(data[0]);
			updateOutput(outputLine);
		}
		else if (response_code == 'DONE') {
			let returnCode = parseInt(data[0]);
			showExecutionStatus(returnCode);
			enableRunButton();
			enableSaveButton();
		}
		else if (response_code == 'ERRR') {
			clearEmailPw();
			errorCode = data[0];
			displayError(errorCode);
		}
    });
	
	let errors = {
		"001": "General Error (001), Try to refresh ",
		"101": "Login Failed (101)",
		"102": "User already exists (102)",
		"201": "File not found (201)",
		"202": "Execution timeout (202)",
		"301": "Failed to create file or folder (301)",
		"302": "Failed to delete file (302)"
	};
	
	function displayError(errorCode) {
		
		if (errorCode != '301') {
			alert(`Error: ${errors[errorCode]}`);
		}
		else {
			showNotification(errors[errorCode], 'error');
		}
	}

    // Function to send code to the server
    function sendCodeToServer() {
		const code = monacoEditor.getValue();
        if (code.trim() === '') {
            alert('Please write some code before running.');
            return;
        }
		
		// Clear output window content
		clearOutput();
		
        // Check if user is logged in and has a current file open
        if (currentFile && document.getElementById('user-email-display')) {
            // First save the current file
            saveCurrentFile();
            
            // Then send the RUNF command with the file path
            const toSend = `RUNF~${currentFile.path}`;
            console.log(`Running file: ${currentFile.path}`);
            socket.send(toSend);
        } else {
            // User not logged in or no file is open, use the original EXEC command
			// Code is encoded (base64)
			let encodedScript = btoa(code);
            const toSend = `EXEC~${encodedScript}`;
            socket.send(toSend);
        }
    }

    // Run button click event
    runBtn.addEventListener('click', () => {
		sendCodeToServer();
		disableRunButton();
		disableSaveButton();
	});
	
	// Function to disable Run button and show a loading throbber
	function disableRunButton() {
		const runBtn = document.getElementById('run-btn');
		if (runBtn) {
			// Save original text to restore later
			runBtn.dataset.originalHtml = runBtn.innerHTML;
			
			// Replace with throbber
			runBtn.innerHTML = '<div class="button-throbber"></div> Running...';
			runBtn.disabled = true;
			runBtn.classList.add('disabled');
		}
	}
	
	// Function to restore Run button to normal state
	function enableRunButton() {
		const runBtn = document.getElementById('run-btn');
		if (runBtn) {
			// Restore original content
			if (runBtn.dataset.originalHtml) {
				runBtn.innerHTML = runBtn.dataset.originalHtml;
			} else {
				runBtn.innerHTML = '<i class="fas fa-play"></i> Run';
			}
			
			runBtn.disabled = false;
			runBtn.classList.remove('disabled');
		}
	}
	
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
					#input-area {
						background-color: transparent;
						color: #66FF66; /* Light green for input */
						caret-color: #66FF66;
					}
					@keyframes blink {
						0% { opacity: 1; }
						50% { opacity: 0; }
						100% { opacity: 1; }
					}
					#input-cursor {
						animation: blink 1s step-end infinite;
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
	
	const returnCodeMessages = {
		0: "Code Execution Successful",
		1: "Code Exited With Errors",
		2: "Code Execution Environment Failed (Server Error)",
		3: "Reached execution timeout"
	}
	
	// Show execution finish status
	function showExecutionStatus(returnCode) {
		let message;
		if (returnCode in returnCodeMessages) {
			message = `\n=== ${returnCodeMessages[returnCode]} ===`;
		} else {
			message = "\n=== Unknown error or signal ===";
		}
		
		updateOutput(message);
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
	
	// Function to handle input in the output window
	function handleInputRequest(prompt) {
		return new Promise((resolve) => {
			if (!output.contentDocument) {
				console.error("Output iframe document not available");
				resolve("");
				return;
			}
			
			const outputDoc = output.contentDocument;
			const preElement = outputDoc.getElementById("pre-text");
			
			if (!preElement) {
				console.error("Pre-text element not found in output");
				resolve("");
				return;
			}
			
			// Display the prompt if provided
			if (prompt) {
				preElement.textContent += prompt;
			}
			
			// Create and append the input element
			const inputSpan = outputDoc.createElement("span");
			inputSpan.id = "input-area";
			inputSpan.contentEditable = true;
			inputSpan.style.outline = "none";
			inputSpan.style.display = "inline-block";
			inputSpan.style.minWidth = "1px";
			inputSpan.style.position = "relative";
			
			// Add cursor animation style
			if (!outputDoc.getElementById("cursor-style")) {
				const style = outputDoc.createElement("style");
				style.id = "cursor-style";
				style.textContent = `
					@keyframes blink {
						0% { opacity: 1; }
						50% { opacity: 0; }
						100% { opacity: 1; }
					}
					#input-area {
						caret-color: #66FF66; /* Green cursor */
					}
					/* Make the entire output area clickable to focus input */
					body {
						cursor: text;
					}
					#pre-text {
						min-height: 100vh;
					}
				`;
				outputDoc.head.appendChild(style);
			}
			
			// Append input area to the pre element
			preElement.appendChild(inputSpan);
			
			// Focus the input area
			inputSpan.focus();
			
			// Create a container for the input state
			const inputState = {
				active: true,
				value: ""
			};
			
			// Make the entire output area clickable to focus input
			function focusInput(e) {
				if (inputState.active && e.target !== inputSpan) {
					e.preventDefault();
					inputSpan.focus();
				}
			}
			
			// Add click event to the entire document body
			outputDoc.body.addEventListener("click", focusInput);
			
			// Handle key events
			function handleKeyDown(e) {
				if (!inputState.active) return;
				
				if (e.key === "Enter") {
					e.preventDefault();
					
					// Capture the entered value
					const userInput = inputSpan.textContent || "";
					inputState.value = userInput;
					inputState.active = false;
					
					// Replace input span with the entered text
					const textNode = outputDoc.createTextNode(userInput);
					preElement.replaceChild(textNode, inputSpan);
					
					// Add new line
					preElement.appendChild(outputDoc.createTextNode("\n"));
					
					// Remove event listeners
					outputDoc.removeEventListener("keydown", handleKeyDown);
					outputDoc.body.removeEventListener("click", focusInput);
					
					// Resolve the promise with the input value
					resolve(userInput);
				}
			}
			
			// Add keydown event listener
			outputDoc.addEventListener("keydown", handleKeyDown);
		});
	}

	// Function to intercept Python input() calls and handle them
	function setupInputInterception(socket) {
		// Add a message handler for input requests
		socket.addEventListener('message', async (event) => {
			const msg = event.data;
			console.log(`Received: ${msg}`);
			
			const fields = msg.split('~');
			const response_code = fields[0];
			const data = fields.slice(1);
			
			// Check if this is an input request
			if (response_code === 'INPT') {
				// Get the prompt (if any)
				const promptData = data[0] ? JSON.parse(data[0]) : {};
				const prompt = promptData.prompt || "";
				
				try {
					// Handle the input request
					const userInput = await handleInputRequest(prompt);
					
					// Send the input back to the server (Base64-encoded)
					const inputResponse = `INPR~${btoa(userInput)}`;
					socket.send(inputResponse);
					console.log(`Sent: ${inputResponse}`);
				} catch (error) {
					console.error("Error handling input:", error);
					// Send empty response in case of error
					socket.send('INPR');
				}
			}
		});
	}

	// Initialize input handling system
	function initializeInputHandling(socket) {
		setupInputInterception(socket);
		console.log("Input handling system initialized");
	}
	
    // Font size controls
    let fontSize = 18;
    const minFontSize = 12;
    const maxFontSize = 24;

    increaseFontBtn.addEventListener('click', () => {
        if (fontSize < maxFontSize) {
            fontSize += 2;
			monacoEditor.updateOptions({ fontSize: fontSize });
        }
    });

    decreaseFontBtn.addEventListener('click', () => {
        if (fontSize > minFontSize) {
            fontSize -= 2;
			monacoEditor.updateOptions({ fontSize: fontSize });
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
	
	// Clear email & password input fields
	function clearEmailPw() {
		emailInput.value = '';
		passwordInput.value = '';
	}
	
	// Function to replace login button with user email display
	function displayUserEmail(email) {
		const authBtn = document.getElementById('auth-btn');
		
		// Create user email display element
		const userEmailDisplay = document.createElement('div');
		userEmailDisplay.id = 'user-email-display';
		userEmailDisplay.className = 'user-email-display';
		userEmailDisplay.innerHTML = `<i class="fas fa-user"></i> ${email}`;

		// Create or find the auth container
		let authContainer = document.getElementById('auth-container');
		if (!authContainer) {
			authContainer = document.createElement('div');
			authContainer.id = 'auth-container';
			authContainer.className = 'auth-container';

			// Insert the container in the header
			const header = document.querySelector('header');
			if (header) {
				// If auth button exists, replace it with the container
				if (authBtn && authBtn.parentNode) {
					authBtn.parentNode.replaceChild(authContainer, authBtn);
				} else {
					// Otherwise insert after title container
					const titleContainer = document.querySelector('.title-container');
					if (titleContainer) {
						header.insertBefore(authContainer, titleContainer.nextSibling);
					} else {
						header.appendChild(authContainer);
					}
				}
			}
		}

		// Add the user email display to the container
		authContainer.appendChild(userEmailDisplay);

		console.log(`Displaying user email: ${email}`);
	}

    // Auth modal functionality
    authBtn.addEventListener('click', () => {
        authModal.classList.remove('hidden');
    });

    authModal.addEventListener('click', (e) => {
        if (e.target === authModal) {
            authModal.classList.add('hidden');
        }
    });

    // Event listener for the Register button
    authForm.addEventListener('submit', (e) => {
		e.preventDefault(); // Prevent form submission
		
		const email = emailInput.value;
		
		const password = passwordInput.value;
		
		// Validate inputs
		if (!email || !password) {
			alert('Please enter both email and password');
			return;
		}
		
		// Determine if this is a Login or Register action
		const isRegister = e.submitter?.classList.contains('register-btn');
		
		if (isRegister) {
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
		} else {
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
        
        // Select the root folder by default
        setTimeout(() => {
            const rootFolderHeader = document.querySelector('.root-folder > .folder-header');
            if (rootFolderHeader) {
                rootFolderHeader.classList.add('selected');
                lastSelectedFolder = rootFolderHeader.parentNode;
            }
        }, 100); // Small delay to ensure DOM is updated
	});

	// Close sidebar function
	function closeSidebar() {
		console.log("closing sidebar")
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
                
                // Also set this as the last selected folder
                lastSelectedFolder = this.parentNode;
                
                // Visual indication that this folder is selected
                document.querySelectorAll('.folder-header.selected').forEach(el => {
                    el.classList.remove('selected');
                });
                this.classList.add('selected');
                
                console.log('Selected folder:', this.querySelector('.folder-name').textContent);
            });
        });
    }
		
	// Function to save the current expanded state of folders
	function saveExpandedFolderState() {
		const expandedFolders = [];
		document.querySelectorAll('.folder-header:not(.collapsed)').forEach(header => {
			const path = buildPathFromFolderHeader(header);
			expandedFolders.push(path.join('/'));
		});
		return expandedFolders;
	}

	// Function to build path from a folder header element
	function buildPathFromFolderHeader(header) {
		const path = [];
		
		// Get folder name
		const folderName = header.querySelector('.folder-name').textContent;
		if (folderName !== 'your_files') {
			path.push(folderName);
		}
		
		// Get parent folders
		let current = header.parentNode;
		while (current) {
			if (current.classList && current.classList.contains('folder-item')) {
				const parentHeader = current.parentNode.parentNode.querySelector(':scope > .folder-header');
				if (parentHeader) {
					const parentName = parentHeader.querySelector('.folder-name');
					if (parentName && parentName.textContent !== 'your_files') {
						path.unshift(parentName.textContent);
					}
				}
			}
			
			// Move up to parent folder
			if (current.parentNode && 
				current.parentNode.classList && 
				current.parentNode.classList.contains('folder-contents')) {
				current = current.parentNode.parentNode;
			} else {
				break;
			}
		}
		
		return path;
	}

	// Function to restore expanded state after rebuilding the tree
	function restoreExpandedFolderState(expandedFolders) {
		expandedFolders.forEach(folderPath => {
			if (!folderPath) return; // Skip empty paths
			
			const pathParts = folderPath.split('/');
			let currentElement = document.querySelector('.root-folder');
			
			// Traverse the path to find the folder
			for (const part of pathParts) {
				if (!currentElement) break;
				
				// Find child folder with matching name
				const folderHeader = Array.from(
					currentElement.querySelectorAll(':scope > .folder-contents > .folder-item > .folder-header')
				).find(header => 
					header.querySelector('.folder-name').textContent === part
				);
				
				if (folderHeader) {
					// Expand this folder
					folderHeader.classList.remove('collapsed');
					const folderContents = folderHeader.parentNode.querySelector('.folder-contents');
					if (folderContents) {
						folderContents.classList.remove('hidden');
					}
					
					// Update folder icon
					const folderIcon = folderHeader.querySelector('.fa-folder, .fa-folder-open');
					if (folderIcon) {
						folderIcon.className = 'fas fa-folder-open';
					}
					
					// Update chevron direction
					const chevron = folderHeader.querySelector('.folder-toggle');
					if (chevron) {
						chevron.style.transform = 'rotate(0deg)';
					}
					
					// Move to next level
					currentElement = folderHeader.parentNode;
				} else {
					break;
				}
			}
		});
	}
	
    // Function to create a dynamic file tree from the fileStructure array
    function populateFileTree() {
		// Save current expanded state before rebuilding
		const expandedFolders = saveExpandedFolderState();
		
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
		
		// Setup folder selection for newly created elements
		setupFolderSelection();
		
		// Restore expanded state
		restoreExpandedFolderState(expandedFolders);
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
    
	// Function to create a file item with click handler
	function createFileItem(file) {
		const fileItem = document.createElement('div');
		fileItem.className = 'file-item';
		
		const fileIcon = document.createElement('i');
		// Make sure the file extension is correctly extracted and passed to getFileIcon
		const extension = file.extension || (file.name.includes('.') ? file.name.split('.').pop() : '');
		fileIcon.className = getFileIcon(extension);
		
		const fileName = document.createElement('span');
		fileName.className = 'file-name';
		fileName.textContent = file.name;
		
		fileItem.appendChild(fileIcon);
		fileItem.appendChild(fileName);
		
		// Add click event to load file content
		fileItem.addEventListener('click', function() {
			// Check if there are unsaved changes in the current file
			if (fileContentChanged) {
				saveCurrentFile();
			}
			
			// Get file path
			const filePath = [...buildPathFromDom(this), file.name].join('/');
			loadFileContent(file.name, filePath);
			
			// Visual indication that this file is selected
			document.querySelectorAll('.file-item.selected').forEach(el => {
				el.classList.remove('selected');
			});
			this.classList.add('selected');
			
			// Store current file info
			currentFile = {
				name: file.name,
				path: filePath
			};
			
			// Show save button
			showSaveButton();
			
			console.log('Selected file:', file.name, 'at path:', filePath);
		});
		
		return fileItem;
	}
	
	// Function to check if a name already exists in the current directory
	function nameExistsInCurrentDirectory(name) {
		// Get the directory where we're trying to create the new item
		let targetDirectory = fileStructure;
		
		// If we have a selected folder, find it in the file structure
		if (lastSelectedFolder && currentPath.length > 0) {
			// Navigate through the path to find the current directory
			for (const segment of currentPath) {
				// Find the folder with this name
				const found = targetDirectory.find(item => 
					item.type === 'folder' && item.name === segment
				);
				
				if (found && found.children) {
					targetDirectory = found.children;
				} else {
					// Path not found, use root directory
					targetDirectory = fileStructure;
					break;
				}
			}
		}
		
		// Check if the name already exists in the target directory
		return targetDirectory.some(item => item.name === name);
	}
	
	// Helper function to find an item in the file structure by path
	function findItemByPath(path) {
		if (!path || path.length === 0) {
			return fileStructure;
		}
		
		let current = fileStructure;
		
		for (let i = 0; i < path.length; i++) {
			const segment = path[i];
			const found = current.find(item => 
				item.type === 'folder' && item.name === segment
			);
			
			if (found && found.children) {
				current = found.children;
			} else {
				return null; // Path not found
			}
		}
		
		return current;
	}
	
	// Function to load file content into editor
	function loadFileContent(fileName, filePath) {
		// Request file content from server
		const contentRequest = `GETF~${filePath}`;
		
		if (socket && socket.readyState === WebSocket.OPEN) {
			socket.send(contentRequest);
			console.log(`Requested content for file: ${filePath}`);
			
			// Show loading indicator in editor			
			monacoEditor.setValue(`# Loading ${fileName}...`);
			
			disableEditor();
			
			// Update file display with the current file name
			updateCurrentFileDisplay(fileName, filePath);
			
			// Close "Files" sidebar
			closeSidebar();
			
		} else {
			console.error('WebSocket not connected');
			alert('Unable to load file: Server connection not available');
		}
	}
	
	// Function to show and update the current file display
	function updateCurrentFileDisplay(fileName, filePath) {
		const currentFileDisplay = document.getElementById('current-file-display');
		const currentFileName = document.getElementById('current-file-name');
		
		if (filePath) {
			currentFileName.textContent = filePath.replace(/\//g, "\\");  // Replace '/' with '\'
			currentFileDisplay.classList.remove('hidden');
			
			// Update the icon based on file extension
			const fileIcon = currentFileDisplay.querySelector('i');
			if (fileIcon) {
				const extension = fileName.includes('.') ? fileName.split('.').pop() : '';
				fileIcon.className = getFileIcon(extension);
			}
		} else {
			currentFileDisplay.classList.add('hidden');
		}
	}

	// Function to create and show save button
	function showSaveButton() {
		// Remove existing save button if it exists
		const existingSaveBtn = document.getElementById('save-btn');
		if (existingSaveBtn) {
			existingSaveBtn.remove();
		}

		// Create save button
		const saveBtn = document.createElement('button');
		saveBtn.id = 'save-btn';
		saveBtn.className = 'save-button';
		saveBtn.innerHTML = '<i class="fas fa-cloud-upload-alt"></i> Save';
		
		saveBtn.addEventListener('click', () => {
			saveCurrentFile();
			disableSaveButton();
		});

		// Find or create auth container
		let authContainer = document.getElementById('auth-container');
		if (!authContainer) {
			authContainer = document.createElement('div');
			authContainer.id = 'auth-container';
			authContainer.className = 'auth-container';

			// Insert container in header
			const header = document.querySelector('header');
			if (header) {
				const titleContainer = document.querySelector('.title-container');
				if (titleContainer) {
					header.insertBefore(authContainer, titleContainer.nextSibling);
				} else {
					header.appendChild(authContainer);
				}
			}
		}

		// Add save button to container
		authContainer.appendChild(saveBtn);
	}

	// Function to save current file content
	function saveCurrentFile() {
		if (!currentFile) return;
		
		const fileContent = monacoEditor.getValue();
		const saveRequest = `SAVF~${JSON.stringify({
			path: currentFile.path,
			content: fileContent
		})}`;
		
		if (socket && socket.readyState === WebSocket.OPEN) {
			socket.send(saveRequest);
			console.log(`Saved file: ${currentFile.path}`);
			fileContentChanged = false;
		} else {
			console.error('WebSocket not connected');
			alert('Unable to save file: Server connection not available');
		}
	}
	
	// Function to disable Save button
	function disableSaveButton() {
		const saveBtn = document.getElementById('save-btn');
		if (saveBtn) {
			// Save original text to restore later
			saveBtn.dataset.originalHtml = saveBtn.innerHTML;
			
			// Replace with throbber
			saveBtn.innerHTML = '<div class="button-throbber"></div> Saving...';
			saveBtn.disabled = true;
			saveBtn.classList.add('disabled');
		}
	}

	// Function to enable Save button
	function enableSaveButton() {
		// Delay for animation
		setTimeout(() => {
			const saveBtn = document.getElementById('save-btn');
			if (saveBtn) {
				// Restore original content
				if (saveBtn.dataset.originalHtml) {
					saveBtn.innerHTML = saveBtn.dataset.originalHtml;
				} else {
					saveBtn.innerHTML = '<i class="fas fa-cloud-upload-alt"></i> Save';
				}
				
				saveBtn.disabled = false;
				saveBtn.classList.remove('disabled');
			}
		}, 300);
		
	}
	
	// Create the notification container if it doesn't exist
	function createNotificationContainer() {
		// Check if the container already exists
		if (document.getElementById('notification-container')) {
			return;
		}
		
		// Create notification container
		const notificationContainer = document.createElement('div');
		notificationContainer.id = 'notification-container';
		notificationContainer.className = 'notification-container';
		document.body.appendChild(notificationContainer);
	}
	
	// Function to show notification
	function showNotification(message, type = 'success') {
		// Create container if it doesn't exist
		createNotificationContainer();
		
		// Create notification element
		const notification = document.createElement('div');
		notification.className = `notification ${type}`;
		
		// Create icon based on notification type
		const icon = document.createElement('i');
		if (type === 'success') {
			icon.className = 'fas fa-check-circle';
		} else if (type === 'error') {
			icon.className = 'fas fa-exclamation-circle';
		} else if (type === 'info') {
			icon.className = 'fas fa-info-circle';
		}
		
		// Create message text
		const text = document.createElement('span');
		text.textContent = message;
		
		// Add elements to notification
		notification.appendChild(icon);
		notification.appendChild(text);
		
		// Add to container
		const container = document.getElementById('notification-container');
		container.appendChild(notification);
		
		// Trigger animation
		setTimeout(() => {
			notification.classList.add('show');
		}, 100);
		
		// Remove after delay
		setTimeout(() => {
			notification.classList.remove('show');
			setTimeout(() => {
				if (notification.parentNode === container) {
					container.removeChild(notification);
				}
			}, 300); // Wait for fade out animation
		}, 3000);
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
	
	// Variables to track current path and selection
	let currentPath = [];
	
	// Track the last selected/clicked folder
	let lastSelectedFolder = null;
    
    // Initialize create mode and create type variables
    let createMode = ""; // 'file' or 'folder'
	
	// Variables to track current state
	let currentFile = null;
	let fileContentChanged = false;
    
    // New File Button Click Event
    if (newFileBtn) {
        newFileBtn.addEventListener('click', function() {
            openCreateModal('file');
        });
    }
    
    // New Folder Button Click Event
    if (newFolderBtn) {
        newFolderBtn.addEventListener('click', function() {
            openCreateModal('folder');
        });
    }
	
	// Function to setup folder selection with path tracking
	function setupFolderSelection() {
    // Get all folder headers
		const folderHeaders = document.querySelectorAll('.folder-header');
		
		folderHeaders.forEach(header => {
			header.addEventListener('click', function(e) {
				// Set this as the last selected folder
				lastSelectedFolder = this.parentNode;
				
				// Get the folder path using the DOM structure
				currentPath = buildPathFromDom(this.parentNode);
				
				// Visual indication that this folder is selected
				document.querySelectorAll('.folder-header.selected').forEach(el => {
					el.classList.remove('selected');
				});
				this.classList.add('selected');
				
				const folderName = this.querySelector('.folder-name').textContent;
				console.log('Selected folder:', folderName);
				console.log('Current path:', currentPath.join('/'));
			});
		});
	}

	// Function to update the current path based on selected folder
	function updatePathFromSelection(selectedHeader) {
		// Reset path
		currentPath = [];
		
		// Start from the selected element and work our way up through the DOM
		let current = selectedHeader;
		const pathElements = [];
		
		// First collect all folder elements in the path
		while (current && current.parentNode) {
			// If this is a folder header, add it to our path elements
			if (current.classList && current.classList.contains('folder-header')) {
				const nameElement = current.querySelector('.folder-name');
				if (nameElement) {
					pathElements.unshift({
						element: current,
						name: nameElement.textContent
					});
				}
			}
			
			// Move to parent element
			if (current.parentNode.classList && current.parentNode.classList.contains('folder-item')) {
				current = current.parentNode;
			} else {
				current = current.parentNode;
			}
			
			// Stop when we reach the file-tree
			if (current.classList && (current.classList.contains('file-tree') || current === document.body)) {
				break;
			}
		}
		
		// Now build the path from the collected elements
		for (const item of pathElements) {
			if (item.name !== 'your_files') { // Skip the root folder name
				currentPath.push(item.name);
			}
		}
		
		console.log("Path elements found:", pathElements.length);
		console.log("Built path:", currentPath);
	}
    
    // Function to open the create modal
    function openCreateModal(type) {
        createMode = type;
        
        if (type === 'file') {
            createModalIcon.className = 'fas fa-file-plus';
            createModalText.textContent = 'New File';
        } else {
            createModalIcon.className = 'fas fa-folder-plus';
            createModalText.textContent = 'New Folder';
        }
        
        // Clear previous input
        createNameInput.value = '';
        
        // Show the modal
        createModal.classList.remove('hidden');
        
        // Focus the input field
        createNameInput.focus();
    }
    
    // Cancel create button
    if (cancelCreateBtn) {
        cancelCreateBtn.addEventListener('click', function() {
            createModal.classList.add('hidden');
        });
    }
    
    // Also close modal when clicking outside
    if (createModal) {
        createModal.addEventListener('click', function(e) {
            if (e.target === createModal) {
                createModal.classList.add('hidden');
            }
        });
    }
    
    // Handle Enter key in the name input
    if (createNameInput) {
        createNameInput.addEventListener('keydown', function(e) {
            if (e.key === 'Enter') {
                confirmCreate();
            }
        });
    }
    
    // Confirm create button
    if (confirmCreateBtn) {
        confirmCreateBtn.addEventListener('click', confirmCreate);
    }
    
    // Function to handle creation confirmation
    function confirmCreate() {
		const name = createNameInput.value.trim();
		
		if (!name) {
			alert('Please enter a name.');
			return;
		}
		
		if (createMode === 'file' && !name.includes('.') || name.lastIndexOf('.') == name.length - 1) {
			alert('File name must contain extension.');
			return;
		}
		
		// Check if the name already exists in the current directory
		if (nameExistsInCurrentDirectory(name)) {
			alert(`A file or folder with the name "${name}" already exists in this directory.`);
			return;
		}
		
		if (createMode === 'file') {
			createNewFile(name);
		} else {
			createNewFolder(name);
		}
		
		// Hide the modal
		createModal.classList.add('hidden');
		
		// Refresh the file tree while maintaining expanded state
		populateFileTree();
	}
    
    // Function to create a new file in the selected folder
	function createNewFile(name) {

		extension = name.split('.').pop();
		
		const newFile = {
			type: 'file',
			name: name,
			extension: extension
		};
		
		// Generate the full path for the new file
		const filePath = [...currentPath, name].join('/');
		
		// Add file to the appropriate location in the file structure
		addToFileStructure(newFile);
		
		console.log(`New file created: ${name} at path: ${filePath}`);
		
		// Send the file creation info to the server
		sendFileCreationToServer('file', name, filePath);
	}
    
    // Function to create a new folder in the selected folder
	function createNewFolder(name) {
		const newFolder = {
			type: 'folder',
			name: name,
			children: []
		};
		
		// Generate the full path for the new folder
		const folderPath = [...currentPath, name].join('/');
		
		// Add folder to the appropriate location in the file structure
		addToFileStructure(newFolder);
		
		console.log(`New folder created: ${name} at path: ${folderPath}`);
		
		// Send the folder creation info to the server
		sendFileCreationToServer('folder', name, folderPath);
	}
    
    // Function to add a new item to the file structure based on the last selected folder
    function addToFileStructure(newItem) {
        // If no folder was selected, add to root
        if (!lastSelectedFolder) {
            fileStructure.push(newItem);
            return;
        }
        
        // Get the folder name from the last selected folder
        const folderName = lastSelectedFolder.querySelector('.folder-name').textContent;
        
        // Find the folder in the structure and add the new item to its children
        // This is a recursive function to search the entire structure
        function findAndAddToFolder(items) {
            for (let i = 0; i < items.length; i++) {
                const item = items[i];
                
                if (item.type === 'folder' && item.name === folderName) {
                    // Found the target folder, add the new item to its children
                    if (!item.children) {
                        item.children = [];
                    }
                    item.children.push(newItem);
                    return true;
                }
                
                // If this is a folder, search its children
                if (item.type === 'folder' && item.children) {
                    if (findAndAddToFolder(item.children)) {
                        return true;
                    }
                }
            }
            return false;
        }
        
        // Start the search from the root
        if (!findAndAddToFolder(fileStructure)) {
            // If folder not found, add to root as fallback
            fileStructure.push(newItem);
        }
    }
	
	// Function to send file/folder creation info to the server
	function sendFileCreationToServer(type, name, path) {
		// Format the message for the server
		const creationMessage = `CREA~${JSON.stringify({
			type: type,
			name: name,
			path: path
		})}`;
		
		// Send to server through the WebSocket
		if (socket && socket.readyState === WebSocket.OPEN) {
			socket.send(creationMessage);
			console.log(`Creation data sent to server: ${type} - ${path}`);
		} else {
			console.error('WebSocket not connected');
			alert(`Unable to create ${type}: Server connection not available`);
		}
	}
	
	// Function to recursively build path from DOM structure
	function buildPathFromDom(element) {
		const path = [];
		
		// Start from the element and traverse up through all parent folder items
		let current = element;
		
		while (current) {
			// If this is a folder item
			if (current.classList && current.classList.contains('folder-item')) {
				const folderHeader = current.querySelector(':scope > .folder-header');
				if (folderHeader) {
					const nameElement = folderHeader.querySelector('.folder-name');
					if (nameElement && nameElement.textContent !== 'your_files') {
						path.unshift(nameElement.textContent);
					}
				}
			}
			
			// Check if parent is a folder-contents which is inside another folder-item
			const parentFolderContents = current.parentElement;
			if (parentFolderContents && parentFolderContents.classList.contains('folder-contents')) {
				current = parentFolderContents.parentElement; // This should be the parent folder-item
			} else {
				break; // Exit if we're not in a nested structure
			}
		}
		
		return path;
	}
	
	// When opening a folder for the first time, initialize the path
	document.querySelector('.root-folder > .folder-header').addEventListener('click', function(e) {
		// Reset path since we're clicking the root
		currentPath = [];
		console.log('Root folder selected, path reset to: []');
	});
	
	// Function to show context menu
    function showContextMenu(event, fileElement) {
        event.preventDefault(); // Prevent default browser context menu
        contextMenu.classList.remove('hidden');
        contextMenu.style.top = `${event.clientY}px`;
        contextMenu.style.left = `${event.clientX}px`;
        currentContextMenuFile = fileElement; // Store the target file
    }

    // Function to hide context menu
    function hideContextMenu() {
        contextMenu.classList.add('hidden');
        currentContextMenuFile = null;
    }

    // Add event listener to hide context menu when clicking elsewhere
    document.addEventListener('click', function (event) {
        if (!contextMenu.contains(event.target)) {
            hideContextMenu();
        }
    });

    // Modify createFileItem function to add context menu listener
    function createFileItem(file) {
        const fileItem = document.createElement('div');
        fileItem.className = 'file-item';

        const fileIcon = document.createElement('i');
        const extension = file.extension || (file.name.includes('.') ? file.name.split('.').pop() : '');
        fileIcon.className = getFileIcon(extension);

        const fileName = document.createElement('span');
        fileName.className = 'file-name';
        fileName.textContent = file.name;

        fileItem.appendChild(fileIcon);
        fileItem.appendChild(fileName);

        // Add context menu event listener
        fileItem.addEventListener('contextmenu', function (event) {
            showContextMenu(event, fileItem);
        });

        // Add click event to load file content (existing logic)
        fileItem.addEventListener('click', function() {
            // Check if there are unsaved changes in the current file
            if (fileContentChanged) {
                saveCurrentFile();
            }

            // Get file path
            const filePath = [...buildPathFromDom(this), file.name].join('/');
            loadFileContent(file.name, filePath);

            // Visual indication that this file is selected
            document.querySelectorAll('.file-item.selected').forEach(el => {
                el.classList.remove('selected');
            });
            this.classList.add('selected');

            // Store current file info
            currentFile = {
                name: file.name,
                path: filePath
            };

            // Show save button
            showSaveButton();

            console.log('Selected file:', file.name, 'at path:', filePath);
            hideContextMenu(); // Hide context menu if it was open
        });

        return fileItem;
    }

    // Context menu action functions
    function deleteFileAction() {
		if (!currentContextMenuFile) {
			hideContextMenu();
			return;
		}
		
		const fileNameElement = currentContextMenuFile.querySelector('.file-name');
		if (!fileNameElement) {
			hideContextMenu();
			return;
		}
		
		const fileName = fileNameElement.textContent;
		
		// Confirm deletion with user
		if (!confirm(`Are you sure you want to delete "${fileName}"?`)) {
			hideContextMenu();
			return;
		}
		
		// Get file path by traversing the DOM
		const filePath = [...buildPathFromDom(currentContextMenuFile), fileName].join('/');
		
		// Send delete request to server
		const deleteMessage = `DELF~${filePath}`;
		
		if (socket && socket.readyState === WebSocket.OPEN) {
			socket.send(deleteMessage);
			console.log(`Delete request sent for file: ${filePath}`);
			
			// If this was the current file being edited, clear the editor
			if (currentFile && currentFile.path === filePath) {
				// Clear editor content
				monacoEditor.setValue('');
				
				// Hide current file display
				const currentFileDisplay = document.getElementById('current-file-display');
				if (currentFileDisplay) {
					currentFileDisplay.classList.add('hidden');
				}
				
				// Remove save button
				const saveBtn = document.getElementById('save-btn');
				if (saveBtn) {
					saveBtn.remove();
				}
				
				// Reset current file
				currentFile = null;
				fileContentChanged = false;
			}
			
			// Remove the file from the file structure
			removeFileFromStructure(filePath);
			
			// Refresh the file tree
			populateFileTree();
		} else {
			console.error('WebSocket not connected');
			showNotification('Unable to delete file: Server connection not available', 'error');
		}
		
		hideContextMenu();
	}

	// Function to remove file from file structure
	function removeFileFromStructure(filePath) {
		const pathParts = filePath.split('/');
		const fileName = pathParts.pop(); // Get the file name (last part)
		
		// Find the parent directory
		let current = fileStructure;
		let parent = null;
		
		// Navigate to the parent directory
		for (const part of pathParts) {
			parent = current;
			const found = current.find(item => item.type === 'folder' && item.name === part);
			if (found && found.children) {
				current = found.children;
			} else {
				return false; // Path not found
			}
		}
		
		// Remove the file from the parent directory
		const fileIndex = current.findIndex(item => item.name === fileName);
		if (fileIndex !== -1) {
			current.splice(fileIndex, 1);
			return true;
		}
		
		return false;
	}

    function renameFileAction() {
        if (currentContextMenuFile) {
            const fileNameElement = currentContextMenuFile.querySelector('.file-name');
            const fileName = fileNameElement ? fileNameElement.textContent : 'unknown file';
            console.log(`Rename file: ${fileName}`);
            // TODO: Implement rename file logic
            alert(`Rename file: ${fileName} (functionality not yet implemented)`);
        }
        hideContextMenu();
    }

    function downloadFileAction() {
        if (currentContextMenuFile) {
            const fileNameElement = currentContextMenuFile.querySelector('.file-name');
            const fileName = fileNameElement ? fileNameElement.textContent : 'unknown file';
            console.log(`Download file: ${fileName}`);
            // TODO: Implement download file logic
            alert(`Download file: ${fileName} (functionality not yet implemented)`);
        }
        hideContextMenu();
    }

    // Add event listeners for context menu buttons
    if (deleteFileBtn) {
        deleteFileBtn.addEventListener('click', deleteFileAction);
    }
    if (renameFileBtn) {
        renameFileBtn.addEventListener('click', renameFileAction);
    }
    if (downloadFileBtn) {
        downloadFileBtn.addEventListener('click', downloadFileAction);
    }
	
	// Sample file structure (this would come from the server)
	// const fileStructure = [
		// {
			// type: 'folder',
			// name: 'Project 1',
			// children: [
				// { type: 'file', name: 'index.html', extension: 'html' },
				// { type: 'file', name: 'styles.css', extension: 'css' },
				// { type: 'file', name: 'script.js', extension: 'js' }
			// ]
		// },
		// {
			// type: 'folder',
			// name: 'Project 2',
			// children: [
				// { type: 'file', name: 'main.py', extension: 'py' },
				// { 
					// type: 'folder', 
					// name: 'data',
					// children: [
						// { type: 'file', name: 'data.csv', extension: 'csv' },
						// { type: 'file', name: 'config.json', extension: 'json' }
					// ]
				// }
			// ]
		// },
		// { type: 'file', name: 'notes.txt', extension: 'txt' }
	// ];
});