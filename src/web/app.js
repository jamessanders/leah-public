const App = () => {
    // Add timestamp formatting helper function at the top of the component
    const formatTimestamp = (epochTime) => {
        if (!epochTime) return '';
        const date = new Date(epochTime * 1000);
        const now = new Date();
        const isToday = date.toDateString() === now.toDateString();
        
        const timeStr = date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
        if (isToday) {
            return timeStr;
        }
        
        const dateStr = date.toLocaleDateString([], { month: 'short', day: 'numeric' });
        return `${dateStr} ${timeStr}`;
    };

    // Load initial state from localStorage or use defaults
    const [inputValue, setInputValue] = React.useState('');
    const [responses, setResponses] = React.useState(() => {
        const saved = localStorage.getItem('responses');
        return saved ? JSON.parse(saved) : [];
    });
    const [loading, setLoading] = React.useState(false);
    const [channels, setChannels] = React.useState([]);
    const [selectedChannel, setSelectedChannel] = React.useState(() => {
        return localStorage.getItem('selectedChannel') || '#general';
    });
    // Add a ref to track the current channel value
    const selectedChannelRef = React.useRef(localStorage.getItem('selectedChannel') || '#general');
    
    // Update the ref whenever selectedChannel changes
    React.useEffect(() => {
        selectedChannelRef.current = selectedChannel;
    }, [selectedChannel]);
    
    const [isSystemMessagesExpanded, setIsSystemMessagesExpanded] = React.useState(false);
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
    const [pendingRequests, setPendingRequests] = React.useState(0);
    // Add state to track subscription status
    const [isSubscriptionActive, setIsSubscriptionActive] = React.useState(false);
    // Add state to track unread messages by channel
    const [unreadMessages, setUnreadMessages] = React.useState({});
    const abortControllerRef = React.useRef(null);

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

    // Add theme state
    const [theme, setTheme] = React.useState(() => {
        return localStorage.getItem('theme') || 'dark';
    });
    const [isThemeAccordionOpen, setIsThemeAccordionOpen] = React.useState(false);

    const themes = [
        { id: 'dark', name: 'Dark Theme' },
        { id: 'light', name: 'Light Theme' },
        { id: 'graphite', name: 'Graphite Theme' },
        { id: 'vibe', name: 'Vibe Theme' },
        { id: 'forest', name: 'Forest Theme' },
        { id: 'ocean', name: 'Ocean Theme' },
        { id: 'sunset', name: 'Sunset Theme' },
        { id: 'zen', name: 'Zen Theme' }
    ];

    const userAvatarUrl = 'https://via.placeholder.com/40?text=U'; // Placeholder for user avatar
    const assistantAvatarUrl = `/avatars/avatar-${selectedChannel.substring(1)}.svg`;

    // Add new state for left panel
    const [isLeftPanelOpen, setIsLeftPanelOpen] = React.useState(true);

    // Add loading state
    const [isLoaded, setIsLoaded] = React.useState(false);

    // Add new state for tracking new system messages
    const [newSystemMessages, setNewSystemMessages] = React.useState({});

    // Add state for section expansion
    const [isChannelsSectionExpanded, setIsChannelsSectionExpanded] = React.useState(true);
    const [isPersonasSectionExpanded, setIsPersonasSectionExpanded] = React.useState(true);

    // Add state for context submission feedback
    const [contextSubmitStatus, setContextSubmitStatus] = React.useState('');
    const [contextLoading, setContextLoading] = React.useState(false);

    // Add function to separate channels and personas
    const separateChannelsAndPersonas = (items) => {
        return items.reduce((acc, item) => {
            if (item.startsWith('@')) {
                acc.personas.push(item);
            } else {
                acc.channels.push(item);
            }
            return acc;
        }, { channels: [], personas: [] });
    };

    // Update useEffect to handle loading state
    React.useEffect(() => {
        const storedUsername = localStorage.getItem('username');
        const storedToken = localStorage.getItem('token');
        const storedChannel = localStorage.getItem('selectedChannel');

        if (storedUsername && storedToken) {
            setIsAuthenticated(true);
            setUsername(storedUsername);
            setToken(storedToken);
        }
        
        // Mark as loaded after initial auth check
        document.getElementById('root').classList.add('loaded');
        setIsLoaded(true);
    }, []);

    // Save state to localStorage whenever it changes
    React.useEffect(() => {
        localStorage.setItem('responses', JSON.stringify(responses));
    }, [responses]);

    React.useEffect(() => {
        localStorage.setItem('conversationHistory', JSON.stringify(conversationHistory));
    }, [conversationHistory]);

    React.useEffect(() => {
        localStorage.setItem('selectedChannel', selectedChannel);
    }, [selectedChannel]);

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

    // Add new effect to fetch conversation history on mount
    React.useEffect(() => {
        const fetchConversationHistory = async () => {
            if (!isAuthenticated || !selectedChannel) {
                return;
            }

            try {
                const response = await fetch('/conversation_history', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'Authorization': `Bearer ${token}`,
                        'X-Username': username
                    },
                    body: JSON.stringify({
                        channel: selectedChannel
                    })
                });

                if (response.ok) {
                    const data = await response.json();
                    if (data.history && Array.isArray(data.history)) {
                        // No need to map the history since it's already in the correct format
                        setResponses(data.history);
                        setConversationHistory(data.history);
                    }
                } else if (response.status === 401) {
                    // Handle unauthorized access
                    setIsAuthenticated(false);
                    setUsername('');
                    setToken('');
                    setConversationHistory([]);
                    setResponses([]);
                }
            } catch (error) {
                console.error('Error fetching conversation history:', error);
            }
        };

        fetchConversationHistory();
    }, [isAuthenticated, selectedChannel, token, username]);

    // Add effect to handle new system messages
    React.useEffect(() => {
        if (!responses.length) return;
        const lastMessage = responses[responses.length - 1];
        if (lastMessage.type === 'system') {
            setNewSystemMessages(prev => ({
                ...prev,
                [lastMessage.id]: true
            }));
        } else {
            // Clear all pips when a non-system message arrives
            setNewSystemMessages({});
        }
    }, [responses]);

    const handleSubmit = React.useCallback(async (input = inputValue) => {
        console.log("Submitting input:", input);
        try {
            setPendingRequests(prev => prev + 1); // Increment counter on submission
            const updatedHistory = [...conversationHistory];
            setConversationHistory(updatedHistory);
            // Only add user input to responses if it's not empty
            const display_input = input.trim() ? input : "...";
            const userMessage = {
                content: display_input,
                from_user: username,
                id: `temp-${Date.now()}`,
                sent_at: Math.floor(Date.now() / 1000),
                type: 'user'
            };
            setResponses([...responses, userMessage]);
            setConversationHistory([...responses, userMessage]);

            setInputValue(''); // Clear the input field before submitting
            setModalInputValue('');

            console.log("Channel:", selectedChannel);
            const res = await fetch('/publish', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${token}`,
                    'X-Username': username
                },
                body: JSON.stringify({
                    query: input,
                    channel: selectedChannel,
                    context: modalInputValue
                }),
            });

            // Handle the response from /publish
            const data = await res.json();

        } catch (error) {
            console.error('Error:', error);
            setPendingRequests(prev => Math.max(0, prev - 1)); // Decrement on error
            setLoading(false);
        }
    }, [inputValue]);

    // Add periodic subscription polling
    React.useEffect(() => {
        let assistantResponse = '';
        let pollingInterval;

        const startSubscription = async () => {
            console.log("Starting subscription");
            try {
                // Only start a new subscription if we don't have an active one
                if (abortControllerRef.current) {
                    console.log("Subscription already active, not restarting");
                    return;
                }
                
                abortControllerRef.current = new AbortController();

                const res = await fetch('/subscribe', {
                    method: 'GET',
                    headers: {
                        'Content-Type': 'application/json',
                        'Authorization': `Bearer ${token}`,
                        'X-Username': username
                    },
                    signal: abortControllerRef.current.signal
                });

                if (res.status === 401) {
                    setIsAuthenticated(false);
                    setUsername('');
                    setToken('');
                    setConversationHistory([]);
                    setResponses([]);
                    setIsSubscriptionActive(false);
                    return;
                }

                // Mark subscription as active
                setIsSubscriptionActive(true);

                const reader = res.body.getReader();
                const decoder = new TextDecoder('utf-8');

                while (true) {
                    const { done, value } = await reader.read();
                    if (done) {
                        setIsSubscriptionActive(false);
                        startSubscription();
                        break;
                    }
                    const chunk = decoder.decode(value, { stream: true });

                    // Split the chunk into individual JSON objects
                    const jsonObjects = chunk.split('\n\n').filter(Boolean);
                   
                    for (const jsonObject of jsonObjects) {
                        try {
                            // Get the current selected channel from the ref
                            const currentChannel = selectedChannelRef.current;
                            console.log("Subscribed to channel:", currentChannel);
                            // Strip the 'data:' prefix and parse the JSON response
                            const jsonResponse = JSON.parse(jsonObject.replace(/^data:\s*/, ''));
                            console.log("JSON response:", jsonResponse);
                            let to_channel = jsonResponse.via_channel;
                            if (jsonResponse.type == "direct") {
                                to_channel = jsonResponse.from_user;
                            }
                            if (to_channel !== currentChannel && jsonResponse.type != "system") {
                                console.log("Skipping message from channel:", jsonResponse.via_channel);
                                console.log("Selected channel:", currentChannel);
                                
                                // Add to unread messages count for non-selected channels
                                setUnreadMessages(prev => ({
                                    ...prev,
                                    [to_channel]: (prev[to_channel] || 0) + 1
                                }));
                                
                                continue;
                            }
                            if (jsonResponse.content) {
                                // For streaming assistant responses, accumulate the content
                                if (jsonResponse.type === 'assistant') {
                                    setResponses(prevResponses => [...prevResponses, jsonResponse]);
                                } else {
                                    // For all other message types, store as is
                                    setResponses(prevResponses => [...prevResponses, jsonResponse]);
                                }
                            } else if (jsonResponse.filename && !isMuted) {
                                console.log("Adding voice to queue:", jsonResponse.filename);
                                addToAudioQueue("/voice/" + jsonResponse.filename);
                            }
                        } catch (error) {
                            console.error('Error parsing JSON:', error);
                        }
                    }
                }
            } catch (error) {
                console.log("Subscription error:", error);
            } finally {
                setIsSubscriptionActive(false);
                abortControllerRef.current = null;
                if (error.name === 'AbortError') {
                    console.log('Subscription aborted');
                    abortControllerRef.current = null;
                    startSubscription();
                } else {
                    console.error('Subscription error:', error);
                    await new Promise(resolve => setTimeout(resolve, 500));
                    startSubscription();
                }
            }
        };

        startSubscription();

        // Setup polling to check subscription status every 500ms
        pollingInterval = setInterval(() => {
            if (!isSubscriptionActive && isAuthenticated) {
                if (!abortControllerRef.current) {
                    startSubscription();
                } 
            }
        }, 1000);

        // Setup user interaction handler to restart subscription if needed
        const handleUserInteraction = () => {
            if (!isSubscriptionActive && isAuthenticated) {
                if (!abortControllerRef.current) {
                    startSubscription();
                } else {
                    console.log("Abort controller still exists, not restarting yet");
                }
            }
        };

        // Add event listeners for user interactions
        window.addEventListener('click', handleUserInteraction);
        window.addEventListener('keydown', handleUserInteraction);
        window.addEventListener('touchstart', handleUserInteraction);

        return () => {
            if (abortControllerRef.current) {
                abortControllerRef.current.abort();
            }
            // Clear polling interval
            clearInterval(pollingInterval);
            // Cleanup event listeners
            window.removeEventListener('click', handleUserInteraction);
            window.removeEventListener('keydown', handleUserInteraction);
            window.removeEventListener('touchstart', handleUserInteraction);
        };
    }, [token, username, isAuthenticated, isMuted]);

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
        localStorage.removeItem('selectedChannel');
        setIsAuthenticated(false);
        setUsername('');
        setToken('');
        setConversationHistory([]);
        setResponses([]);
        setSelectedChannel('#general');
    };

    // Fetch available channels on component mount
    const fetchChannels = React.useCallback(async () => {
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
                setChannels(['#general']);
            } else {
                const { personas = [], channels: regularChannels = [] } = data;
                // Convert personas to channels with @ prefix
                const personaChannels = personas.map(p => `@${p}`);
                const allChannels = [...personaChannels, ...regularChannels];
                
                if (selectedChannel && !allChannels.includes(selectedChannel)) {
                    setSelectedChannel(allChannels[0]);
                }
                setChannels(allChannels);
            }
        } catch (error) {
            console.error('Error fetching channels:', error);
        }
    }, [isAuthenticated, token, username, selectedChannel]);

    // Initial fetch on mount
    React.useEffect(() => {
        fetchChannels();
    }, [fetchChannels]);

    // Periodic fetch every 10 seconds
    React.useEffect(() => {
        if (!isAuthenticated) return;

        const intervalId = setInterval(() => {
            fetchChannels();
        }, 10000);

        // Cleanup interval on unmount
        return () => clearInterval(intervalId);
    }, [fetchChannels, isAuthenticated]);

    // Add new function to fetch conversation history for a specific channel
    const fetchConversationHistoryForChannel = async (channel) => {
        try {
            const response = await fetch('/conversation_history', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${token}`,
                    'X-Username': username
                },
                body: JSON.stringify({
                    channel: channel
                })  
            });

            if (response.ok) {
                const data = await response.json();
                if (data.history && Array.isArray(data.history)) {
                    // No need to map the history since it's already in the correct format
                    setResponses(data.history);
                    setConversationHistory(data.history);
                    localStorage.setItem('responses', JSON.stringify(data.history));
                    localStorage.setItem('conversationHistory', JSON.stringify(data.history));
                }
            } else if (response.status === 401) {
                // Handle unauthorized access
                setIsAuthenticated(false);
                setUsername('');
                setToken('');
                setConversationHistory([]);
                setResponses([]);
            } else {
                // If there's no history or other error, clear the history
                setConversationHistory([]);
                setResponses([]);
                localStorage.removeItem('conversationHistory');
                localStorage.removeItem('responses');
            }
        } catch (error) {
            console.error('Error fetching conversation history:', error);
            // On error, clear the history
            setConversationHistory([]);
            setResponses([]);
            localStorage.removeItem('conversationHistory');
            localStorage.removeItem('responses');
        }
    };

    // Handle channel change (keep for compatibility with any other uses)
    const handleChannelChange = async (event) => {
        const newChannel = event.target.value;
        setSelectedChannel(newChannel);
        selectedChannelRef.current = newChannel;
        localStorage.setItem('selectedChannel', newChannel);
        await fetchConversationHistoryForChannel(newChannel);
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

    // Scroll to bottom on initial mount
    React.useEffect(() => {
        if (responseAreaRef.current) {
            responseAreaRef.current.scrollTop = responseAreaRef.current.scrollHeight;
        }
    }, []); // Empty dependency array means this runs once on mount

    // Detect if the device is mobile
    React.useEffect(() => {
        const checkIfMobile = () => {
            const isMobileDevice = /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent);
            const isSmallScreen = window.innerWidth <= 768; // Consider screens <= 768px as small
            setIsMobile(isMobileDevice);
            setIsLeftPanelOpen(!isSmallScreen); // Close panel by default on small screens
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
    const leftPanelRef = React.useRef(null);

    // Close the panel if clicked outside
    const handleClickOutside = (event) => {
        if (panelRef.current && !panelRef.current.contains(event.target)) {
            setIsDropdownOpen(false);
        }
        // Close left panel on mobile when clicking outside
        if (isMobile && isLeftPanelOpen && leftPanelRef.current && 
            !leftPanelRef.current.contains(event.target) &&
            !event.target.closest('.panel-toggle-button')) {
            setIsLeftPanelOpen(false);
        }
    };

    // Add event listener for clicks outside the panel
    React.useEffect(() => {
        if (isDropdownOpen || (isMobile && isLeftPanelOpen)) {
            document.addEventListener('mousedown', handleClickOutside);
        } else {
            document.removeEventListener('mousedown', handleClickOutside);
        }

        return () => {
            document.removeEventListener('mousedown', handleClickOutside);
        };
    }, [isDropdownOpen, isMobile, isLeftPanelOpen]);

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

    // Save theme to localStorage whenever it changes
    React.useEffect(() => {
        localStorage.setItem('theme', theme);
        document.body.className = theme === 'dark' ? '' : `${theme}-theme`;
    }, [theme]);

    const handleThemeChange = (newTheme) => {
        setTheme(newTheme);
        // Don't close the accordion to allow for easy theme comparison
    };

    const toggleThemeAccordion = () => {
        setIsThemeAccordionOpen(!isThemeAccordionOpen);
    };

    // Add the avatar URL generation
    const getAvatarUrl = (messageType, fromUser) => {
        return `/avatars/avatar-${fromUser?.replace(/^@/, '')}.svg`;
    };

    // Add handler to clear new message indicator
    const handleSystemMessagesClick = (group) => {
        setIsSystemMessagesExpanded(prev => !prev);
        setNewSystemMessages(prev => {
            const newState = { ...prev };
            // Clear new message indicators for this group
            group.systemMessages.forEach(msg => {
                delete newState[msg.id];
            });
            return newState;
        });
    };

    // Add handler for submitting context to /channel_context
    const handleContextSubmit = async () => {
        setContextLoading(true);
        setContextSubmitStatus('');
        try {
            const response = await fetch('/channel_context', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${token}`,
                    'X-Username': username
                },
                body: JSON.stringify({
                    channel: selectedChannel,
                    text: modalInputValue
                })
            });
            const data = await response.json();
            if (response.ok) {
                setContextSubmitStatus('Context added!');
                setModalInputValue('');
            } else {
                setContextSubmitStatus(data.error || 'Failed to add context.');
            }
        } catch (error) {
            setContextSubmitStatus('Error submitting context.');
        } finally {
            setContextLoading(false);
        }
    };

    return React.createElement('div', null,
        // Only show login panel if not authenticated AND loaded
        (!isAuthenticated && isLoaded) ? (
            React.createElement('div', {
                className: 'login-panel visible'
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
            React.createElement('div', { className: 'app-container' },
                // Notification bubbles container
                React.createElement('div', { className: 'notifications-container' },
                    Object.entries(unreadMessages).map(([channel, count]) => 
                        React.createElement('div', {
                            key: channel,
                            className: 'notification-bubble',
                            onClick: () => {
                                setSelectedChannel(channel);
                                selectedChannelRef.current = channel;
                                localStorage.setItem('selectedChannel', channel);
                                fetchConversationHistoryForChannel(channel);
                                // Clear unread count for this channel
                                setUnreadMessages(prev => {
                                    const newState = { ...prev };
                                    delete newState[channel];
                                    return newState;
                                });
                            }
                        }, 
                            `${channel.replace(/^[@#]/, '')}: ${count}`
                        )
                    )
                ),
                React.createElement('div', { className: 'content-area' },
                    React.createElement('div', {
                        className: `left-panel ${!isLeftPanelOpen ? 'collapsed' : ''} ${isMobile && isLeftPanelOpen ? 'open' : ''}`,
                        ref: leftPanelRef
                    },
                        !isMobile && React.createElement('div', { className: 'left-panel-header' },
                            React.createElement('button', {
                                className: 'toggle-panel-button',
                                onClick: () => setIsLeftPanelOpen(!isLeftPanelOpen)
                            }, isLeftPanelOpen ? '←' : '→')
                        ),
                        React.createElement('div', { className: 'sections-container' },
                            // Channels Section
                            React.createElement('div', { className: 'panel-section' },
                                React.createElement('div', {
                                    className: 'section-header',
                                    onClick: () => setIsChannelsSectionExpanded(!isChannelsSectionExpanded)
                                },
                                    React.createElement('span', null, 'Channels'),
                                    React.createElement('span', {
                                        className: `expand-icon ${isChannelsSectionExpanded ? 'expanded' : ''}`
                                    })
                                ),
                                isChannelsSectionExpanded && React.createElement('div', { className: 'section-content' },
                                    separateChannelsAndPersonas(channels).channels.map(channel =>
                                        React.createElement('div', {
                                            key: channel,
                                            className: `persona-item ${selectedChannel === channel ? 'selected' : ''}`,
                                            onClick: () => {
                                                setSelectedChannel(channel);
                                                selectedChannelRef.current = channel;
                                                localStorage.setItem('selectedChannel', channel);
                                                fetchConversationHistoryForChannel(channel);
                                                // Clear unread count for this channel
                                                setUnreadMessages(prev => {
                                                    const newState = { ...prev };
                                                    delete newState[channel];
                                                    return newState;
                                                });
                                            }
                                        },
                                            React.createElement('div', {
                                                className: 'channel-icon'
                                            }, '#'),
                                            React.createElement('span', null,
                                                channel.charAt(0).toUpperCase() + channel.slice(1)
                                            )
                                        )
                                    )
                                )
                            ),
                            // Personas Section
                            React.createElement('div', { className: 'panel-section' },
                                React.createElement('div', {
                                    className: 'section-header',
                                    onClick: () => setIsPersonasSectionExpanded(!isPersonasSectionExpanded)
                                },
                                    React.createElement('span', null, 'Personas'),
                                    React.createElement('span', {
                                        className: `expand-icon ${isPersonasSectionExpanded ? 'expanded' : ''}`
                                    })
                                ),
                                isPersonasSectionExpanded && React.createElement('div', { className: 'section-content' },
                                    separateChannelsAndPersonas(channels).personas.map(persona =>
                                        React.createElement('div', {
                                            key: persona,
                                            className: `persona-item ${selectedChannel === persona ? 'selected' : ''}`,
                                            onClick: () => {
                                                setSelectedChannel(persona);
                                                selectedChannelRef.current = persona;
                                                localStorage.setItem('selectedChannel', persona);
                                                fetchConversationHistoryForChannel(persona);
                                                // Clear unread count for this persona
                                                setUnreadMessages(prev => {
                                                    const newState = { ...prev };
                                                    delete newState[persona];
                                                    return newState;
                                                });
                                            }
                                        },
                                            React.createElement('img', {
                                                src: `/avatars/avatar-${persona.substring(1)}.svg`,
                                                alt: persona,
                                                className: 'persona-avatar'
                                            }),
                                            React.createElement('span', null,
                                                persona.substring(1).charAt(0).toUpperCase() + persona.substring(2)
                                            )
                                        )
                                    )
                                )
                            )
                        )
                    ),
                    React.createElement('div', { className: 'main-content' },
                        React.createElement('div', { className: 'header' },
                            React.createElement('div', { className: 'header-left' },
                                React.createElement('button', {
                                    className: 'panel-toggle-button',
                                    onClick: () => setIsLeftPanelOpen(!isLeftPanelOpen),
                                    style: { display: isMobile ? 'flex' : 'none' }
                                }, isLeftPanelOpen ? '←' : '→'),
                                React.createElement('button', {
                                    onClick: handleModalOpen,
                                    title: 'Add Channel Context',
                                    className: 'context-add-button',
                                },
                                    React.createElement('svg', {
                                        width: 22,
                                        height: 22,
                                        viewBox: '0 0 24 24',
                                        fill: 'none',
                                        stroke: 'currentColor',
                                        strokeWidth: 2,
                                        strokeLinecap: 'round',
                                        strokeLinejoin: 'round',
                                        style: { display: 'block' }
                                    },
                                        React.createElement('line', { x1: 12, y1: 5, x2: 12, y2: 19 }),
                                        React.createElement('line', { x1: 5, y1: 12, x2: 19, y2: 12 })
                                    )
                                )
                            ),
                            React.createElement('div', { className: 'header-right' },
                                React.createElement('div', {
                                    onClick: toggleDropdown,
                                    className: 'dropdown-button',
                                },
                                    React.createElement('svg', {
                                        className: 'hamburger-icon',
                                        viewBox: '0 0 24 24'
                                    },
                                        React.createElement('line', {
                                            x1: '3',
                                            y1: '6',
                                            x2: '21',
                                            y2: '6'
                                        }),
                                        React.createElement('line', {
                                            x1: '3',
                                            y1: '12',
                                            x2: '21',
                                            y2: '12'
                                        }),
                                        React.createElement('line', {
                                            x1: '3',
                                            y1: '18',
                                            x2: '21',
                                            y2: '18'
                                        })
                                    )
                                ),
                                React.createElement('div', {
                                    className: isDropdownOpen ? 'dropdown-menu' : 'dropdown-menu hidden',
                                    ref: panelRef
                                },
                                    React.createElement('div', {
                                        onClick: async () => {
                                            console.log("Resetting conversation history");
                                            // Call the reset endpoint
                                            try {
                                                const response = await fetch('/reset', {
                                                    method: 'POST',
                                                    headers: {
                                                        'Content-Type': 'application/json',
                                                        'Authorization': `Bearer ${token}`,
                                                        'X-Username': username
                                                    },
                                                    body: JSON.stringify({
                                                        channel: selectedChannel
                                                    })
                                                });
                                                if (!response.ok) {
                                                    console.error('Failed to reset conversation on server');
                                                }
                                            } catch (error) {
                                                console.error('Error resetting conversation:', error);
                                            }
                                            // Clear local state
                                            setConversationHistory([]);
                                            setResponses([]);
                                            localStorage.removeItem('conversationHistory');
                                            localStorage.removeItem('responses');
                                        },
                                        className: 'dropdown-item'
                                    }, 'Reset'),
                                    React.createElement('div', { onClick: handleModalOpen, className: 'dropdown-item' }, 'Context'),
                                    React.createElement('div', {
                                        onClick: handleMuteToggle,
                                        className: 'dropdown-item'
                                    }, isMuted ? 'Unmute' : 'Mute'),
                                    React.createElement('div', {
                                        onClick: toggleThemeAccordion,
                                        className: 'dropdown-item'
                                    }, 'Change Theme'),
                                    React.createElement('div', {
                                        className: `theme-accordion ${isThemeAccordionOpen ? 'open' : ''}`
                                    }, themes.map(themeOption => 
                                        React.createElement('div', {
                                            key: themeOption.id,
                                            onClick: () => handleThemeChange(themeOption.id),
                                            className: `theme-option ${theme === themeOption.id ? 'active' : ''}`
                                        }, themeOption.name)
                                    )),
                                    React.createElement('div', {
                                        onClick: handleLogout,
                                        className: 'dropdown-item'
                                    }, 'Logout')
                                )
                            )
                        ),
                        React.createElement('div', { className: 'chat-container' },
                            React.createElement('div', { className: 'responseArea', ref: responseAreaRef },
                                (() => {
                                    // Group messages into conversation blocks
                                    const messageGroups = responses.reduce((groups, message) => {
                                        if (message.type === 'system') {
                                            // Add system message to the last group's system messages
                                            if (groups.length > 0) {
                                                const lastGroup = groups[groups.length - 1];
                                                lastGroup.systemMessages.push(message);
                                            } else {
                                                // If no groups exist yet, create one for orphaned system messages
                                                groups.push({
                                                    message: null,
                                                    systemMessages: [message]
                                                });
                                            }
                                        } else {
                                            // Create a new group for non-system message
                                            groups.push({
                                                message: message,
                                                systemMessages: []
                                            });
                                        }
                                        return groups;
                                    }, []);

                                    return messageGroups.map((group, groupIndex) => 
                                        React.createElement('div', {
                                            key: `group-${groupIndex}`,
                                            className: 'message-group'
                                        },
                                            // Render the main message if it exists
                                            group.message && React.createElement('div', {
                                                key: `message-${group.message.id || groupIndex}`,
                                                id: group.message.id,
                                                className: `message ${group.message.type}Message ` + (group.message.from_user == "@"+username ? 'userMessage' : ''),
                                                style: { display: 'flex', alignItems: 'flex-start' }
                                            },
                                                React.createElement('div', {
                                                    className: 'avatar'
                                                },
                                                    React.createElement('img', {
                                                        src: getAvatarUrl(group.message.type, group.message.from_user || selectedChannel),
                                                        alt: `${group.message.type === 'assistant' ? 'Assistant' : 'User'} Avatar`
                                                    })),
                                                React.createElement('div', {
                                                    className: 'message-container'
                                                },
                                                    React.createElement('div', {
                                                        className: 'message-header'
                                                    },
                                                        React.createElement('span', {
                                                            className: 'message-sender'
                                                        }, group.message.from_user ? group.message.from_user.replace(/^@/, '') : (group.message.type === 'assistant' ? selectedChannel.replace(/^@/, '') : username)),
                                                        React.createElement('span', {
                                                            className: 'message-time'
                                                        }, formatTimestamp(group.message.sent_at))
                                                    ),
                                                    React.createElement('div', {
                                                        className: 'message-content',
                                                        dangerouslySetInnerHTML: { __html: marked.parse(group.message.content) }
                                                    })
                                                )
                                            ),
                                            // Render system messages if there are any
                                            group.systemMessages.length > 0 && React.createElement('div', {
                                                className: 'system-messages-group'
                                            },
                                                React.createElement('div', {
                                                    className: 'system-messages-header',
                                                    onClick: () => handleSystemMessagesClick(group)
                                                },
                                                    React.createElement('div', {
                                                        className: 'system-messages-header-content'
                                                    },
                                                        // Show pips for each new message
                                                        React.createElement('div', {
                                                            className: 'system-messages-pips'
                                                        },
                                                            group.systemMessages.map(msg => 
                                                                newSystemMessages[msg.id] && React.createElement('span', {
                                                                    key: msg.id + Math.random(),
                                                                    className: 'system-messages-pip'
                                                                })
                                                            )
                                                        ),
                                                        React.createElement('span', null, '')
                                                    ),
                                                    React.createElement('span', {
                                                        className: `expand-icon ${isSystemMessagesExpanded ? 'expanded' : ''}`
                                                    })
                                                ),
                                                isSystemMessagesExpanded && React.createElement('div', {
                                                    className: 'system-messages-content'
                                                },
                                                    group.systemMessages.map((systemMessage, index) =>
                                                        React.createElement('div', {
                                                            key: `system-${groupIndex}-${index}-${systemMessage.id || ''}`,
                                                            className: 'system-message'
                                                        },
                                                            React.createElement('div', {
                                                                className: 'message-content',
                                                                dangerouslySetInnerHTML: { __html: marked.parse(systemMessage.content) }
                                                            })
                                                        )
                                                    )
                                                )
                                            )
                                        )
                                    );
                                })(),
                                loading && React.createElement(LoadingSpinner)
                            ),
                            React.createElement('div', { className: 'input-container' },
                                React.createElement('input', {
                                    type: 'text',
                                    value: inputValue,
                                    onChange: handleInputChange,
                                    onKeyPress: handleKeyPress,
                                    onBlur: handleBlur,
                                    placeholder: 'Enter your query',
                                    className: 'queryInput',
                                    ref: inputRef
                                })
                            )
                        )
                    )
                ),
                // Add modal component
                isModalOpen && React.createElement('div', { className: 'modal' },
                    React.createElement('textarea', {
                        value: modalInputValue,
                        onChange: handleModalInputChange,
                        placeholder: 'Enter context here...'
                    }),
                    React.createElement('div', { style: { display: 'flex', justifyContent: 'flex-end', alignItems: 'center' } },
                        React.createElement('button', {
                            onClick: handleContextSubmit,
                            disabled: contextLoading || !modalInputValue.trim(),
                            style: { marginRight: '10px' }
                        }, contextLoading ? '...' : 'Submit'),
                        React.createElement('button', {
                            onClick: handleModalClose
                        }, 'Close')
                    ),
                    contextSubmitStatus && React.createElement('div', { style: { color: contextSubmitStatus === 'Context added!' ? 'green' : 'red', marginTop: '10px' } }, contextSubmitStatus)
                )
            )
        )
    );
};

ReactDOM.render(React.createElement(App), document.getElementById('root')); 

// Add CSS for notifications
const notificationStyles = document.createElement('style');
notificationStyles.textContent = `
.notifications-container {
    position: fixed;
    top: 20px;
    right: 20px;
    z-index: 1000;
    display: flex;
    flex-direction: column;
    gap: 10px;
    max-height: 80vh;
    overflow-y: auto;
    pointer-events: none; /* Allow clicking through container */
}

.notification-bubble {
    background-color: var(--primary-color, #007bff);
    color: white;
    padding: 8px 12px;
    border-radius: 20px;
    box-shadow: 0 2px 5px rgba(0, 0, 0, 0.2);
    font-size: 14px;
    max-width: 200px;
    word-break: break-word;
    pointer-events: auto; /* Make bubbles clickable */
    cursor: pointer;
    animation: notification-pop 0.3s ease-out;
    transition: transform 0.2s;
}

.notification-bubble:hover {
    transform: scale(1.05);
}

@keyframes notification-pop {
    0% { transform: scale(0.8); opacity: 0; }
    50% { transform: scale(1.1); }
    100% { transform: scale(1); opacity: 1; }
}
`;
document.head.appendChild(notificationStyles); 