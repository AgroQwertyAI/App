"use client";

import { useState, useEffect } from 'react';
import { useTranslations } from 'next-intl';
import { AlertCircle } from 'lucide-react';
import {
    PieChart, Pie, Cell,
    BarChart, Bar,
    LineChart, Line,
    XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer
} from 'recharts';

// Define interfaces for chart data structures
interface ChartDataset {
    label: string;
    data: number[];
}

interface ChartJsData {
    labels: string[];
    datasets: ChartDataset[];
}

interface ChartResponse {
    data?: ChartJsData;
    datasets?: ChartDataset[];
    labels?: string[];
}

interface DataItem {
    label?: string;
    name?: string;
    date?: string;
    value?: number;
    data?: number;
    series?: string;
    operation?: string;
    [key: string]: any;
}

interface DashboardState {
    operations: ChartResponse | DataItem[] | null;
    cultures: ChartResponse | DataItem[] | null;
    dailyProgress: ChartResponse | DataItem[] | null;
    totalProgress: ChartResponse | DataItem[] | null;
}

interface TransformedPieData {
    name: string;
    value: number;
}

interface TransformedBarData {
    name: string;
    value: number;
}

interface TransformedLineData {
    name: string;
    [key: string]: number | string;
}

interface DebugInfo {
    operations?: ChartResponse | DataItem[] | null;
    cultures?: ChartResponse | DataItem[] | null;
    dailyProgress?: ChartResponse | DataItem[] | null;
    totalProgress?: ChartResponse | DataItem[] | null;
}

// Custom colors for charts
const COLORS = ['#0088FE', '#00C49F', '#FFBB28', '#FF8042', '#8884d8', '#82ca9d', '#ffc658', '#8dd1e1'];

export default function DashboardPanel() {
    const dashT = useTranslations('dashboard');
    const [dashboardChatId, setDashboardChatId] = useState<string>('');
    const [chartData, setChartData] = useState<DashboardState>({
        operations: null,
        cultures: null,
        dailyProgress: null,
        totalProgress: null
    });
    const [isLoading, setIsLoading] = useState<boolean>(false);
    const [error, setError] = useState<string>('');
    const [debugInfo, setDebugInfo] = useState<DebugInfo | null>(null);

    useEffect(() => {
        fetchDashboardChatId();
    }, []);

    const fetchDashboardChatId = async () => {
        try {
            const response = await fetch('/api/settings/dashboard_chat');
            if (response.ok) {
                const data = await response.json();
                setDashboardChatId(data.dashboard_chat_id);

                if (data.dashboard_chat_id) {
                    generateCharts(data.dashboard_chat_id);
                }
            }
        } catch (error) {
            console.error("Error fetching dashboard chat ID:", error);
            setError(dashT('errors.fetchFailed') || 'Failed to fetch settings');
        }
    };

    const generateCharts = async (chatId: string) => {
        if (!chatId) return;

        setIsLoading(true);
        setError('');

        try {
            // Generate charts sequentially instead of in parallel to avoid race conditions
            await generateOperationsChart(chatId);
            await generateCulturesChart(chatId);
            await generateDailyProgressChart(chatId);
            await generateTotalProgressChart(chatId);
        } catch (error) {
            console.error("Error generating charts:", error);
            setError(dashT('errors.chartsLoadFailed') || 'Failed to load charts');
        } finally {
            setIsLoading(false);
        }
    };

    const generateOperationsChart = async (chatId: string) => {
        const now = new Date();
        const startDate = new Date(now.getFullYear(), now.getMonth(), 1); // Start of current month

        const response = await fetch(`/api/charts/${chatId}`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                time: {
                    start: startDate.toISOString(),
                    end: now.toISOString(),
                    format: 'day'
                },
                chart_definition: {
                    chart_type: 'pie',
                    label_field: 'Операция',
                    value_aggregation: 'sum',
                    value_field: 'За день, га',
                    title: dashT('charts.operationsByArea') || 'Operations by Area'
                }
            }),
        });

        if (!response.ok) {
            throw new Error('Failed to generate operations chart');
        }

        const data = await response.json();
        console.log("Operations chart data:", data);
        setDebugInfo(prevDebug => ({ ...prevDebug, operations: data }));
        setChartData(prev => ({ ...prev, operations: data }));
    };

    const generateCulturesChart = async (chatId: string) => {
        const now = new Date();
        const startDate = new Date(now.getFullYear(), now.getMonth(), 1); // Start of current month

        const response = await fetch(`/api/charts/${chatId}`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                time: {
                    start: startDate.toISOString(),
                    end: now.toISOString(),
                    format: 'day'
                },
                chart_definition: {
                    chart_type: 'doughnut',
                    label_field: 'Культура',
                    value_aggregation: 'sum',
                    value_field: 'За день, га',
                    title: dashT('charts.culturesByArea') || 'Cultures by Area'
                }
            }),
        });

        if (!response.ok) {
            throw new Error('Failed to generate cultures chart');
        }

        const data = await response.json();
        console.log("Cultures chart data:", data);
        setChartData(prev => ({ ...prev, cultures: data }));
    };

    const generateDailyProgressChart = async (chatId: string) => {
        const now = new Date();
        const startDate = new Date(now.getFullYear(), now.getMonth(), 1); // Start of current month

        const response = await fetch(`/api/charts/${chatId}`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                time: {
                    start: startDate.toISOString(),
                    end: now.toISOString(),
                    format: 'day'
                },
                chart_definition: {
                    chart_type: 'bar',
                    label_field: 'Дата',
                    value_aggregation: 'sum',
                    value_field: 'За день, га',
                    title: dashT('charts.dailyProgress') || 'Daily Progress (ha)'
                }
            }),
        });

        if (!response.ok) {
            throw new Error('Failed to generate daily progress chart');
        }

        const data = await response.json();
        console.log("Daily progress chart data:", data);
        setChartData(prev => ({ ...prev, dailyProgress: data }));
    };

    const generateTotalProgressChart = async (chatId: string) => {
        const now = new Date();
        const startDate = new Date(now.getFullYear(), now.getMonth(), 1); // Start of current month

        const response = await fetch(`/api/charts/${chatId}`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                time: {
                    start: startDate.toISOString(),
                    end: now.toISOString(),
                    format: 'day'
                },
                chart_definition: {
                    chart_type: 'line',
                    label_field: 'Операция',
                    value_aggregation: 'sum',
                    value_field: 'С начала операции, га',
                    series_field: 'Операция',
                    title: dashT('charts.totalProgress') || 'Total Progress by Operation (ha)'
                }
            }),
        });

        if (!response.ok) {
            throw new Error('Failed to generate total progress chart');
        }

        const data = await response.json();
        console.log("Total progress chart data:", data);
        setChartData(prev => ({ ...prev, totalProgress: data }));
    };

    // Transform Chart.js data to Recharts format for pie/doughnut charts
    const transformPieData = (chartData: ChartResponse | DataItem[] | null): TransformedPieData[] => {
        try {
            if (!chartData) return [];

            // Check for different possible data structures
            if (chartData && 'data' in chartData && chartData.data?.labels) {
                // Original Chart.js format
                return chartData.data.labels.map((label, index) => ({
                    name: label,
                    value: chartData.data?.datasets[0].data[index] || 0
                }));
            } else if (Array.isArray(chartData)) {
                // Direct array of data
                return chartData.map(item => ({
                    name: item.label || item.name || '',
                    value: item.value || item.data || 0
                }));
            } else if ('datasets' in chartData && chartData.labels) {
                // Another possible format
                return chartData.labels.map((label, index) => ({
                    name: label,
                    value: chartData.datasets?.[0].data[index] || 0
                }));
            }

            console.error("Unknown pie chart data format:", chartData);
            return [];
        } catch (error) {
            console.error("Error transforming pie data:", error, chartData);
            return [];
        }
    };

    // Transform Chart.js data to Recharts format for bar chart
    const transformBarData = (chartData: ChartResponse | DataItem[] | null): TransformedBarData[] => {
        try {
            if (!chartData) return [];

            // Check for different possible data structures
            if (chartData && 'data' in chartData && chartData.data?.labels) {
                // Original Chart.js format
                return chartData.data.labels.map((label, index) => ({
                    name: label,
                    value: chartData.data?.datasets[0].data[index] || 0
                }));
            } else if (Array.isArray(chartData)) {
                // Direct array of data
                return chartData.map(item => ({
                    name: item.label || item.name || item.date || '',
                    value: item.value || item.data || 0
                }));
            } else if ('datasets' in chartData && chartData.labels) {
                // Another possible format
                return chartData.labels.map((label, index) => ({
                    name: label,
                    value: chartData.datasets?.[0].data[index] || 0
                }));
            }

            console.error("Unknown bar chart data format:", chartData);
            return [];
        } catch (error) {
            console.error("Error transforming bar data:", error, chartData);
            return [];
        }
    };

    // Transform Chart.js data to Recharts format for line chart
    const transformLineData = (chartData: ChartResponse | DataItem[] | null): TransformedLineData[] => {
        try {
            if (!chartData) return [];

            // Check for different possible data structures
            if (chartData && 'data' in chartData && chartData.data?.labels) {
                // Original Chart.js format
                const { labels, datasets } = chartData.data;

                return labels.map((label, i) => {
                    const dataPoint: TransformedLineData = { name: label };

                    datasets.forEach((dataset) => {
                        dataPoint[dataset.label] = dataset.data[i];
                    });

                    return dataPoint;
                });
            } else if (Array.isArray(chartData)) {
                // If data is already in the right format or needs regrouping
                // Check if it's grouped by date or series
                const firstItem = chartData[0];

                if (firstItem && (firstItem.date || firstItem.name)) {
                    // Group by date/name
                    const groupedData: Record<string, TransformedLineData> = {};

                    chartData.forEach(item => {
                        const key = item.date || item.name || '';
                        const series = item.series || item.operation || 'Value';

                        if (!groupedData[key]) {
                            groupedData[key] = { name: key };
                        }

                        groupedData[key][series] = item.value || item.data || 0;
                    });

                    return Object.values(groupedData);
                }

                return chartData as TransformedLineData[];
            } else if ('datasets' in chartData && chartData.labels) {
                // Another possible format
                const { labels, datasets } = chartData;

                return labels.map((label, i) => {
                    const dataPoint: TransformedLineData = { name: label };

                    datasets?.forEach((dataset) => {
                        dataPoint[dataset.label] = dataset.data[i];
                    });

                    return dataPoint;
                });
            }

            console.error("Unknown line chart data format:", chartData);
            return [];
        } catch (error) {
            console.error("Error transforming line data:", error, chartData);
            return [];
        }
    };

    // Rendering for pie chart (operations and cultures)
    const renderPieChart = (data: ChartResponse | DataItem[] | null, isDonut = false) => {
        if (!data) return null;

        const transformedData = transformPieData(data);

        if (transformedData.length === 0) {
            return <div className="p-4 text-center text-gray-500">No data available</div>;
        }

        return (
            <ResponsiveContainer width="100%" height={300}>
                <PieChart>
                    <Pie
                        data={transformedData}
                        cx="50%"
                        cy="50%"
                        labelLine={true}
                        label={({ name, percent }) => `${name}: ${(percent * 100).toFixed(0)}%`}
                        outerRadius={isDonut ? 80 : 100}
                        innerRadius={isDonut ? 40 : 0}
                        fill="#8884d8"
                        dataKey="value"
                    >
                        {transformedData.map((entry, index) => (
                            <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                        ))}
                    </Pie>
                    <Tooltip
                        formatter={(value) => [`${value} ha`, '']}
                    />
                    <Legend />
                </PieChart>
            </ResponsiveContainer>
        );
    };

    // Rendering for bar chart (daily progress)
    const renderBarChart = (data: ChartResponse | DataItem[] | null) => {
        if (!data) return null;

        const transformedData = transformBarData(data);

        if (transformedData.length === 0) {
            return <div className="p-4 text-center text-gray-500">No data available</div>;
        }

        return (
            <ResponsiveContainer width="100%" height={300}>
                <BarChart
                    data={transformedData}
                    margin={{ top: 20, right: 30, left: 20, bottom: 5 }}
                >
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="name" />
                    <YAxis />
                    <Tooltip formatter={(value) => [`${value} ha`, '']} />
                    <Legend />
                    <Bar dataKey="value" name="Hectares" fill="#8884d8" />
                </BarChart>
            </ResponsiveContainer>
        );
    };

    // Rendering for line chart (total progress)
    const renderLineChart = (data: ChartResponse | DataItem[] | null) => {
        if (!data) return null;

        const transformedData = transformLineData(data);

        if (transformedData.length === 0) {
            return <div className="p-4 text-center text-gray-500">No data available</div>;
        }

        // Find all data keys excluding 'name'
        const dataKeys = Object.keys(transformedData[0] || {}).filter(key => key !== 'name');

        return (
            <ResponsiveContainer width="100%" height={300}>
                <LineChart
                    data={transformedData}
                    margin={{ top: 20, right: 30, left: 20, bottom: 5 }}
                >
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="name" />
                    <YAxis />
                    <Tooltip formatter={(value) => [`${value} ha`, '']} />
                    <Legend />
                    {dataKeys.map((key, index) => (
                        <Line
                            key={key}
                            type="monotone"
                            dataKey={key}
                            stroke={COLORS[index % COLORS.length]}
                            activeDot={{ r: 8 }}
                        />
                    ))}
                </LineChart>
            </ResponsiveContainer>
        );
    };

    return (
        <>
            {/* Stats cards 
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 my-6">
                <div className="stats shadow bg-primary text-primary-content">
                    <div className="stat">
                        <div className="stat-title">{dashT('stats.tasksProcessedToday')}</div>
                        <div className="stat-value">89</div>
                        <div className="stat-desc">{dashT('stats.moreFromYesterday')}</div>
                    </div>
                </div>
                <div className="stats shadow bg-accent text-accent-content">
                    <div className="stat">
                        <div className="stat-title">{dashT('stats.processingQueue')}</div>
                        <div className="stat-value">12</div>
                        <div className="stat-desc">{dashT('stats.awaitingProcessing')}</div>
                    </div>
                </div>
                <div className="stats shadow bg-secondary text-secondary-content">
                    <div className="stat">
                        <div className="stat-title">{dashT('stats.apiCallsToday')}</div>
                        <div className="stat-value">324</div>
                        <div className="stat-desc">{dashT('stats.llmCalls')}</div>
                    </div>
                </div>
                <div className="stats shadow bg-neutral text-neutral-content">
                    <div className="stat">
                        <div className="stat-title">{dashT('stats.successRate')}</div>
                        <div className="stat-value">98.5%</div>
                        <div className="stat-desc">{dashT('stats.increaseRate')}</div>
                    </div>
                </div>
            </div>
            */}

            {/* Charts section */}
            <div className="mb-6">

                {!dashboardChatId && (
                    <div className="alert alert-info">
                        <div className="flex items-center">
                            <AlertCircle size={18} />
                            <span className="ml-2">{dashT('charts.noChatSelected') || 'No chat selected for dashboard charts. Please configure it in settings.'}</span>
                        </div>
                    </div>
                )}

                {isLoading && (
                    <div className="flex justify-center items-center p-8">
                        <div className="loading loading-spinner loading-lg"></div>
                    </div>
                )}

                {error && (
                    <div className="alert alert-error">
                        <div className="flex items-center">
                            <AlertCircle size={18} />
                            <span className="ml-2">{error}</span>
                        </div>
                    </div>
                )}

                {dashboardChatId && !isLoading && !error && (
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                        <div className="card bg-base-100 shadow-lg">
                            <div className="card-body">
                                <h4 className="card-title text-accent">
                                    {dashT('charts.operationsByArea') || 'Operations by Area'}
                                </h4>
                                {renderPieChart(chartData.operations)}
                            </div>
                        </div>

                        <div className="card bg-base-100 shadow-lg">
                            <div className="card-body">
                                <h4 className="card-title text-accent">
                                    {dashT('charts.culturesByArea') || 'Cultures by Area'}
                                </h4>
                                {renderPieChart(chartData.cultures, true)}
                            </div>
                        </div>

                        <div className="card bg-base-100 shadow-lg">
                            <div className="card-body">
                                <h4 className="card-title text-accent">
                                    {dashT('charts.dailyProgress') || 'Daily Progress (ha)'}
                                </h4>
                                {renderBarChart(chartData.dailyProgress)}
                            </div>
                        </div>

                        <div className="card bg-base-100 shadow-lg">
                            <div className="card-body">
                                <h4 className="card-title text-accent">
                                    {dashT('charts.totalProgress') || 'Total Progress by Operation (ha)'}
                                </h4>
                                {renderLineChart(chartData.totalProgress)}
                            </div>
                        </div>
                    </div>
                )}
            </div>
        </>
    );
}