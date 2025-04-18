import React, { useEffect, useState, useRef } from 'react';
import { useTranslations } from 'next-intl';

interface Log {
  _id?: string; // Optional _id from database
  message: string;
  level: string;
  source: string;
  timestamp: string;
}

const LogPanel: React.FC = () => {
  const t = useTranslations('LogPanel');
  const [logs, setLogs] = useState<Log[]>([]);
  const [isConnected, setIsConnected] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const logEndRef = useRef<HTMLDivElement>(null); // Ref to scroll to

  // Fetch initial logs on component mount
  useEffect(() => {
    const fetchLogs = async () => {
      setIsLoading(true); // Start loading
      try {
        const response = await fetch('/api/logs');
        if (!response.ok) throw new Error('Failed to fetch logs');
        const data: Log[] = await response.json();

        // **MODIFICATION 1: Ensure initial logs are oldest first**
        // Assuming the API might return newest first, we sort by timestamp ascending.
        // If your API guarantees oldest first, you can remove the sort.
        data.sort((a, b) => new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime());

        setLogs(data);
      } catch (error) {
        console.error('Error fetching logs:', error);
        setLogs([]); // Set empty array on error
      } finally {
        setIsLoading(false); // Stop loading regardless of outcome
      }
    };

    fetchLogs();
  }, []); // Empty dependency array ensures this runs only once on mount

  // Connect to SSE stream for real-time updates
  useEffect(() => {
    const eventSource = new EventSource('/api/logs/stream');

    eventSource.onopen = () => {
      console.log('SSE Connection Opened');
      setIsConnected(true);
    };

    eventSource.onmessage = (event) => {
      try {
        const newLog: Log = JSON.parse(event.data);

        // Ignore potential connection confirmation messages if they exist
        if (newLog.message === 'Connected' || (newLog as any).connected) {
             console.log('SSE received connection confirmation');
             return;
        }

        // **MODIFICATION 2: Append new log to the END of the array**
        setLogs(prevLogs => [...prevLogs, newLog]);

      } catch (error) {
        console.error('Error parsing log data from SSE:', error, 'Data:', event.data);
      }
    };

    eventSource.onerror = (err) => {
      console.error('SSE Error:', err);
      setIsConnected(false);
      eventSource.close();

      // Optional: Implement a more robust reconnect strategy if needed
      // For now, reloading after a delay as in the original code
      console.log('Attempting to reconnect SSE after 5 seconds...');
      setTimeout(() => {
        // Consider a more targeted reconnect instead of full reload if possible
         window.location.reload();
      }, 5000);
    };

    // Cleanup function to close the connection when the component unmounts
    return () => {
      console.log('Closing SSE Connection');
      eventSource.close();
    };
  }, []); // Empty dependency array ensures this runs only once

  // Auto-scroll to bottom when new logs arrive
  useEffect(() => {
    // Scroll to the bottom whenever the logs array changes
    logEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [logs]); // Dependency array includes logs

  // Function to get badge color based on log level
  const getBadgeColor = (level: string) => {
    switch (level?.toLowerCase()) { // Added null check for safety
      case 'error': return 'badge-error';
      case 'warn': return 'badge-warning';
      case 'info': return 'badge-info';
      case 'debug': return 'badge-ghost';
      default: return 'badge-primary';
    }
  };

  // Function to format timestamp
  const formatTime = (timestamp: string) => {
    try {
      return new Date(timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
    } catch (e) {
      return t('invalidDate'); // Handle potential invalid date strings
    }
  };

  // Function to translate log level
  const translateLevel = (level: string) => {
    if (!level) return t('na');
    return t(`level.${level.toLowerCase()}`, { defaultValue: level });
  };

  return (
    <div className="text-base-content card bg-base-100 shadow-lg mb-6 h-full flex flex-col"> {/* Added h-full and flex */}
      <div className="card-body flex flex-col overflow-hidden"> {/* Added flex, flex-col, overflow-hidden */}
        {/* Header */}
        <div className="flex justify-between items-center mb-4 flex-shrink-0"> {/* Added flex-shrink-0 */}
          <h2 className="card-title text-primary">{t('title')}</h2>
          <div className="flex items-center gap-2">
            <span className="text-sm">{t('status')}:</span>
            <div className={`badge ${isConnected ? 'badge-success' : 'badge-error'}`}>
              {isConnected ? t('connected') : t('disconnected')}
            </div>
          </div>
        </div>

        {/* Log Area */}
        {isLoading ? (
          <div className="flex justify-center items-center flex-grow"> {/* Added flex-grow */}
            <span className="loading loading-spinner loading-lg"></span>
          </div>
        ) : (
          // **MODIFICATION 3: Ensure this div takes remaining space and scrolls**
          <div className="flex-grow overflow-y-auto max-h-[calc(100vh-200px)]"> {/* Adjust max-h as needed */}
            <div className="space-y-2 p-1"> {/* Added padding for scrollbar space */}
              {logs.length === 0 ? (
                <div className="text-center p-4 text-base-content/70">{t('noLogs')}</div>
              ) : (
                logs.map((log, index) => (
                  // Use timestamp + index as key for better stability if _id is missing temporarily
                  <div key={log._id || `${log.timestamp}-${index}`} className="bg-base-100 p-3 rounded-lg shadow-sm break-words">
                    <div className="flex justify-between items-start gap-2">
                      <div className="flex items-center gap-2 flex-wrap"> {/* Added flex-wrap */}
                        <div className={`badge ${getBadgeColor(log.level)}`}>{translateLevel(log.level)}</div>
                        <span className="text-xs opacity-70 whitespace-nowrap">{formatTime(log.timestamp)}</span>
                      </div>
                      <div className="badge badge-outline badge-sm flex-shrink-0">{log.source || t('unknown')}</div>
                    </div>
                    {/* Use pre-wrap to respect whitespace and wrap long lines */}
                    <p className="mt-2 whitespace-pre-wrap text-sm">{log.message}</p>
                  </div>
                ))
              )}
              {/* **MODIFICATION 4: Ref is still at the end, which is now the correct place** */}
              <div ref={logEndRef} />
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default LogPanel;