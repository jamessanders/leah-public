const App = () => {
    // Load initial state from localStorage or use defaults
    const [inputValue, setInputValue] = React.useState('');
    const [responses, setResponses] = React.useState(() => {
        const saved = localStorage.getItem('responses');
        return saved ? JSON.parse(saved) : [];
    });
    const [loading, setLoading] = React.useState(false);
    const [personas, setPersonas] = React.useState([]);
    const [selectedPersona, setSelectedPersona] = React.useState(() => {
        return localStorage.getItem('selectedPersona') || 'leah';
    });
    const [conversationId, setConversationId] = React.useState(() => {
        return localStorage.getItem('conversationId') || '';
    });
    const inputRef = React.useRef(null);
    const responseAreaRef = React.useRef(null);
    const audioRef = React.useRef(null);
    const [conversationHistory, setConversationHistory] = React.useState(() => {
        const saved = localStorage.getItem('conversationHistory');
        return saved ? JSON.parse(saved) : [];
    });
    const [audioQueue, setAudioQueue] = React.useState([]);
    const [queue, setQueue] = React.useState([]);
    const [isPlaying, setIsPlaying] = React.useState(false);
    const [isMobile, setIsMobile] = React.useState(false);
    const [isModalOpen, setIsModalOpen] = React.useState(false);
    const [modalInputValue, setModalInputValue] = React.useState('');
    const [submissionQueue, setSubmissionQueue] = React.useState([]);
    
    // Authentication state
    const [isAuthenticated, setIsAuthenticated] = React.useState(false);
    const [username, setUsername] = React.useState(() => {
        return localStorage.getItem('username') || '';
    });
    const [token, setToken] = React.useState(() => {
        return localStorage.getItem('token') || '';
    });
    const [isMuted, setIsMuted] = React.useState(() => {
        return localStorage.getItem('isMuted') === 'true';
    });
    const [loginError, setLoginError] = React.useState('');
    const [loginLoading, setLoginLoading] = React.useState(false);
    const [loginForm, setLoginForm] = React.useState({
        username: '',
        password: ''
    });

    const userAvatarUrl = 'https://via.placeholder.com/40?text=U'; // Placeholder for user avatar
    const assistantAvatarUrl = `/avatars/avatar-${selectedPersona}.png`;

    // Check authentication status on component mount
    React.useEffect(() => {
        const storedUsername = localStorage.getItem('username');
        const storedToken = localStorage.getItem('token');
        
        if (storedUsername && storedToken) {
            setIsAuthenticated(true);
            setUsername(storedUsername);
            setToken(storedToken);
        }
    }, []);

    // Save state to localStorage whenever it changes
    React.useEffect(() => {
        localStorage.setItem('responses', JSON.stringify(responses));
    }, [responses]);

    React.useEffect(() => {
        localStorage.setItem('conversationHistory', JSON.stringify(conversationHistory));
    }, [conversationHistory]);

    React.useEffect(() => {
        localStorage.setItem('selectedPersona', selectedPersona);
    }, [selectedPersona]);

    // Save authentication data to localStorage
    React.useEffect(() => {
        if (username && token) {
            localStorage.setItem('username', username);
            localStorage.setItem('token', token);
        }
    }, [username, token]);

    // Save mute state to localStorage whenever it changes
    React.useEffect(() => {
        localStorage.setItem('isMuted', isMuted);
    }, [isMuted]);

    // Save conversation ID to localStorage whenever it changes
    React.useEffect(() => {
        if (conversationId) {
            localStorage.setItem('conversationId', conversationId);
        }
    }, [conversationId]);

    // Handle login form input changes
    const handleLoginInputChange = (e) => {
        const { name, value } = e.target;
        setLoginForm(prev => ({
            ...prev,
            [name]: value
        }));
    };

    // Handle login form submission
    const handleLogin = async (e) => {
        e.preventDefault();
        setLoginLoading(true);
        setLoginError('');
        
        try {
            const response = await fetch('/login', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    username: loginForm.username,
                    password: loginForm.password
                }),
            });
            
            const data = await response.json();
            
            if (response.ok && data.token) {
                setUsername(loginForm.username);
                setToken(data.token);
                setIsAuthenticated(true);
                setLoginForm({ username: '', password: '' });
            } else {
                setLoginError(data.message || 'Login failed. Please check your credentials.');
            }
        } catch (error) {
            console.error('Login error:', error);
            setLoginError('An error occurred during login. Please try again.');
        } finally {
            setLoginLoading(false);
        }
    };

    // Handle logout
    const handleLogout = () => {
        localStorage.removeItem('username');
        localStorage.removeItem('token');
        localStorage.removeItem('conversationHistory');
        localStorage.removeItem('responses');
        localStorage.removeItem('conversationId');
        setIsAuthenticated(false);
        setUsername('');
        setToken('');
        setConversationHistory([]);
        setResponses([]);
        setConversationId('');
    };

    // Fetch available personas on component mount
    React.useEffect(() => {
        const fetchPersonas = async () => {
            if (!isAuthenticated) {
                return;
            }
            try {
                const response = await fetch('/personas', {
                    headers: {
                        'Authorization': `Bearer ${token}`,
                        'X-Username': username
                    }
                });
                const data = await response.json();
                if (!data) {
                    setPersonas(["beth"]);
                } else {
                    if (selectedPersona && !data.includes(selectedPersona)) {
                        setSelectedPersona(data[0]);
                    }
                    setPersonas(data);
                }
            } catch (error) {
                console.error('Error fetching personas:', error);
            }
        };
        fetchPersonas();
    }, [isAuthenticated, token, username]);

    const handlePersonaChange = (event) => {
        setSelectedPersona(event.target.value);
    };

    const handleInputChange = (event) => {
        setInputValue(event.target.value);
    };

    const handleKeyPress = (event) => {
        if (event.key === 'Enter') {
            handleSubmit(event.target.value);
        }
    };

    const handleBlur = () => {
        // On mobile, when keyboard is dismissed (blur event), submit if there's text
        if (isMobile && inputValue.trim() !== '') {
            handleSubmit();
        }
    };

    const processNextSubmission = React.useCallback(() => {
        console.log("Attempting to process next submission");
        console.log("Current queue:", submissionQueue);
        if (submissionQueue.length > 0) {
            const nextSubmission = submissionQueue[0];
            console.log("Processing submission:", nextSubmission);
            setSubmissionQueue(submissionQueue.slice(1));
            handleSubmit(nextSubmission);
        } else {
            console.log("No submissions to process");
        }
    }, [submissionQueue]);

    const handleSubmit = async (input = inputValue) => {
        if (loading) {
            setSubmissionQueue(prevQueue => [...prevQueue, input]);
            console.log("Currently loading, queuing submission:", input);
            setInputValue(''); // Clear the input field immediately when queuing
            console.log("Updated submission queue (after queuing):", submissionQueue);
            return;
        }

        console.log("Submitting input:", input);
        try {
            setLoading(true); // Show loading message
            const updatedHistory = [...conversationHistory];
            setConversationHistory(updatedHistory);
            setResponses([...responses, { role: 'user', content: input }]);
            setConversationHistory([...responses, { role: 'user', content: input }]);
            setInputValue(''); // Clear the input field before submitting
            setModalInputValue('');

            const res = await fetch('/query', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${token}`,
                    'X-Username': username
                },
                body: JSON.stringify({ 
                    query: input, 
                    conversation_id: conversationId,
                    persona: selectedPersona,
                    context: modalInputValue
                }),
            });

            const status = res.status;
            if (status === 401) {
                setIsAuthenticated(false);
                setUsername('');
                setToken('');
                setConversationHistory([]);
                setResponses([]);
                return;
            }
            const reader = res.body.getReader();
            const decoder = new TextDecoder('utf-8');

            let assistantResponse = '';

            while (true) {
                const { done, value } = await reader.read();
                if (done) break;
                const chunk = decoder.decode(value, { stream: true });

                // Split the chunk into individual JSON objects
                const jsonObjects = chunk.split('\n\n').filter(Boolean);
                for (const jsonObject of jsonObjects) {
                    try {
                        // Strip the 'data:' prefix and parse the JSON response
                        const jsonResponse = JSON.parse(jsonObject.replace(/^data:\s*/, ''));
                        console.log("JSON response:", jsonResponse);
                        if (jsonResponse.type === 'conversation_id') {
                            setConversationId(jsonResponse.id);
                        } else if (jsonResponse.type === 'system' && jsonResponse.content) {
                            console.log('System message:', jsonResponse.content);
                            setResponses(prevResponses => {
                                const lastResponse = prevResponses[prevResponses.length - 1];
                                if (lastResponse.role === 'assistant') {
                                    // Insert system message before the last assistant response
                                    return [...prevResponses.slice(0, -1), { role: 'system', content: `${jsonResponse.content}` }, lastResponse];
                                } else {
                                    // Add system message normally
                                    return [...prevResponses, { role: 'system', content: `${jsonResponse.content}` }];
                                }
                            });
                        } else if (jsonResponse.type === 'end') {
                            setLoading(false); // Hide loading message
                            console.log("Finished processing submission, checking queue");
                            console.log("DONE Submission queue:", submissionQueue);
                            processNextSubmission(); // Process the next submission in the queue
                        } else if (jsonResponse.content) {
                            // Append content as plain text
                            const plainTextContent = jsonResponse.content;
                            assistantResponse += plainTextContent;
                            setResponses(prevResponses => {
                                const lastResponse = prevResponses[prevResponses.length - 1];
                                if (lastResponse.role === 'assistant') {
                                    // Append to the last assistant response
                                    lastResponse.content += plainTextContent;
                                    return [...prevResponses.slice(0, -1), lastResponse];
                                } else {
                                    // Add a new assistant response
                                    return [...prevResponses, { role: 'assistant', content: plainTextContent }];
                                }
                            });
                        } else if (jsonResponse.filename && !isMuted) {
                            console.log("Adding voice to queue:", jsonResponse.filename);
                            addToAudioQueue("/voice/" + jsonResponse.filename); // Add to the audio queue only if not muted
                        } else if (jsonResponse.type === "history" && jsonResponse.history) {
                            // Update the conversation history with the server's version
                            console.log("Updating conversation history with server's version:", jsonResponse.history);
                            setConversationHistory(jsonResponse.history);
                        } 
                    } catch (error) {
                        console.error('Error parsing JSON:', error);
                    }
                }
            }

            // Store the complete assistant response in conversation history
            setConversationHistory(prevHistory => [...prevHistory, { role: 'assistant', content: assistantResponse }]);

            // Convert the complete response from markdown to HTML
            const htmlResponse = marked.parse(assistantResponse);

            // Overwrite the UI with the converted HTML content
            setResponses(prevResponses => {
                // Filter out system messages
                const filteredResponses = prevResponses.filter(response => !response.content.includes('<i>'));
                const lastResponse = filteredResponses[filteredResponses.length - 1];
                if (lastResponse && lastResponse.role === 'assistant') {
                    // Overwrite the last assistant response
                    lastResponse.content = htmlResponse;
                    return [...filteredResponses.slice(0, -1), lastResponse];
                } else {
                    // Add a new assistant response
                    return [...filteredResponses, { role: 'assistant', content: htmlResponse }];
                }
            });
        }    catch (error) {
            console.error('Error:', error);
        } 
    };

    const useAudioPlayer = () => {
        // We are managing promises of audio urls instead of directly storing strings
        // because there is no guarantee when openai tts api finishes processing and resolves a specific url
        // For more info, check this comment:
        // https://github.com/tarasglek/chatcraft.org/pull/357#discussion_r1473470003
        const [queue, setQueue] = React.useState([]);
        const [isPlaying, setIsPlaying] = React.useState(false);
        const audioContextRef = React.useRef(null);
        const sourceNodeRef = React.useRef(null);
      
        React.useEffect(() => {
          if (!isPlaying && queue.length > 0) {
            playAudio(queue[0]);
          }
        }, [queue, isPlaying]);
      
        const playAudio = async (audioClipUri) => {
          console.log('Attempting to play audio with Web Audio API:', audioClipUri);
          if (!audioClipUri) {
              console.error('No audio URI provided');
              return;
          }
          setIsPlaying(true);
          const audioUrl = await audioClipUri;
          
          // Create a new audio context if one doesn't exist
          if (!audioContextRef.current) {
            audioContextRef.current = new (window.AudioContext || window.webkitAudioContext)();
          }
          
          try {
              const response = await fetch(audioUrl);
              const arrayBuffer = await response.arrayBuffer();
              const audioBuffer = await audioContextRef.current.decodeAudioData(arrayBuffer);
              const source = audioContextRef.current.createBufferSource();
              source.buffer = audioBuffer;
              source.connect(audioContextRef.current.destination);
              source.onended = () => {
                  setQueue((oldQueue) => oldQueue.slice(1));
                  setIsPlaying(false);
                  sourceNodeRef.current = null;
              };
              source.start(0);
              sourceNodeRef.current = source;
          } catch (error) {
              console.error('Error with Web Audio API playback:', error);
              setQueue((oldQueue) => oldQueue.slice(1));
              setIsPlaying(false);
              sourceNodeRef.current = null;
          }
        };
      
        const addToAudioQueue = (audioClipUri) => {
          setQueue((oldQueue) => [...oldQueue, audioClipUri]);
        };
      
        const clearAudioQueue = () => {
          setQueue([]);
          
          // Stop currently playing audio if any
          if (sourceNodeRef.current) {
            try {
              sourceNodeRef.current.stop();
              sourceNodeRef.current = null;
            } catch (error) {
              console.error('Error stopping audio:', error);
            }
          }
          
          // Close the audio context
          if (audioContextRef.current) {
            audioContextRef.current.close();
            audioContextRef.current = null;
          }
          
          setIsPlaying(false);
        };
      
        return { addToAudioQueue, clearAudioQueue };
      };
      const { addToAudioQueue, clearAudioQueue } = useAudioPlayer();

    React.useEffect(() => {
        if (inputRef.current) {
            inputRef.current.focus();
        }
    }, []);

    React.useEffect(() => {
        if (responseAreaRef.current) {
            responseAreaRef.current.scrollTop = responseAreaRef.current.scrollHeight;
        }
    }, [responses]);

    // Detect if the device is mobile
    React.useEffect(() => {
        const checkIfMobile = () => {
            const isMobileDevice = /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent);
            setIsMobile(isMobileDevice);
        };
        
        checkIfMobile();
        window.addEventListener('resize', checkIfMobile);
        
        return () => {
            window.removeEventListener('resize', checkIfMobile);
        };
    }, []);

    const handleModalOpen = () => {
        setIsModalOpen(true);
    };

    const handleModalClose = () => {
        setIsModalOpen(false);
    };

    const handleModalInputChange = (event) => {
        setModalInputValue(event.target.value);
    };

    const handleMuteToggle = () => {
        setIsMuted(!isMuted);
        if (!isMuted) {
            clearAudioQueue();
        }
    };

    const [isDropdownOpen, setIsDropdownOpen] = React.useState(false);

    const panelRef = React.useRef(null);

    // Close the panel if clicked outside
    const handleClickOutside = (event) => {
        if (panelRef.current && !panelRef.current.contains(event.target)) {
                setIsDropdownOpen(false);
        }
    };

// Add event listener for clicks outside the panel
React.useEffect(() => {
    if (isDropdownOpen) {
        document.addEventListener('mousedown', handleClickOutside);
    } else {
        document.removeEventListener('mousedown', handleClickOutside);
    }

    return () => {
        document.removeEventListener('mousedown', handleClickOutside);
    };
}, [isDropdownOpen]);

    const toggleDropdown = () => {
        setIsDropdownOpen(prev => !prev);
    };

    // Add SVG Spinner component
    const LoadingSpinner = () => {
        return React.createElement('div', { 
            className: 'loading-spinner-container'
        },
            React.createElement('svg', {
                className: 'loading-spinner',
                viewBox: '0 0 50 50',
                width: '30',
                height: '30'
            },
                React.createElement('circle', {
                    className: 'loading-spinner-circle',
                    cx: '25',
                    cy: '25',
                    r: '20',
                    fill: 'none',
                    strokeWidth: '5'
                })
            )
        );
    };

    return React.createElement('div', null,
        // Show login panel if not authenticated
        !isAuthenticated ? (
            React.createElement('div', { 
                className: 'login-panel'
            },
                React.createElement('h2', null, 'Login'),
                React.createElement('form', { 
                    onSubmit: handleLogin,
                    className: 'login-form'
                },
                    React.createElement('div', { className: 'form-group' },
                        React.createElement('label', { htmlFor: 'username' }, 'Username'),
                        React.createElement('input', {
                            type: 'text',
                            id: 'username',
                            name: 'username',
                            value: loginForm.username,
                            onChange: handleLoginInputChange,
                            required: true
                        })
                    ),
                    React.createElement('div', { className: 'form-group' },
                        React.createElement('label', { htmlFor: 'password' }, 'Password'),
                        React.createElement('input', {
                            type: 'password',
                            id: 'password',
                            name: 'password',
                            value: loginForm.password,
                            onChange: handleLoginInputChange,
                            required: true
                        })
                    ),
                    loginError && React.createElement('div', { 
                        className: 'login-error'
                    }, loginError),
                    React.createElement('div', {
                        onClick: handleLogin,
                        className: 'login-button',
                        style: { 
                            opacity: loginLoading ? 0.7 : 1,
                            pointerEvents: loginLoading ? 'none' : 'auto'
                        }
                    }, loginLoading ? 'Logging in...' : 'Login')
                )
            )
        ) : (
            React.createElement(React.Fragment, null,
                React.createElement('div', { className: 'header' },
                    React.createElement('h1', null, ''),personas.length > 1 ? 
                    React.createElement('select', {
                        className: 'personaSelector',
                        value: selectedPersona,
                        onChange: handlePersonaChange
                    },
                        personas.map(persona =>
                            React.createElement('option', {
                                key: persona,
                                value: persona
                            }, persona.charAt(0).toUpperCase() + persona.slice(1))
                        ) 
                    ) : null,
                    React.createElement('div', {
                        onClick: toggleDropdown,
                        className: 'dropdown-button',
                    }, 'Menu'),
                    React.createElement('div', { className: isDropdownOpen ? 'dropdown-menu' : 'dropdown-menu hidden', ref: panelRef },
                        React.createElement('div', {
                            onClick: () => {
                                console.log("Resetting conversation history");
                                setConversationHistory([]);
                                setResponses([]);
                                setConversationId('');
                                localStorage.removeItem('conversationHistory');
                                localStorage.removeItem('responses');
                                localStorage.removeItem('conversationId');
                            },
                            className: 'dropdown-item'
                        }, 'Reset'),
                        React.createElement('div', { onClick: handleModalOpen, className: 'dropdown-item' }, 'Context'),
                        React.createElement('div', { 
                            onClick: handleMuteToggle, 
                            className: 'dropdown-item'
                        }, isMuted ? 'Unmute' : 'Mute'),
                        React.createElement('div', { 
                            onClick: handleLogout, 
                            className: 'dropdown-item'
                        }, 'Logout')
                    )
                ),
                React.createElement('div', { className: 'responseArea', ref: responseAreaRef },
                    responses.map((item, index) =>
                        React.createElement('div', {
                            key: index,
                            className: (item.role === 'user' ? 'userInputBox' : 'responseBox') + (item.role === 'system' ? ' systemMessage' : ''),
                            style: { display: 'flex', alignItems: 'flex-start' }
                        },
                        item.role !== 'system' && React.createElement('div', {
                            className: 'avatar'
                        },
                        item.role === 'assistant' && React.createElement('img', {
                            src: assistantAvatarUrl,
                            alt: 'Assistant Avatar'
                        })),
                        React.createElement('div', {
                            className: 'content',
                            dangerouslySetInnerHTML: { __html: item.content }
                        })
                        )
                    ),
                    loading && React.createElement(LoadingSpinner)
                ),
                React.createElement('input', {
                    type: 'text',
                    value: inputValue,
                    onChange: handleInputChange,
                    onKeyPress: handleKeyPress,
                    onBlur: handleBlur,
                    placeholder: 'Enter your query',
                    className: 'queryInput',
                    ref: inputRef
                }),
                isModalOpen && (
                    React.createElement('div', { className: 'modal' },
                        React.createElement('textarea', {
                            value: modalInputValue,
                            onChange: handleModalInputChange,
                            placeholder: 'Enter your context here...'
                        }),
                        React.createElement('div', { onClick: handleModalClose, className: 'close-modal', style: { cursor: 'pointer', padding: '10px 20px', backgroundColor: '#007bff', color: '#fff', borderRadius: '5px', display: 'inline-block', textAlign: 'center', marginTop: '10px' } }, 'Close')
                    )
                )
            )
        )
    );
};

ReactDOM.render(React.createElement(App), document.getElementById('root')); 