"use client";

import { useState, useEffect } from 'react';
import { useTranslations } from 'next-intl';
import { Server, Cpu, CheckCircle, Clock, Activity, BarChart3 } from 'lucide-react';

// Type definitions based on the API
interface ModelLoadConfig {
  num_gpu_layers: number;
  gpu_split: number[];
}

interface ModelPerformanceMetrics {
  parallel_requests: number;
  ram_requirement: number;
  vram_requirement: number[];
  benchmark_results: Record<string, any>;
}

interface ModelConfig {
  alias: string | null;
  backend: string | null;
  quant: string | null;
  wrapper: string | null;
  context_length: number;
  api_name: string;
  load_options: ModelLoadConfig;
  performance_metrics?: ModelPerformanceMetrics;
}

interface GpuMetrics {
  index: number;
  name: string;
  util_percent: number;
  memory_used_mb: number;
  memory_total_mb: number;
  memory_percent: number;
}

interface MetricsSnapshot {
  cpu_percent: number;
  ram_percent: number;
  ram_used_mb: number;
  ram_total_mb: number;
  tasks_processed: number;
  gpus: GpuMetrics[];
  timestamp?: number; // This might be implicitly present or added by us
}

interface Worker {
  uid: string;
  name: string;
  connected: boolean;
  supported_models: ModelConfig[];
  backend_types: string[];
  hot_models: ModelConfig[];
  cold_models: ModelConfig[];
  first_seen?: string;
  last_seen?: string;
  metrics: MetricsSnapshot[];
}

// Helper component to display a bar graph
const BarGraph = ({
  data,
  height = 40,
  colorClass = "bg-primary",
  showValues = true,
  maxCapacity = null // Add new prop for maximum capacity
}: {
  data: number[],
  height?: number,
  colorClass?: string,
  showValues?: boolean,
  maxCapacity?: number | null
}) => {
  // Use provided maxCapacity if available, otherwise use max from data
  const maxValue = maxCapacity !== null ? maxCapacity : Math.max(...data, 0.1);

  return (
    <div className="flex items-end w-full h-full gap-px">
      {data.map((value, idx) => {
        const percentage = (value / maxValue) * 100;
        return (
          <div
            key={idx}
            className="flex flex-col items-center justify-end flex-1 h-full"
            title={`${value.toFixed(1)} / ${maxValue.toFixed(1)} (${percentage.toFixed(1)}%)`}
          >
            <div
              className={`w-full ${colorClass} rounded-sm`}
              style={{ height: `${Math.max(percentage, 2)}%` }}
            />
            {showValues && idx === data.length - 1 && (
              <span className="text-xs absolute -mt-4 right-0">
                {value.toFixed(1)}
              </span>
            )}
          </div>
        );
      })}
    </div>
  );
};

// Component for worker metrics visualization
const WorkerMetrics = ({ worker, entrypointUrl }: { worker: Worker, entrypointUrl: string }) => {
  const t = useTranslations('modelsPanel');
  const [showMetrics, setShowMetrics] = useState(false);
  const [metricsData, setMetricsData] = useState<MetricsSnapshot[]>(worker.metrics || []);
  const [error, setError] = useState<string | null>(null);
  const [isFirstLoad, setIsFirstLoad] = useState(true);
  const MAX_DATA_POINTS = 30; // Limit number of data points to prevent excessive memory usage

  // Fetch updated metrics when component is visible
  useEffect(() => {
    let intervalId: NodeJS.Timeout;

    const fetchMetrics = async () => {
      if (!showMetrics || !entrypointUrl) return;

      try {
        // Using the workers endpoint and filtering for our specific worker
        const response = await fetch(`${entrypointUrl}/info/get_workers`);

        if (!response.ok) {
          const errorData = await response.json();
          throw new Error(errorData.detail || t('fetchError'));
        }

        const data = await response.json();
        if (data && data.workers) {
          // Find our specific worker
          const updatedWorker = data.workers.find((w: Worker) => w.uid === worker.uid);
          if (updatedWorker && updatedWorker.metrics) {
            // Update metrics data with a limit on history length
            setMetricsData(prevData => {
              // Only add new metrics that aren't already in the data
              const newMetrics = [...updatedWorker.metrics];
              return newMetrics.slice(-MAX_DATA_POINTS);
            });

            if (isFirstLoad) {
              setIsFirstLoad(false);
            }

            setError(null);
          }
        }
      } catch (err) {
        console.error("Error fetching worker metrics:", err);
        setError(t('metricsError'));
      }
    };

    if (showMetrics) {
      // Fetch immediately when opened
      fetchMetrics();

      // Then set up interval for regular updates
      intervalId = setInterval(fetchMetrics, 2000);
    }

    return () => {
      if (intervalId) {
        clearInterval(intervalId);
      }
    };
  }, [showMetrics, entrypointUrl, worker.uid, t, isFirstLoad]);

  // If no metrics data available
  if (metricsData.length === 0) return null;

  // Extract data for graphs
  const tasksData = metricsData.map(m => m.tasks_processed);
  const cpuData = metricsData.map(m => m.cpu_percent);
  const ramData = metricsData.map(m => m.ram_percent);

  // Get latest metrics for display
  const latest = metricsData[metricsData.length - 1];

  return (
    <div className="mt-4">
      <button
        className="btn btn-sm btn-outline w-full flex justify-between items-center"
        onClick={() => setShowMetrics(!showMetrics)}
      >
        <div className="flex items-center gap-2">
          <Activity size={16} />
          {t('performanceMetrics')}
        </div>
        <span>{showMetrics ? '▲' : '▼'}</span>
      </button>

      {showMetrics && (
        <div className="mt-2 p-3 bg-base-200 rounded-lg relative min-h-[200px]">
          {isFirstLoad ? (
            <div className="absolute inset-0 flex justify-center items-center">
              <span className="loading loading-spinner loading-md"></span>
            </div>
          ) : (
            <>
              {error && (
                <div className="alert alert-error alert-sm mb-2">
                  <span className="text-xs">{error}</span>
                </div>
              )}

              <div className="transition-opacity duration-200">
                {/* Tasks processed graph */}
                <div className="mb-4">
                  <div className="flex justify-between items-center mb-1">
                    <span className="text-xs font-medium">{t('tasksProcessed')}</span>
                    <span className="text-xs">{latest.tasks_processed}</span>
                  </div>
                  <div className="h-30 bg-base-300 rounded p-1" style={{ minHeight: "40px" }}>
                    <BarGraph data={tasksData} colorClass="bg-success" />
                  </div>
                </div>

                {/* CPU & RAM usage */}
                <div className="grid grid-cols-2 gap-4 mb-4">
                  <div>
                    <div className="flex justify-between items-center mb-1">
                      <span className="text-xs font-medium">{t('cpuUsage')}</span>
                      <span className="text-xs">{latest.cpu_percent.toFixed(1)}%</span>
                    </div>
                    <div className="h-30 bg-base-300 rounded p-1" style={{ minHeight: "40px" }}>
                      <BarGraph data={cpuData} colorClass="bg-primary" showValues={false} maxCapacity={100} />
                    </div>
                  </div>

                  <div>
                    <div className="flex justify-between items-center mb-1">
                      <span className="text-xs font-medium">{t('ramUsage')}</span>
                      <span className="text-xs">
                        {latest.ram_percent.toFixed(1)}% ({(latest.ram_used_mb / 1024).toFixed(1)} GB / {(latest.ram_total_mb / 1024).toFixed(1)} GB)
                      </span>
                    </div>
                    <div className="h-30 bg-base-300 rounded p-1" style={{ minHeight: "40px" }}>
                      <BarGraph data={ramData} colorClass="bg-secondary" showValues={false} maxCapacity={100} />
                    </div>
                  </div>
                </div>

                {/* GPU metrics */}
                {latest.gpus.map((gpu, idx) => {
                  const gpuHistory = metricsData.map(m =>
                    m.gpus && m.gpus[idx] ? m.gpus[idx].util_percent : 0
                  );
                  const memoryHistory = metricsData.map(m =>
                    m.gpus && m.gpus[idx] ? m.gpus[idx].memory_percent : 0
                  );

                  return (
                    <div key={`gpu-${idx}`} className="mb-4">
                      <div className="flex justify-between items-center mb-1">
                        <span className="text-xs font-medium">
                          {gpu.name} (GPU {gpu.index})
                        </span>
                      </div>

                      <div className="grid grid-cols-2 gap-4">
                        <div>
                          <div className="flex justify-between items-center mb-1">
                            <span className="text-xs">{t('gpuUsage')}</span>
                            <span className="text-xs">{gpu.util_percent.toFixed(1)}%</span>
                          </div>
                          <div className="h-30 bg-base-300 rounded p-1" style={{ minHeight: "40px" }}>
                            <BarGraph data={gpuHistory} colorClass="bg-accent" showValues={false} maxCapacity={100} />
                          </div>
                        </div>

                        <div>
                          <div className="flex justify-between items-center mb-1">
                            <span className="text-xs">{t('vramUsage')}</span>
                            <span className="text-xs">
                              {gpu.memory_percent.toFixed(1)}% ({(gpu.memory_used_mb / 1024).toFixed(1)} GB / {(gpu.memory_total_mb / 1024).toFixed(1)} GB)
                            </span>
                          </div>
                          <div className="h-30 bg-base-300 rounded p-1" style={{ minHeight: "40px" }}>
                            <BarGraph data={memoryHistory} colorClass="bg-warning" showValues={false} maxCapacity={100} />
                          </div>
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            </>
          )}
        </div>
      )}
    </div>
  );
};

export default function ModelsPanel() {
  const t = useTranslations('modelsPanel');

  // State variables
  const [workers, setWorkers] = useState<Worker[]>([]);
  const [allowedLLMs, setAllowedLLMs] = useState<string[]>([]);
  const [allowedVLMs, setAllowedVLMs] = useState<string[]>([]);
  const [entrypointUrl, setEntrypointUrl] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [message, setMessage] = useState({ text: '', type: '' });

  // Fetch data when component mounts
  useEffect(() => {
    fetchLLMEntrypoint();
    fetchAllowedLLMs();
    fetchAllowedVLMs();
  }, []);

  // Fetch workers when entrypoint URL is available
  useEffect(() => {
    if (entrypointUrl) {
      fetchWorkers();
    }
  }, [entrypointUrl]);

  // API calls
  const fetchLLMEntrypoint = async () => {
    try {
      const response = await fetch('/api/settings/llm_endpoint');

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.error || t('fetchError'));
      }

      const data = await response.json();
      setEntrypointUrl(data.llm_endpoint);
    } catch (error :any) {
      setMessage({ text: error.message, type: 'error' });
    }
  };

  const fetchAllowedLLMs = async () => {
    try {
      const response = await fetch('/api/settings/llms');

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.error || t('fetchError'));
      }

      const data = await response.json();
      setAllowedLLMs(data.llms || []);
    } catch (error) {
      console.error('Error fetching allowed LLMs:', error);
    }
  };

  const fetchAllowedVLMs = async () => {
    try {
      const response = await fetch('/api/settings/vlms');

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.error || t('fetchError'));
      }

      const data = await response.json();
      setAllowedVLMs(data.vlms || []);
    } catch (error) {
      console.error('Error fetching allowed VLMs:', error);
    }
  };

  const updateAllowedLLMs = async (models: string[]) => {
    try {
      setIsLoading(true);
      const response = await fetch('/api/settings/llms', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ llms: models }),
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.error || t('updateError'));
      }

      setAllowedLLMs(models);
      setMessage({ text: t('llmUpdateSuccess'), type: 'success' });

      // Clear message after 3 seconds
      setTimeout(() => setMessage({ text: '', type: '' }), 3000);
    } catch (error :any) {
      setMessage({ text: error.message, type: 'error' });
    } finally {
      setIsLoading(false);
    }
  };

  const updateAllowedVLMs = async (models: string[]) => {
    try {
      setIsLoading(true);
      const response = await fetch('/api/settings/vlms', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ vlms: models }),
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.error || t('updateError'));
      }

      setAllowedVLMs(models);
      setMessage({ text: t('vlmUpdateSuccess'), type: 'success' });

      // Clear message after 3 seconds
      setTimeout(() => setMessage({ text: '', type: '' }), 3000);
    } catch (error :any) {
      setMessage({ text: error.message, type: 'error' });
    } finally {
      setIsLoading(false);
    }
  };

  const fetchWorkers = async () => {
    try {
      setIsLoading(true);
      // Fetch from the models endpoint at the entrypoint URL
      const response = await fetch(`${entrypointUrl}/info/get_workers`);

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || t('fetchError'));
      }

      const data = await response.json();
      setWorkers(data.workers || []);
    } catch (error) {
      console.error('Error fetching workers:', error);
      setMessage({ text: t('workersError'), type: 'error' });
    } finally {
      setIsLoading(false);
    }
  };

  const toggleLLM = (model: string) => {
    const newModels = allowedLLMs.includes(model)
      ? allowedLLMs.filter(m => m !== model)
      : [...allowedLLMs, model];

    updateAllowedLLMs(newModels);
  };

  const toggleVLM = (model: string) => {
    const newModels = allowedVLMs.includes(model)
      ? allowedVLMs.filter(m => m !== model)
      : [...allowedVLMs, model];

    updateAllowedVLMs(newModels);
  };


  // Get all unique model names across workers
  const getAllModels = () => {
    const allModels = new Set<string>();

    workers.forEach(worker => {
      [...(worker.hot_models || []), ...(worker.cold_models || [])].forEach(model => {
        if (model && model.alias) {
          allModels.add(model.alias);
        }
      });
    });

    return Array.from(allModels);
  };

  return (
    <div className="w-full text-base-content">
      {message.text && (
        <div className={`alert ${message.type === 'success' ? 'alert-success' : 'alert-error'} mb-4`}>
          <span>{message.text}</span>
        </div>
      )}

      {isLoading && (
        <div className="flex justify-center my-4">
          <span className="loading loading-spinner loading-lg text-primary"></span>
        </div>
      )}

      {/* Workers section */}
      <div className="card bg-base-100 shadow-lg mb-6">
        <div className="card-body">
          <div className="flex items-center gap-2 mb-4">
            <Cpu size={20} className="text-primary" />
            <h3 className="text-lg font-medium">{t('workersTitle')}</h3>
          </div>

          {!isLoading && workers.length === 0 ? (
            <div className="alert alert-info">
              <span>{t('noWorkersFound')}</span>
            </div>
          ) : (
            <div className="grid grid-cols-1 gap-4">
              {workers.map((worker) => (
                <div key={worker.uid} className="card bg-base-200">
                  <div className="card-body p-4">
                    <div className="flex justify-between items-center">
                      <h4 className="card-title text-base">
                        {worker.name}
                        <span className={`badge ${worker.connected ? 'badge-success' : 'badge-error'} ml-2`}>
                          {worker.connected ? t('connected') : t('disconnected')}
                        </span>
                      </h4>
                      <span className="badge badge-outline">{worker.uid.slice(0, 8)}</span>
                    </div>

                    {/* Add the metrics visualization component here */}
                    {worker.metrics && worker.metrics.length > 0 && (
                      <WorkerMetrics worker={worker} entrypointUrl={entrypointUrl} />
                    )}

                    {/* Hot Models Section */}
                    <div className="divider my-1">{t('hotModels')}</div>
                    {worker.hot_models && worker.hot_models.length > 0 ? (
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
                        {worker.hot_models.map((model, idx) => (
                          <div key={`${worker.uid}-hot-${idx}`} className="card bg-accent text-accent-content shadow-sm">
                            <div className="card-body p-3">
                              <div className="flex items-center gap-2">
                                <CheckCircle size={16} />
                                <h5 className="card-title text-sm">{model.alias || model.api_name}</h5>
                              </div>
                              <div className="grid grid-cols-2 gap-x-4 gap-y-1 text-xs mt-2">
                                <div><span className="font-semibold">{t('apiName')}:</span> {model.api_name}</div>
                                <div><span className="font-semibold">{t('backend')}:</span> {model.backend || 'N/A'}</div>
                                <div><span className="font-semibold">{t('quant')}:</span> {model.quant || 'N/A'}</div>
                                <div><span className="font-semibold">{t('wrapper')}:</span> {model.wrapper || 'N/A'}</div>
                                <div><span className="font-semibold">{t('contextLength')}:</span> {model.context_length}</div>
                                <div><span className="font-semibold">{t('parallelRequests')}:</span> {model.performance_metrics?.parallel_requests || 'N/A'}</div>
                              </div>
                            </div>
                          </div>
                        ))}
                      </div>
                    ) : (
                      <p className="text-sm opacity-70">{t('noHotModels')}</p>
                    )}

                    {/* Cold Models Section */}
                    <div className="divider my-1">{t('coldModels')}</div>
                    {worker.cold_models && worker.cold_models.length > 0 ? (
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
                        {worker.cold_models.map((model, idx) => (
                          <div key={`${worker.uid}-cold-${idx}`} className="card bg-base-100 border border-neutral-content shadow-sm">
                            <div className="card-body p-3">
                              <div className="flex items-center gap-2">
                                <Clock size={16} />
                                <h5 className="card-title text-sm">{model.alias || model.api_name}</h5>
                              </div>
                              <div className="grid grid-cols-2 gap-x-4 gap-y-1 text-xs mt-2">
                                <div><span className="font-semibold">{t('apiName')}:</span> {model.api_name}</div>
                                <div><span className="font-semibold">{t('backend')}:</span> {model.backend || 'N/A'}</div>
                                <div><span className="font-semibold">{t('quant')}:</span> {model.quant || 'N/A'}</div>
                                <div><span className="font-semibold">{t('wrapper')}:</span> {model.wrapper || 'N/A'}</div>
                                <div><span className="font-semibold">{t('contextLength')}:</span> {model.context_length}</div>
                                <div><span className="font-semibold">{t('parallelRequests')}:</span> {model.performance_metrics?.parallel_requests || 'N/A'}</div>
                              </div>
                            </div>
                          </div>
                        ))}
                      </div>
                    ) : (
                      <p className="text-sm opacity-70">{t('noColdModels')}</p>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Model Selection section */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* LLM Selection */}
        <div className="card bg-base-100 shadow-lg">
          <div className="card-body">
            <div className="flex items-center gap-2 mb-4">
              <Server size={20} className="text-primary" />
              <h3 className="text-lg font-medium">{t('llmSelectionTitle')}</h3>
            </div>

            <div className="mb-4">
              <h4 className="font-medium mb-2">{t('selectedLLMs')}</h4>
              <div className="flex flex-wrap gap-2 mb-4 min-h-16">
                {allowedLLMs.length > 0 ? (
                  allowedLLMs.map((model, idx) => (
                    <span
                      key={`selected-llm-${idx}`}
                      className="badge badge-primary badge-lg cursor-pointer"
                      onClick={() => toggleLLM(model)}
                    >
                      {model} ✕
                    </span>
                  ))
                ) : (
                  <span className="text-sm opacity-70">{t('noModelsSelected')}</span>
                )}
              </div>

              <h4 className="font-medium mb-2">{t('availableLLMs')}</h4>
              <div className="flex flex-wrap gap-2 min-h-16">
                {getAllModels()
                  .filter(model => !allowedLLMs.includes(model))
                  .map((model, idx) => (
                    <span
                      key={`available-llm-${idx}`}
                      className="badge badge-outline badge-lg cursor-pointer hover:bg-primary hover:text-primary-content"
                      onClick={() => toggleLLM(model)}
                    >
                      {model} +
                    </span>
                  ))
                }
                {getAllModels().filter(model => !allowedLLMs.includes(model)).length === 0 && (
                  <span className="text-sm opacity-70">{t('noAvailableModels')}</span>
                )}
              </div>
            </div>
          </div>
        </div>

        {/* VLM Selection */}
        <div className="card bg-base-100 shadow-lg">
          <div className="card-body">
            <div className="flex items-center gap-2 mb-4">
              <Server size={20} className="text-secondary" />
              <h3 className="text-lg font-medium">{t('vlmSelectionTitle')}</h3>
            </div>

            <div className="mb-4">
              <h4 className="font-medium mb-2">{t('selectedVLMs')}</h4>
              <div className="flex flex-wrap gap-2 mb-4 min-h-16">
                {allowedVLMs.length > 0 ? (
                  allowedVLMs.map((model, idx) => (
                    <span
                      key={`selected-vlm-${idx}`}
                      className="badge badge-secondary badge-lg cursor-pointer"
                      onClick={() => toggleVLM(model)}
                    >
                      {model} ✕
                    </span>
                  ))
                ) : (
                  <span className="text-sm opacity-70">{t('noModelsSelected')}</span>
                )}
              </div>

              <h4 className="font-medium mb-2">{t('availableVLMs')}</h4>
              <div className="flex flex-wrap gap-2 min-h-16">
                {getAllModels()
                  .filter(model => !allowedVLMs.includes(model))
                  .map((model, idx) => (
                    <span
                      key={`available-vlm-${idx}`}
                      className="badge badge-outline badge-lg cursor-pointer hover:bg-secondary hover:text-secondary-content"
                      onClick={() => toggleVLM(model)}
                    >
                      {model} +
                    </span>
                  ))
                }
                {getAllModels().filter(model => !allowedVLMs.includes(model)).length === 0 && (
                  <span className="text-sm opacity-70">{t('noAvailableModels')}</span>
                )}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}