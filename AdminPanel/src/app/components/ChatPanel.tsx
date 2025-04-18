"use client";

import { useState, useEffect, useRef, useCallback, useLayoutEffect } from 'react';
import { useTranslations } from 'next-intl';
import { MessageSquare, Database, CheckSquare, Loader2, AlertTriangle, BadgeCheck, Info } from 'lucide-react';
import React from 'react';

// Define updated message structure
interface Message {
    message_id: string;    // MongoDB _id from Data Service
    _id: string;          // Same as message_id, added by server
    source_name: string;  // Source of the message
    chat_id: string;      // ID of the chat
    text: string;         // Message content
    sender_id?: string;   // Optional ID of sender
    sender_name: string;  // Name of the sender
    image?: any;          // Optional image data
    // Data can be present, explicitly null, or undefined initially
    data?: Record<string, string> | null;
    timestamp: string;    // Message timestamp
    updated_at: string;   // Last update time
}

// Interface for props
interface MessagesPanelProps {
    chatIds: string[];
    chats: any[]; // Consider a more specific type if possible
    allChats: any[]; // Consider a more specific type if possible
}

const MessagesPanel: React.FC<MessagesPanelProps> = ({ chatIds, chats, allChats }) => {
    const t = useTranslations('chatPanel');
    const [allMessages, setAllMessages] = useState<Message[]>([]);
    const containerRef = useRef<HTMLDivElement>(null);
    const [isUserAtBottom, setIsUserAtBottom] = useState(true);
    const isInitialRenderForChatIds = useRef(true);
    const [isLoading, setIsLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const shouldScrollAfterUpdate = useRef(false);

    // Ref to track scroll state without triggering SSE reconnect
    const isUserAtBottomRef = useRef(isUserAtBottom);
    useEffect(() => {
        isUserAtBottomRef.current = isUserAtBottom;
    }, [isUserAtBottom]);

    // Chat Name Mapping
    const chatNameMap = useRef<Record<string, string>>({});
    useEffect(() => {
        const newMap: Record<string, string> = {};
        allChats?.forEach(chat => {
            if (chat.chat_id) newMap[chat.chat_id] = chat.chat_name || chat.chat_id;
        });
        chats?.forEach(chat => {
            if (chat.chat_id && !newMap[chat.chat_id]) {
                newMap[chat.chat_id] = chat.chat_name || chat.chat_id;
            }
        });
        chatNameMap.current = newMap;
    }, [chats, allChats]);

    const getChatName = useCallback((chatId: string) => {
        return chatNameMap.current[chatId] || t('unknownChat');
    }, [t]);

    // Scrolling Logic
    const scrollToBottom = useCallback((behavior: ScrollBehavior = 'smooth') => {
        requestAnimationFrame(() => {
            if (containerRef.current) {
                const { scrollHeight, clientHeight } = containerRef.current;
                const maxScrollTop = scrollHeight - clientHeight;
                containerRef.current.scrollTo({
                    top: maxScrollTop > 0 ? maxScrollTop : 0,
                    behavior: behavior
                });

                if (behavior === 'smooth' || (behavior === 'auto' && !isInitialRenderForChatIds.current)) {
                    const delay = behavior === 'auto' ? 50 : 0;
                    setTimeout(() => setIsUserAtBottom(true), delay);
                }
            }
        });
    }, []);

    const handleScroll = useCallback(() => {
        if (containerRef.current) {
            const { scrollTop, scrollHeight, clientHeight } = containerRef.current;
            const isNearBottom = scrollHeight - scrollTop - clientHeight <= 10;
            setIsUserAtBottom(prev => prev === isNearBottom ? prev : isNearBottom);
        }
    }, []);

    // Effect for Initial Message Load
    useEffect(() => {
        setAllMessages([]);
        setError(null);
        setIsLoading(true);
        setIsUserAtBottom(true);
        isInitialRenderForChatIds.current = true;
        console.log("Initial fetch effect triggered for chatIds:", chatIds.join(', '));

        const fetchInitialMessages = async () => {
            if (chatIds.length === 0) {
                setIsLoading(false);
                return;
            }

            console.log(`Fetching initial messages for chats: ${chatIds.join(', ')}`);
            try {
                const fetchPromises = chatIds.map(async (chatId) => {
                    const response = await fetch(`/api/chats/messages/${chatId}`);
                    if (!response.ok) {
                        console.error(`Failed to fetch messages for chat ${chatId}: ${response.statusText}`);
                        let errorDetail = `Server responded with status ${response.status}`;
                        try { const errorData = await response.json(); errorDetail = errorData.detail || errorDetail; } catch (e) { /* ignore */ }
                        throw new Error(`Failed to fetch messages for chat ${chatId}: ${errorDetail}`);
                    }
                    const data: Message[] = await response.json();
                    return data;
                });

                const results = await Promise.all(fetchPromises);
                const mergedMessages = results.flat();
                mergedMessages.sort((a, b) =>
                    new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime()
                );

                setAllMessages(mergedMessages);
                console.log('Initial messages loaded:', mergedMessages.length);

                setTimeout(() => {
                    scrollToBottom('auto');
                    isInitialRenderForChatIds.current = false;
                    console.log("Initial scroll ('auto') performed. Initial render phase finished.");
                }, 0);

            } catch (error) {
                console.error("Error fetching initial messages:", error);
                setError(error instanceof Error ? error.message : t('errorFetchingMessages'));
                setAllMessages([]);
                isInitialRenderForChatIds.current = false;
            } finally {
                setIsLoading(false);
                console.log("Initial fetch finished, setIsLoading(false)");
            }
        };

        fetchInitialMessages();

        return () => {
            console.log("Cleanup initial fetch effect for chatIds:", chatIds.join(', '));
            isInitialRenderForChatIds.current = false;
        };
    }, [chatIds, t, scrollToBottom]);

    // Effect for SSE Connection
    useEffect(() => {
        if (chatIds.length === 0) {
            console.log("SSE setup skipped: No chat IDs selected.");
            shouldScrollAfterUpdate.current = false;
            return;
        }

        console.log('>>> Setting up SSE connection for chats:', chatIds.join(', '));
        const eventSource = new EventSource('/api/chats/stream_messages');
        let isMounted = true;

        eventSource.onopen = () => {
            if (!isMounted) return;
            console.log('SSE Connection opened successfully.');
            setError(null);
        };

        eventSource.onmessage = (event) => {
            if (!isMounted) return;
            try {
                const incomingData = JSON.parse(event.data);
                console.log("SSE Received:", incomingData); // Log raw incoming data

                if (incomingData.type === "connection_established") {
                    console.log("SSE connection established successfully");
                    return;
                }

                const incomingMessage: Partial<Message> & { message_id: string, chat_id: string, timestamp: string } = incomingData;

                if (!incomingMessage.message_id || !incomingMessage.chat_id || !incomingMessage.timestamp) {
                    console.warn("SSE Received invalid/incomplete message object:", incomingMessage);
                    return;
                }

                if (chatIds.includes(incomingMessage.chat_id)) {
                    console.log(`SSE Processing message for chat ${incomingMessage.chat_id} (ID: ${incomingMessage.message_id})`);

                    const shouldScroll = isUserAtBottomRef.current;
                    shouldScrollAfterUpdate.current = shouldScroll;

                    setAllMessages((prevMessages) => {
                        const existingMessageIndex = prevMessages.findIndex(msg =>
                            msg.message_id === incomingMessage.message_id || msg._id === incomingMessage.message_id);

                        if (existingMessageIndex !== -1) {
                            console.log(`SSE Updating message ID: ${incomingMessage.message_id}`);
                            const updatedMessages = [...prevMessages];
                            // Merge incoming data with existing, ensuring all required fields are present
                            const updatedMsg = {
                                ...prevMessages[existingMessageIndex],
                                ...incomingMessage,
                                // Ensure required fields from original if not in update (though they should be)
                                _id: prevMessages[existingMessageIndex]._id || incomingMessage.message_id,
                                source_name: incomingMessage.source_name ?? prevMessages[existingMessageIndex].source_name,
                                sender_name: incomingMessage.sender_name ?? prevMessages[existingMessageIndex].sender_name,
                                text: incomingMessage.text ?? prevMessages[existingMessageIndex].text,
                                // Crucially, update 'data' if present in the incoming message
                                data: incomingMessage.data !== undefined ? incomingMessage.data : prevMessages[existingMessageIndex].data,
                                updated_at: incomingMessage.updated_at || new Date().toISOString(), // Update timestamp
                            };
                            updatedMessages[existingMessageIndex] = updatedMsg as Message; // Assert type after merge
                            return updatedMessages;
                        } else {
                            // Add new message - ensure it conforms to the full Message interface
                            // Provide defaults for potentially missing non-required fields if needed
                            console.log(`SSE Adding new message ID: ${incomingMessage.message_id}`);
                            const newMessage: Message = {
                                message_id: incomingMessage.message_id,
                                _id: incomingMessage.message_id, // Use message_id for _id initially
                                source_name: incomingMessage.source_name || 'Unknown Source',
                                chat_id: incomingMessage.chat_id,
                                text: incomingMessage.text || '', // Default to empty string if missing
                                sender_id: incomingMessage.sender_id,
                                sender_name: incomingMessage.sender_name || 'Unknown Sender',
                                image: incomingMessage.image,
                                data: incomingMessage.data, // Can be undefined/null initially
                                timestamp: incomingMessage.timestamp,
                                updated_at: incomingMessage.updated_at || incomingMessage.timestamp,
                            };
                            const updatedMessages = [...prevMessages, newMessage];
                            updatedMessages.sort((a, b) =>
                                new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime()
                            );
                            return updatedMessages;
                        }
                    });
                }
            } catch (e) {
                console.error('Failed to parse or process SSE message:', e, "\nRaw data:", event.data);
            }
        };

        eventSource.onerror = (error) => {
            if (!isMounted) return;
            console.error('SSE Error:', error);
            if (eventSource.readyState === EventSource.CLOSED) {
                console.log("SSE connection closed by server or network issue.");
            } else if (eventSource.readyState === EventSource.CONNECTING) {
                console.log("SSE connection attempt failed or was interrupted.");
                setError(t('sseConnectionError'));
            } else {
                console.error("SSE unknown error state:", eventSource.readyState);
                setError(t('sseConnectionError'));
            }
            eventSource.close();
        };

        return () => {
            isMounted = false;
            console.log('<<< Closing SSE connection...');
            eventSource.close();
            setError(null);
            shouldScrollAfterUpdate.current = false;
        };
    }, [chatIds, t]);

    // Effect to handle scrolling after new messages render
    useLayoutEffect(() => {
        if (shouldScrollAfterUpdate.current && containerRef.current) {
            scrollToBottom('auto');
            shouldScrollAfterUpdate.current = false;
        } else if (shouldScrollAfterUpdate.current) {
            console.warn("LayoutEffect: Scroll after update skipped because containerRef not ready?");
            shouldScrollAfterUpdate.current = false;
        }
    }, [allMessages, scrollToBottom]);

    // Rendering message data - MODIFIED to handle initially missing data
    const renderMessageData = (messageData: Record<string, any> | Array<Record<string, any>> | undefined | null) => {
        // 1. Handle explicitly missing data (initial state before update)
        if (messageData === undefined || messageData === null) {
            return (
                <div className="mt-2 text-xs opacity-70 flex items-center gap-1 text-info">
                    <Loader2 className="animate-spin h-3 w-3" />
                    <span>{t('processingReport')}...</span>
                </div>
            );
        }

        // Check if messageData is an array (new format)
        if (Array.isArray(messageData)) {
            if (messageData.length === 0) {
                return (
                    <div className="mt-1 text-xs opacity-60 flex items-center gap-1">
                        <BadgeCheck className="h-3 w-3 text-success" />
                        <span>{t('reportProcessedEmpty')}</span>
                    </div>
                );
            }

            // Extract column headers from the first object
            const headers = Object.keys(messageData[0]);

            return (
                <div className="mt-2 overflow-x-auto">
                    <table className="table table-xs table-zebra w-full text-xs">
                        <thead>
                            <tr className="bg-base-300">
                                {headers.map((header, index) => (
                                    <th key={index} className="font-medium">{header}</th>
                                ))}
                            </tr>
                        </thead>
                        <tbody>
                            {messageData.map((row, rowIndex) => (
                                <tr key={rowIndex}>
                                    {headers.map((header, colIndex) => (
                                        <td key={colIndex}>{row[header] || ''}</td>
                                    ))}
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
            );
        }

        // Original implementation for non-array data
        const status = messageData.status;

        // Explicit processing status within data object
        if (status === 'processing') {
            return (
                <div className="mt-2 text-xs opacity-70 flex items-center gap-1 text-info">
                    <Loader2 className="animate-spin h-3 w-3" />
                    <span>{t('processingReport')}...</span>
                </div>
            );
        }
        // Explicit error status
        else if (status === 'error') {
            return (
                <div className="mt-2 bg-error/10 p-2 rounded-md text-xs border border-error/30">
                    <div className="flex items-center gap-1.5 font-medium text-error mb-1">
                        <AlertTriangle className="h-3.5 w-3.5" />
                        <span>{t('processingError')}:</span>
                    </div>
                    <pre className="whitespace-pre-wrap break-all text-error/90 pl-1">
                        {messageData.detail || t('unknownError')}
                    </pre>
                </div>
            );
        }
        // Data exists, not explicitly processing or error
        else {
            const displayData = { ...messageData };
            delete displayData.status; // Remove status for display purposes

            // Check if there's any actual data left to display
            if (Object.keys(displayData).length > 0) {
                const isProcessed = status === 'processed'; // Check original status
                return (
                    <div className="mt-2 bg-base-300/30 p-2 rounded-md text-xs border border-base-300/50">
                        <div className="flex items-center gap-1.5 font-medium text-base-content/90 mb-1">
                            {isProcessed ? <BadgeCheck className="h-3.5 w-3.5 text-success" /> : <Info className="h-3.5 w-3.5" />}
                            <span>{t('additionalData')}:</span>
                        </div>
                        <pre className="whitespace-pre-wrap break-all pl-1">
                            {JSON.stringify(displayData, null, 2)}
                        </pre>
                    </div>
                );
            }
            // No data fields left, check if it was marked as processed
            else if (status === 'processed') {
                return (
                    <div className="mt-1 text-xs opacity-60 flex items-center gap-1">
                        <BadgeCheck className="h-3 w-3 text-success" />
                        <span>{t('reportProcessedEmpty')}</span>
                    </div>
                );
            }
            // Data existed, wasn't processing/error, empty after removing status, and not explicitly processed?
            else {
                return null;
            }
        }
    };

    const renderContent = () => {
        if (isLoading && isInitialRenderForChatIds.current) {
            return (
                <div className="flex justify-center items-center h-full">
                    <Loader2 className="animate-spin h-8 w-8 text-primary" />
                </div>
            );
        }

        if (error) {
            const errorPrefix = error.includes("SSE") ? t('sseErrorPrefix') : t('errorLoadingMessages');
            return (
                <div className="alert alert-error m-4">
                    <AlertTriangle />
                    <span>{errorPrefix}: {error}</span>
                </div>
            );
        }

        if (chatIds.length === 0) {
            return (
                <div className="flex justify-center items-center h-full text-base-content/70">
                    <MessageSquare className="mr-2 h-5 w-5" />
                    {t('selectChatsToView')}
                </div>
            );
        }

        if (!isLoading && allMessages.length === 0) {
            return (
                <div className="flex justify-center items-center h-full text-base-content/70">
                    {t('noMessages')}
                </div>
            );
        }

        // Render messages with updated structure
        return allMessages.map((message) => {
            // Add a check for message validity, especially after potential partial updates
            if (!message?.message_id || !message.chat_id || !message.timestamp) {
                console.warn("Skipping rendering invalid message object:", message);
                return null;
            }

            const chatName = getChatName(message.chat_id);
            const messageKey = message.message_id + '-' + message.updated_at; // Use updated_at for better keying on updates
            const dataContent = renderMessageData(message.data); // Pass message.data here

            return (
                <div key={messageKey} className="chat chat-start mb-4 px-4">
                    <div className="chat-bubble bg-base-100 text-base-content break-words max-w-[95%] sm:max-w-[85%] md:max-w-[75%]">
                        {/* Header */}
                        <div className="flex flex-wrap items-center gap-x-3 gap-y-1 mb-1 text-xs opacity-80">
                            {message.source_name && (
                                <span className="font-medium">{message.source_name}</span>
                            )}
                            {chatIds.length > 1 && (
                                <span className="badge badge-ghost badge-sm">{chatName}</span>
                            )}
                            <span className="whitespace-nowrap">
                                {new Date(message.timestamp).toLocaleString()}
                            </span>
                            {/* Optional: Show updated time if different from timestamp */}
                            {message.updated_at && message.timestamp !== message.updated_at && (
                                <span className="text-xs opacity-60 ml-1">(updated {new Date(message.updated_at).toLocaleTimeString()})</span>
                            )}
                        </div>
                        {/* Sender */}
                        <div className="font-semibold text-primary mb-0.5">
                            {message.sender_name ?? t('unknownSender')}
                            
                        </div>
                        {/* Text */}
                        {message.text != null && message.text !== '' && ( // Also check for empty string
                            <div className="mt-1 whitespace-pre-wrap">{message.text}</div>
                        )}
                        {/* Image if present */}
                        {message.image && (
                            <div className="mt-2 rounded-md overflow-hidden">
                                <img src={message.image} alt="Message attachment" className="max-w-full" />
                            </div>
                        )}
                        {/* Data/Report Section */}
                        {dataContent} {/* Render the result from renderMessageData */}
                    </div>
                </div>
            );
        });
    };

    return (
        <div
            className="bg-base-200 rounded-box h-[32rem] lg:h-[40rem] overflow-y-auto relative"
            ref={containerRef}
            onScroll={handleScroll}
            style={{ scrollBehavior: 'smooth' }}
        >
            {renderContent()}
        </div>
    );
};


// The rest of the ChatPanel component (state, handlers, JSX) remains the same as in your original code.
// Make sure to export ChatPanel if it's not already done.
export default function ChatPanel() {
    const t = useTranslations('chatPanel');

    const [dataSources, setDataSources] = useState<string[]>([]);
    const [selectedDataSources, setSelectedDataSources] = useState<string[]>([]);
    const [chats, setChats] = useState<any[]>([]);
    const [selectedChats, setSelectedChats] = useState<string[]>([]);
    const [allChats, setAllChats] = useState<any[]>([]);
    const [selectedConfigSource, setSelectedConfigSource] = useState<string>('');
    const [isUpdating, setIsUpdating] = useState(false);
    const [message, setMessage] = useState({ text: '', type: '' });

    // Fetch data sources on component mount
    useEffect(() => {
        fetchDataSources();
    }, []);

    // Fetch chats for selected data sources
    useEffect(() => {
        if (selectedDataSources.length > 0) {
            fetchChatsFromMultipleSources();
        } else {
            setChats([]);
            setSelectedChats([]);
        }
    }, [selectedDataSources]);

    // Fetch all chats for configuration
    useEffect(() => {
        if (selectedConfigSource) {
            fetchAllChats(selectedConfigSource);
        } else {
            setAllChats([]);
        }
    }, [selectedConfigSource]);

    const fetchDataSources = async () => {
        console.log('Fetching data sources...');
        try {
            // Updated API endpoint
            const response = await fetch('/api/chats/datasources');
            if (!response.ok) {
                const errorData = await response.json().catch(() => ({ detail: 'Failed to fetch data sources' }));
                throw new Error(errorData.detail || "Unknown error fetching data sources");
            }

            const data = await response.json();
            const sources = data.datasources || [];
            setDataSources(sources);

            // Select all sources by default and set the first as config source
            if (sources.length > 0) {
                setSelectedDataSources(sources);
                if (!selectedConfigSource) {
                    setSelectedConfigSource(sources[0]);
                }
            }
            console.log('Data sources loaded:', sources);
        } catch (error) {
            console.error("Error fetching data sources:", error);
            setMessage({ text: error instanceof Error ? error.message : String(error), type: 'error' });
        }
    };

    // Fetches active chats from selected sources
    const fetchChatsFromMultipleSources = async () => {
        console.log(`Fetching active chats for sources: ${selectedDataSources.join(', ')}`);
        setMessage({ text: '', type: '' });
        try {
            const fetchPromises = selectedDataSources.map(async (sourceName) => {
                // Updated API endpoint
                const response = await fetch(`/api/chats/?source_name=${sourceName}`);
                if (!response.ok) {
                    console.warn(`Failed to fetch chats for source ${sourceName}: ${response.statusText}`);
                    return [];
                }
                const data = await response.json();
                return (data.chats || []).filter((chat: any) => chat.active);
            });

            const results = await Promise.all(fetchPromises);
            const activeChats = results.flat();
            setChats(activeChats);
            console.log('Active chats for viewer loaded:', activeChats);

            // Keep selected chats that are still valid
            setSelectedChats(prevSelected =>
                prevSelected.filter(id => activeChats.some(chat => chat.chat_id === id))
            );

        } catch (error) {
            console.error("Error fetching active chats:", error);
            setMessage({ text: error instanceof Error ? error.message : String(error), type: 'error' });
            setChats([]);
            setSelectedChats([]);
        }
    };

    // Fetches all chats for configuration
    const fetchAllChats = async (sourceName: string) => {
        console.log(`Fetching all chats for configuration: ${sourceName}`);
        setMessage({ text: '', type: '' });
        try {
            // Updated API endpoint
            const response = await fetch(`/api/chats/?source_name=${sourceName}`);
            if (!response.ok) {
                const errorData = await response.json().catch(() => ({ detail: `Failed to fetch chats for ${sourceName}` }));
                throw new Error(errorData.detail || `Unknown error fetching chats for ${sourceName}`);
            }
            const data = await response.json();
            setAllChats(data.chats || []);
            console.log(`All chats for ${sourceName} loaded:`, data.chats);
        } catch (error) {
            console.error(`Error fetching all chats for ${sourceName}:`, error);
            setMessage({ text: error instanceof Error ? error.message : String(error), type: 'error' });
            setAllChats([]);
        }
    };

    // Toggles chat active status
    const handleToggleChat = async (chatId: string, currentActiveState: boolean) => {
        if (!selectedConfigSource) return;

        setIsUpdating(true);
        setMessage({ text: '', type: '' });

        try {
            // Updated API endpoint and method
            const response = await fetch(`/api/chats/${chatId}`, {
                method: 'PATCH',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    source_name: selectedConfigSource,
                    active: !currentActiveState
                }),
            });

            if (!response.ok) {
                const error = await response.json().catch(() => ({ detail: 'Failed to update chat status' }));
                throw new Error(error.detail || "Unknown error updating chat status");
            }

            // Update local state
            setAllChats(prevAllChats =>
                prevAllChats.map(chat =>
                    chat.chat_id === chatId
                        ? { ...chat, active: !currentActiveState }
                        : chat
                )
            );

            // Refresh active chats if needed
            if (selectedDataSources.includes(selectedConfigSource)) {
                await fetchChatsFromMultipleSources();
            }

            setMessage({ text: t('chatStatusUpdated'), type: 'success' });
            setTimeout(() => setMessage({ text: '', type: '' }), 3000);

        } catch (error) {
            console.error("Error toggling chat active status:", error);
            setMessage({ text: error instanceof Error ? error.message : String(error), type: 'error' });
            await fetchAllChats(selectedConfigSource);
        } finally {
            setIsUpdating(false);
        }
    };

    // UI handlers remain the same
    const handleToggleDataSource = (sourceName: string) => {
        setSelectedDataSources(prev =>
            prev.includes(sourceName)
                ? prev.filter(name => name !== sourceName)
                : [...prev, sourceName]
        );
    };

    const handleSelectAllDataSources = () => {
        if (selectedDataSources.length === dataSources.length) {
            setSelectedDataSources([]);
        } else {
            setSelectedDataSources([...dataSources]);
        }
    };

    const handleToggleSelectedChat = (chatId: string) => {
        setSelectedChats(prev =>
            prev.includes(chatId)
                ? prev.filter(id => id !== chatId)
                : [...prev, chatId]
        );
    };

    const handleSelectAllChats = () => {
        if (selectedChats.length === chats.length) {
            setSelectedChats([]);
        } else {
            setSelectedChats(chats.map(chat => chat.chat_id));
        }
    };

    return (
        <div className="w-full text-base-content">
            {message.text && (
                <div className={`alert ${message.type === 'success' ? 'alert-success' : 'alert-error'} mb-4 shadow-md`}>
                    <div className="flex-1">
                        <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" className="w-6 h-6 mx-2 stroke-current">
                            {message.type === 'success' ? <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"></path> : <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M18.364 18.364A9 9 0 005.636 5.636m12.728 12.728A9 9 0 015.636 5.636m12.728 12.728L5.636 5.636"></path>}
                        </svg>
                        <label>{message.text}</label>
                    </div>
                </div>
            )}

            {/* Chat viewer section */}
            <div className="card bg-base-100 shadow-lg mb-8">
                <div className="card-body">
                    <div className="flex items-center gap-2 mb-4">
                        <MessageSquare size={20} className="text-primary" />
                        <h3 className="text-lg font-medium">{t('chatViewer')}</h3>
                    </div>

                    {/* Data Source Selection for Viewer */}
                    <div className="mb-6">
                        <div className="flex justify-between items-center mb-2">
                            <label className="label">
                                <span className="label-text font-medium">{t('selectDataSource')}</span>
                            </label>
                            {dataSources.length > 0 && (
                                <button
                                    className="btn btn-xs btn-outline"
                                    onClick={handleSelectAllDataSources}
                                    disabled={dataSources.length === 0}
                                >
                                    {selectedDataSources.length === dataSources.length ? t('deselectAll') : t('selectAll')}
                                </button>
                            )}
                        </div>
                        <div className="bg-base-200 rounded-box p-4 mb-2">
                            {dataSources.length === 0 ? (
                                <div className="text-center text-base-content/70">{t('noDataSources')}</div>
                            ) : (
                                <div className="flex flex-wrap gap-2">
                                    {dataSources.map((source) => (
                                        <div
                                            key={source}
                                            className={`badge badge-lg cursor-pointer transition-colors duration-150 ${selectedDataSources.includes(source)
                                                ? 'badge-primary'
                                                : 'badge-outline hover:bg-primary/20'
                                                }`}
                                            onClick={() => handleToggleDataSource(source)}
                                        >
                                            {source}
                                        </div>
                                    ))}
                                </div>
                            )}
                        </div>
                    </div>

                    {/* Active Chat Selection for Viewer */}
                    <div className="mb-6">
                        <div className="flex justify-between items-center mb-2">
                            <label className="label">
                                <span className="label-text font-medium">{t('selectChat')}</span>
                            </label>
                            {chats.length > 0 && (
                                <button
                                    className="btn btn-xs btn-outline"
                                    onClick={handleSelectAllChats}
                                >
                                    {selectedChats.length === chats.length ? t('deselectAll') : t('selectAll')}
                                </button>
                            )}
                        </div>

                        <div className="bg-base-200 rounded-box p-3">
                            {selectedDataSources.length === 0 ? (
                                <div className="text-center text-base-content/70 py-2">{t('selectDataSourceFirst')}</div>
                            ) : chats.length === 0 ? (
                                <div className="text-center text-base-content/70 py-2">{t('noActiveChats')}</div>
                            ) : (
                                <div className="flex flex-wrap gap-2">
                                    {chats.map((chat) => (
                                        <div
                                            key={chat.chat_id}
                                            className={`badge badge-lg cursor-pointer transition-colors duration-150 ${selectedChats.includes(chat.chat_id)
                                                ? 'badge-secondary'
                                                : 'badge-outline hover:bg-secondary/20'
                                                }`}
                                            onClick={() => handleToggleSelectedChat(chat.chat_id)}
                                        >
                                            {chat.chat_name || t('unnamed')} ({chat.source_name})
                                        </div>
                                    ))}
                                </div>
                            )}
                        </div>
                    </div>

                    {/* Messages Panel */}
                    <MessagesPanel chatIds={selectedChats} chats={chats} allChats={allChats} />
                </div>
            </div>

            {/* Chat configuration section */}
            <div className="card bg-base-100 shadow-lg">
                <div className="card-body">
                    <div className="flex items-center gap-2 mb-4">
                        <Database size={20} className="text-primary" />
                        <h3 className="text-lg font-medium">{t('chatConfiguration')}</h3>
                    </div>

                    {/* Data Source Selection for Config */}
                    <div className="form-control mb-4">
                        <label className="label">
                            <span className="label-text font-medium">{t('configureDataSource')}</span>
                        </label>
                        <select
                            className="select select-bordered w-full"
                            value={selectedConfigSource}
                            onChange={(e) => setSelectedConfigSource(e.target.value)}
                            disabled={dataSources.length === 0}
                        >
                            <option value="" disabled>{t('selectSourcePrompt')}</option>
                            {dataSources.map((source) => (
                                <option key={source} value={source}>{source}</option>
                            ))}
                        </select>
                    </div>

                    {/* Chat Activation List */}
                    <div className="bg-base-200 rounded-box p-4 mb-4 min-h-[10rem]">
                        <h4 className="font-medium mb-3">{t('availableChats')} ({selectedConfigSource || t('noSourceSelected')})</h4>

                        {!selectedConfigSource ? (
                            <div className="text-base-content/70 text-center py-4">{t('selectSourceToConfigure')}</div>
                        ) : allChats.length === 0 ? (
                            <div className="text-base-content/70 text-center py-4">{t('noChatsAvailableForSource')}</div>
                        ) : (
                            <div className="space-y-2 max-h-60 overflow-y-auto pr-2">
                                {allChats.map((chat) => (
                                    <div key={chat.chat_id} className="form-control">
                                        <label className="label cursor-pointer justify-start gap-3 p-2 hover:bg-base-100/50 rounded-md">
                                            <input
                                                type="checkbox"
                                                className="checkbox checkbox-primary checkbox-sm"
                                                checked={chat.active || false}
                                                onChange={() => handleToggleChat(chat.chat_id, chat.active || false)}
                                                disabled={isUpdating}
                                            />
                                            <span className="label-text flex-grow">
                                                {chat.chat_name || t('unnamed')}
                                                <span className="text-xs opacity-60 ml-2">({chat.chat_id})</span>
                                            </span>
                                            {isUpdating && <span className="loading loading-spinner loading-xs ml-2"></span>}
                                        </label>
                                    </div>
                                ))}
                            </div>
                        )}
                    </div>
                </div>
            </div>
        </div>
    );
}