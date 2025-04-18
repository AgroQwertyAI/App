"use client"; // This component uses hooks and event handlers

import React, { useState, useEffect, useCallback } from 'react';
import Papa from 'papaparse';
import { useTranslations } from 'next-intl';

// Define types for better code clarity
interface Chat {
    chat_id: string;
    chat_name: string;
    active: boolean;
    source_name: string;
}

// Assuming report data rows are objects with string keys/values after parsing
type ReportRow = Record<string, string>;

export default function ReportGeneratorPage() {
    const t = useTranslations('reports');
    
    const [chats, setChats] = useState<Chat[]>([]);
    const [selectedChatId, setSelectedChatId] = useState<string>('');
    const [reportData, setReportData] = useState<ReportRow[]>([]);
    const [reportHeaders, setReportHeaders] = useState<string[]>([]);
    const [isLoadingChats, setIsLoadingChats] = useState<boolean>(false);
    const [isGeneratingReport, setIsGeneratingReport] = useState<boolean>(false);
    const [isDownloading, setIsDownloading] = useState<boolean>(false);
    const [error, setError] = useState<string | null>(null);
    const [startDate, setStartDate] = useState<string>('');
    const [endDate, setEndDate] = useState<string>('');

    // Fetch active chats from both WhatsApp and Telegram
    const fetchChats = useCallback(async () => {
        setIsLoadingChats(true);
        setError(null);
        setChats([]); // Clear previous chats

        try {
            // Fetch chats from both sources
            const [whatsappResponse, telegramResponse] = await Promise.all([
                fetch(`/api/chats?source_name=${encodeURIComponent("whatsapp")}`),
                fetch(`/api/chats?source_name=${encodeURIComponent("telegram")}`)
            ]);

            if (!whatsappResponse.ok) {
                const errorData = await whatsappResponse.json();
                throw new Error(errorData.error || t('errors.whatsappFetch', { status: whatsappResponse.status }));
            }

            if (!telegramResponse.ok) {
                const errorData = await telegramResponse.json();
                throw new Error(errorData.error || t('errors.telegramFetch', { status: telegramResponse.status }));
            }

            const whatsappData: { chats: Chat[] } = await whatsappResponse.json();
            const telegramData: { chats: Chat[] } = await telegramResponse.json();

            // Combine and filter active chats from both sources
            const allActiveChats = [
                ...whatsappData.chats.filter(chat => chat.active),
                ...telegramData.chats.filter(chat => chat.active)
            ];

            setChats(allActiveChats);
        } catch (err: any) {
            console.error("Error fetching chats:", err);
            setError(err.message || t('errors.unknown'));
        } finally {
            setIsLoadingChats(false);
        }
    }, [t]);

    // Fetch chats on component mount
    useEffect(() => {
        fetchChats();
    }, [fetchChats]);

    // Handle chat selection change
    const handleChatSelect = (event: React.ChangeEvent<HTMLSelectElement>) => {
        setSelectedChatId(event.target.value);
        // Reset report data when selection changes
        setReportData([]);
        setReportHeaders([]);
        setError(null);
    };

    // Generate report for display
    const generateReport = async () => {
        if (!selectedChatId) return;

        setIsGeneratingReport(true);
        setError(null);
        setReportData([]);
        setReportHeaders([]);

        try {
            // Use our new API endpoint with POST request
            const url = `/api/tables/${encodeURIComponent(selectedChatId)}`;

            // Get columns from report headers or use default empty array if not available
            const columns = reportHeaders.length > 0 ? reportHeaders : [];

            // Default to a recent time range if not specified
            const now = new Date();
            const oneMonthAgo = new Date();
            oneMonthAgo.setMonth(oneMonthAgo.getMonth() - 1);

            // Format dates with time component to ensure proper parsing
            const formatDateForAPI = (date: Date) => {
                return date.toISOString(); // Full ISO timestamp with timezone
            };

            // Updated request body
            const requestBody = {
                time: {
                    start: startDate ? `${startDate}T00:00:00Z` : formatDateForAPI(oneMonthAgo),
                    end: endDate ? `${endDate}T23:59:59Z` : formatDateForAPI(now),
                    format: "iso"
                },
                columns: columns,
                format: "csv" // Always use CSV for preview
            };

            const response = await fetch(url, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(requestBody)
            });

            if (!response.ok) {
                // Try to get error message from response body if possible
                let errorMsg = t('errors.reportGeneration', { status: response.status });
                try {
                    const errorText = await response.text();
                    errorMsg = t('errors.reportGenerationWithDetails', {
                        details: errorText || response.statusText
                    });
                } catch  { /* Ignore parsing error */ }
                throw new Error(errorMsg);
            }

            const csvText = await response.text();

            // Parse CSV data
            Papa.parse<ReportRow>(csvText, {
                header: true, // Assumes first row is header
                skipEmptyLines: true,
                complete: (results) => {
                    if (results.errors.length > 0) {
                        console.error("CSV Parsing errors:", results.errors);
                        setError(t('errors.csvParse', { details: results.errors[0]?.message || '' }));
                        setReportData([]);
                        setReportHeaders([]);
                    } else {
                        setReportHeaders(results.meta.fields || []);
                        setReportData(results.data);
                    }
                },
                error: (err: Error) => {
                    console.error("CSV Parsing error:", err);
                    setError(t('errors.csvParseDetailed', { details: err.message }));
                    setReportData([]);
                    setReportHeaders([]);
                }
            });

        } catch (err: any) {
            console.error("Error generating report:", err);
            setError(err.message || t('errors.reportGenerationUnknown'));
            setReportData([]);
            setReportHeaders([]);
        } finally {
            setIsGeneratingReport(false);
        }
    };

    // Download report file
    const downloadReport = async (format: 'csv' | 'xlsx') => {
        if (!selectedChatId) return;

        setIsDownloading(true);
        setError(null); // Clear previous errors

        try {
            // Use our new API endpoint with POST request
            const url = `/api/tables/${encodeURIComponent(selectedChatId)}`;

            // Get columns from report headers or use default empty array if not available
            const columns = reportHeaders.length > 0 ? reportHeaders : [];

            // Default to a recent time range if not specified
            const now = new Date();
            const oneMonthAgo = new Date();
            oneMonthAgo.setMonth(oneMonthAgo.getMonth() - 1);

            // Format dates with time component to ensure proper parsing
            const formatDateForAPI = (date: Date) => {
                return date.toISOString(); // Full ISO timestamp with timezone
            };

            // Updated request body
            const requestBody = {
                time: {
                    start: startDate ? `${startDate}T00:00:00Z` : formatDateForAPI(oneMonthAgo),
                    end: endDate ? `${endDate}T23:59:59Z` : formatDateForAPI(now),
                    format: "iso"
                },
                columns: columns,
                format: format
            };

            const response = await fetch(url, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(requestBody)
            });

            if (!response.ok) {
                let errorMsg = t('errors.downloadFailed', { status: response.status });
                try {
                    const errorText = await response.text();
                    errorMsg = t('errors.downloadFailedDetails', { 
                        details: errorText || response.statusText 
                    });
                } catch { /* Ignore parsing error */ }
                throw new Error(errorMsg);
            }

            const blob = await response.blob();
            const downloadUrl = window.URL.createObjectURL(blob);
            const link = document.createElement('a');
            link.href = downloadUrl;
            link.download = `report-${selectedChatId}.${format}`; // Set filename
            document.body.appendChild(link);
            link.click(); // Trigger download
            document.body.removeChild(link); // Clean up
            window.URL.revokeObjectURL(downloadUrl); // Free up memory

        } catch (err: any) {
            console.error(`Error downloading ${format} report:`, err);
            setError(err.message || t('errors.downloadUnknown', { format }));
        } finally {
            setIsDownloading(false);
        }
    };


    return (
        <div className="container max-w p-4 space-y-6">

            {/* Chat Selection */}
            <div className="form-control w-full max-w-xs">
                <label className="label">
                    <span className="label-text text-base-content">{t('chatSelection.label')}</span>
                </label>
                <select
                    className={`select select-bordered text-base-content ${isLoadingChats ? 'opacity-50' : ''}`}
                    value={selectedChatId}
                    onChange={handleChatSelect}
                    disabled={isLoadingChats || chats.length === 0}
                >
                    <option value="" disabled className="text-base-content">
                        {isLoadingChats 
                            ? t('chatSelection.loading') 
                            : (chats.length === 0 
                                ? t('chatSelection.noChats') 
                                : t('chatSelection.placeholder'))}
                    </option>
                    {chats.map((chat) => (
                        <option key={chat.chat_id} value={chat.chat_id} className="text-base-content">
                            {chat.chat_name} ({chat.chat_id}) - {chat.source_name}
                        </option>
                    ))}
                </select>
                {isLoadingChats && <span className="loading loading-spinner loading-sm ml-2"></span>}
            </div>

            {/* Date Range Selection */}
            <div className="flex flex-wrap gap-4 items-center">
                <div className="form-control">
                    <label className="label">
                        <span className="label-text text-base-content">{t('dateRange.startDate')}</span>
                    </label>
                    <input
                        type="date"
                        className="input input-bordered text-base-content"
                        value={startDate}
                        onChange={(e) => setStartDate(e.target.value)}
                    />
                </div>
                <div className="form-control">
                    <label className="label">
                        <span className="label-text text-base-content">{t('dateRange.endDate')}</span>
                    </label>
                    <input
                        type="date"
                        className="input input-bordered text-base-content"
                        value={endDate}
                        onChange={(e) => setEndDate(e.target.value)}
                    />
                </div>
            </div>

            {/* Action Buttons */}
            <div className="flex flex-wrap gap-2 items-center">
                <button
                    className="btn btn-primary text-base-content"
                    onClick={generateReport}
                    disabled={!selectedChatId || isGeneratingReport || isDownloading}
                >
                    {isGeneratingReport ? (
                        <>
                            <span className="loading loading-spinner loading-xs"></span>
                            <span className="text-base-content">{t('buttons.generating')}</span>
                        </>
                    ) : (
                        <span className="text-base-content">{t('buttons.generateReport')}</span>
                    )}
                </button>
                <button
                    className="btn btn-secondary text-base-content"
                    onClick={() => downloadReport('csv')}
                    disabled={!selectedChatId || isGeneratingReport || isDownloading}
                >
                    {isDownloading ? (
                        <>
                            <span className="loading loading-spinner loading-xs"></span>
                            <span className="text-base-content">{t('buttons.downloading')}</span>
                        </>
                    ) : (
                        <span className="text-base-content">{t('buttons.downloadCsv')}</span>
                    )}
                </button>
                <button
                    className="btn btn-accent text-base-content"
                    onClick={() => downloadReport('xlsx')}
                    disabled={!selectedChatId || isGeneratingReport || isDownloading}
                >
                    {isDownloading ? (
                        <>
                            <span className="loading loading-spinner loading-xs"></span>
                            <span className="text-base-content">{t('buttons.downloading')}</span>
                        </>
                    ) : (
                        <span className="text-base-content">{t('buttons.downloadXlsx')}</span>
                    )}
                </button>
            </div>

            {/* Error Display */}
            {error && (
                <div role="alert" className="alert alert-error">
                    <svg xmlns="http://www.w3.org/2000/svg" className="stroke-current shrink-0 h-6 w-6" fill="none" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M10 14l2-2m0 0l2-2m-2 2l-2-2m2 2l2 2m7-2a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>
                    <span className="text-base-content">{t('errors.prefix')}: {error}</span>
                </div>
            )}

            {/* Report Table Display */}
            {reportData.length > 0 && reportHeaders.length > 0 && (
                <div className="mt-6">
                    <h2 className="text-xl font-semibold mb-2 text-base-content">{t('report.title')}</h2>
                    <div className="overflow-x-auto border border-base-300 rounded-lg">
                        <table className="table table-zebra w-full">
                            {/* head */}
                            <thead className="bg-base-200">
                                <tr>
                                    {reportHeaders.map((header) => (
                                        <th key={header} className="text-base-content">{header}</th>
                                    ))}
                                </tr>
                            </thead>
                            <tbody>
                                {/* body */}
                                {reportData.map((row, rowIndex) => (
                                    <tr key={rowIndex} className="hover">
                                        {reportHeaders.map((header) => (
                                            <td key={`${rowIndex}-${header}`} className="text-base-content">{row[header]}</td>
                                        ))}
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                </div>
            )}
            {isGeneratingReport && reportData.length === 0 && (
                <div className="text-center p-4 text-base-content">{t('report.generating')}</div>
            )}
        </div>
    );
}