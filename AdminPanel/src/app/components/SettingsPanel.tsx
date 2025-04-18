"use client";

import { useState, useEffect } from 'react';
import { useTranslations } from 'next-intl';
import { Server, QrCode, BarChart2, Calendar, Cloud, Trash2, Edit, Plus, Save, X } from 'lucide-react';
import QRCode from 'react-qr-code';
import { Setting, SendingReportTo, YandexDiskConfig, GoogleDriveConfig } from '../types/settings';

interface Chat {
  chat_id: string;
  chat_name: string;
  source_name: string;
  setting_id?: number;
}

export default function SettingsPanel() {
  const settingsT = useTranslations('settingsPanel');
  const [entrypointUrl, setEntrypointUrl] = useState('');
  const [whatsappQrCode, setWhatsappQrCode] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [message, setMessage] = useState({ text: '', type: '' });

  // Dashboard chat settings
  const [dashboardChatId, setDashboardChatId] = useState('');
  const [sources, setSources] = useState<string[]>([]);
  const [selectedSource, setSelectedSource] = useState('');
  const [chats, setChats] = useState<Chat[]>([]);
  const [loadingSources, setLoadingSources] = useState(false);
  const [loadingChats, setLoadingChats] = useState(false);

  // Report Schedule Settings
  const [reportSettings, setReportSettings] = useState<Setting[]>([]);
  const [loadingSettings, setLoadingSettings] = useState(false);
  const [showDeletedSettings, setShowDeletedSettings] = useState(false);
  const [editingSetting, setEditingSetting] = useState<Partial<Setting> | null>(null);
  const [isAddingNew, setIsAddingNew] = useState(false);

  // Cloud Storage Settings
  const [yandexConfig, setYandexConfig] = useState<YandexDiskConfig | null>(null);
  const [googleDriveConfig, setGoogleDriveConfig] = useState<GoogleDriveConfig | null>(null);
  const [editingYandexConfig, setEditingYandexConfig] = useState<YandexDiskConfig | null>(null);
  const [editingGoogleConfig, setEditingGoogleConfig] = useState<GoogleDriveConfig | null>(null);
  const [loadingCloud, setLoadingCloud] = useState(false);

  // Add new state for selected chats in settings
  const [availableChats, setAvailableChats] = useState<Chat[]>([]);
  const [selectedChats, setSelectedChats] = useState<string[]>([]);
  const [loadingAvailableChats, setLoadingAvailableChats] = useState(false);

  useEffect(() => {
    fetchLLMEntrypoint();
    fetchWhatsappQrCode();
    fetchDashboardChatId();
    fetchSources();
    fetchReportSettings();
    fetchCloudConfig();

    // Set up polling interval (every second)
    const intervalId = setInterval(() => {
      fetchWhatsappQrCode();
    }, 1000);

    // Clean up interval on unmount
    return () => clearInterval(intervalId);
  }, []);

  useEffect(() => {
    if (selectedSource) {
      fetchChats(selectedSource);
    }
  }, [selectedSource]);

  const fetchLLMEntrypoint = async () => {
    try {
      setIsLoading(true);
      const response = await fetch('/api/settings/llm_endpoint');

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.error || settingsT('fetchError'));
      }

      const data = await response.json();
      setEntrypointUrl(data.llm_endpoint);
    } catch (error :any) {
      setMessage({ text: error.message, type: 'error' });
    } finally {
      setIsLoading(false);
    }
  };

  const fetchWhatsappQrCode = async () => {
    try {
      const response = await fetch('/api/settings/whatsapp_qr');

      if (!response.ok) {
        // Don't show error if QR code just doesn't exist yet
        if (response.status !== 404) {
          const error = await response.json();
          throw new Error(error.message || settingsT('qrCodeFetchError'));
        }
        return;
      }

      const data = await response.json();
      if (data.success && data.data?.qr_code) {
        setWhatsappQrCode(data.data.qr_code);
      }
    } catch (error) {
      console.error("Error fetching WhatsApp QR code:", error);
    }
  };

  const handleSubmit = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();

    try {
      setIsLoading(true);
      const response = await fetch('/api/settings/llm_endpoint', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ url: entrypointUrl }),
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.error || settingsT('updateError'));
      }

      setMessage({ text: settingsT('updateSuccess'), type: 'success' });
    } catch (error :any) {
      setMessage({ text: error.message, type: 'error' });
    } finally {
      setIsLoading(false);
    }
  };

  // New functions for dashboard chat settings
  const fetchDashboardChatId = async () => {
    try {
      const response = await fetch('/api/settings/dashboard_chat');
      if (response.ok) {
        const data = await response.json();
        setDashboardChatId(data.dashboard_chat_id);
      }
    } catch (error :any) {
      console.error("Error fetching dashboard chat ID:", error);
    }
  };

  const fetchSources = async () => {
    try {
      setLoadingSources(true);

      const data = ["whatsapp", "telegram"];
      setSources(data);
      if (!selectedSource) {
        setSelectedSource(data[0]);
      }
    } catch (error) {
      console.error("Error fetching sources:", error);
    } finally {
      setLoadingSources(false);
    }
  };

  const fetchChats = async (sourceName: string) => {
    if (!sourceName) return;

    try {
      setLoadingChats(true);
      const response = await fetch(`/api/chats?source_name=${encodeURIComponent(sourceName)}`);
      if (response.ok) {
        const data = await response.json();
        setChats(data.chats || []);
      }
    } catch (error) {
      console.error("Error fetching chats:", error);
    } finally {
      setLoadingChats(false);
    }
  };

  const saveDashboardChatId = async () => {
    try {
      setIsLoading(true);
      const response = await fetch('/api/settings/dashboard_chat', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ dashboard_chat_id: dashboardChatId }),
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.error || settingsT('updateError'));
      }

      setMessage({ text: settingsT('dashboardChatUpdateSuccess') || 'Dashboard chat updated successfully', type: 'success' });
    } catch (error :any) {
      setMessage({ text: error.message, type: 'error' });
    } finally {
      setIsLoading(false);
    }
  };

  // Report Setting Functions
  const fetchReportSettings = async () => {
    try {
      setLoadingSettings(true);
      const response = await fetch(`/api/settings?show_deleted=${showDeletedSettings}`);

      if (!response.ok) {
        throw new Error('Failed to fetch report settings');
      }

      const data = await response.json();
      setReportSettings(data);
    } catch (error :any) {
      console.error("Error fetching report settings:", error);
      setMessage({ text: error.message, type: 'error' });
    } finally {
      setLoadingSettings(false);
    }
  };

  const handleDeleteSetting = async (id: number) => {
    try {
      setIsLoading(true);
      const response = await fetch(`/api/setting/${id}`, {
        method: 'DELETE',
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.error || 'Failed to delete setting');
      }

      setMessage({ text: 'Setting deleted successfully', type: 'success' });
      fetchReportSettings(); // Refresh the list
    } catch (error :any) {
      setMessage({ text: error.message, type: 'error' });
    } finally {
      setIsLoading(false);
    }
  };

  const updateSettingChats = async (settingId :any) => {
    if (!settingId) return;

    // Update each selected chat to associate it with this setting
    for (const chatId of selectedChats) {
      try {
        await fetch(`/api/chats/${chatId}`, {
          method: 'PATCH',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({ setting_id: settingId }),
        });
      } catch (error) {
        console.error(`Error updating chat ${chatId}:`, error);
      }
    }

    // Remove setting association from previously selected but now unselected chats
    const previouslySelected = availableChats
      .filter(chat => chat.setting_id === settingId)
      .map(chat => chat.chat_id);

    for (const chatId of previouslySelected) {
      if (!selectedChats.includes(chatId)) {
        try {
          await fetch(`/api/chats/${chatId}`, {
            method: 'PATCH',
            headers: {
              'Content-Type': 'application/json',
            },
            body: JSON.stringify({ setting_id: null }),
          });
        } catch (error) {
          console.error(`Error removing setting from chat ${chatId}:`, error);
        }
      }
    }
  };

  const handleSaveSetting = async () => {
    if (!editingSetting) return;

    try {
      setIsLoading(true);
      const method = isAddingNew ? 'POST' : 'PUT';
      const url = isAddingNew
        ? '/api/setting'
        : `/api/setting/${editingSetting.setting_id}`;

      const response = await fetch(url, {
        method,
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(editingSetting),
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.error || 'Failed to save setting');
      }

      const result = await response.json();
      const settingId = result.setting_id || editingSetting.setting_id;

      // Update chat associations
      await updateSettingChats(settingId);

      setMessage({
        text: isAddingNew ? 'Setting created successfully' : 'Setting updated successfully',
        type: 'success'
      });
      setEditingSetting(null);
      setIsAddingNew(false);
      fetchReportSettings(); // Refresh the list
    } catch (error :any) {
      setMessage({ text: error.message, type: 'error' });
    } finally {
      setIsLoading(false);
    }
  };

  const addPhoneNumber = () => {
    if (!editingSetting) return;

    setEditingSetting({
      ...editingSetting,
      send_to: [
        ...(editingSetting.send_to || []),
        { phone_number: '', messenger: 'whatsapp' }  // Changed from platform to messenger
      ]
    });
  };

  const removePhoneNumber = (index: number) => {
    if (!editingSetting) return;

    const newSendTo = [...(editingSetting.send_to || [])];
    newSendTo.splice(index, 1);

    setEditingSetting({
      ...editingSetting,
      send_to: newSendTo
    });
  };

  const updatePhoneNumber = (index: number, field: keyof SendingReportTo, value: string) => {
    if (!editingSetting) return;

    const newSendTo = [...(editingSetting.send_to || [])];
    newSendTo[index] = {
      ...newSendTo[index],
      [field]: value
    };

    setEditingSetting({
      ...editingSetting,
      send_to: newSendTo
    });
  };

  // Cloud Config Functions
  const fetchCloudConfig = async () => {
    setLoadingCloud(true);

    try {
      // Fetch Yandex Disk Config
      const yandexResponse = await fetch('/api/cloud-config/yandex-disk');
      if (yandexResponse.ok) {
        const data = await yandexResponse.json();
        setYandexConfig(data);
      }
    } catch (error) {
      console.error("Error fetching Yandex Disk config:", error);
    }

    try {
      // Fetch Google Drive Config
      const googleResponse = await fetch('/api/cloud-config/google-drive');
      if (googleResponse.ok) {
        const data = await googleResponse.json();
        setGoogleDriveConfig(data);
      }
    } catch (error) {
      console.error("Error fetching Google Drive config:", error);
    } finally {
      setLoadingCloud(false);
    }
  };

  const saveYandexConfig = async () => {
    if (!editingYandexConfig) return;

    try {
      setIsLoading(true);
      const response = await fetch('/api/cloud-config/yandex-disk', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(editingYandexConfig),
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.error || 'Failed to save Yandex Disk configuration');
      }

      setMessage({ text: 'Yandex Disk configuration saved successfully', type: 'success' });
      setYandexConfig(editingYandexConfig);
      setEditingYandexConfig(null);
    } catch (error :any) {
      setMessage({ text: error.message, type: 'error' });
    } finally {
      setIsLoading(false);
    }
  };

  const saveGoogleDriveConfig = async () => {
    if (!editingGoogleConfig) return;

    try {
      setIsLoading(true);
      const response = await fetch('/api/cloud-config/google-drive', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(editingGoogleConfig),
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.error || 'Failed to save Google Drive configuration');
      }

      setMessage({ text: 'Google Drive configuration saved successfully', type: 'success' });
      setGoogleDriveConfig(editingGoogleConfig);
      setEditingGoogleConfig(null);
    } catch (error :any) {
      setMessage({ text: error.message, type: 'error' });
    } finally {
      setIsLoading(false);
    }
  };

  const handleJsonFileUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    const reader = new FileReader();
    reader.onload = (event) => {
      try {
        const json = JSON.parse(event.target?.result as string);
        setEditingGoogleConfig({
          ...editingGoogleConfig!,
          service_account_json: json
        });
      } catch  {
        setMessage({ text: 'Invalid JSON file', type: 'error' });
      }
    };
    reader.readAsText(file);
  };

  // Add function to fetch available chats for a setting
  const fetchAvailableChats = async () => {
    if (!sources.length) return;

    try {
      setLoadingAvailableChats(true);
      const allChats = [];

      // Fetch chats for each source
      for (const source of sources) {
        const response = await fetch(`/api/chats?source_name=${encodeURIComponent(source)}`);
        if (response.ok) {
          const data = await response.json();
          allChats.push(...(data.chats || []));
        }
      }

      setAvailableChats(allChats);
    } catch (error) {
      console.error("Error fetching available chats:", error);
    } finally {
      setLoadingAvailableChats(false);
    }
  };

  // Add function to fetch chats associated with a setting
  const fetchSettingChats = async (settingId :any) => {
    if (!settingId) return;

    try {
      const response = await fetch(`/api/settings/${settingId}/chats`);
      if (response.ok) {
        const data = await response.json();
        setSelectedChats(data.chats || []);
      }
    } catch (error) {
      console.error("Error fetching setting chats:", error);
    }
  };

  // Modify the existing function to handle setting editing
  const handleEditSetting = (setting :any) => {
    setEditingSetting(setting);
    setIsAddingNew(false);

    // Fetch chats for this setting
    fetchAvailableChats();
    if (setting.setting_id) {
      fetchSettingChats(setting.setting_id);
    } else {
      setSelectedChats([]);
    }
  };

  // Add functions to handle chat selection
  const handleChatSelectionChange = (chatId :any) => {
    setSelectedChats(prev => {
      if (prev.includes(chatId)) {
        return prev.filter(id => id !== chatId);
      } else {
        return [...prev, chatId];
      }
    });
  };

  return (
    <div className="w-full text-base-content">
      <h2 className="card-title text-secondary mb-6">{settingsT('title')}</h2>

      {message.text && (
        <div className={`alert ${message.type === 'success' ? 'alert-success' : 'alert-error'} mb-4`}>
          <span>{message.text}</span>
        </div>
      )}

      <div className="card bg-base-100 shadow-lg mb-6">
        <div className="card-body">
          <div className="flex items-center gap-2 mb-4">
            <Server size={20} className="text-primary" />
            <h3 className="text-lg font-medium">{settingsT('apiConfigTitle')}</h3>
          </div>

          <form onSubmit={handleSubmit}>
            <div className="form-control w-full mb-4">
              <label className="label">
                <span className="label-text">{settingsT('apiUrlLabel')}</span>
              </label>
              <input
                type="text"
                value={entrypointUrl}
                onChange={(e) => setEntrypointUrl(e.target.value)}
                placeholder={settingsT('apiUrlPlaceholder')}
                className="input input-bordered w-full"
                required
              />
            </div>

            <div className="flex gap-2">
              <button
                type="submit"
                className={`btn btn-primary ${isLoading ? 'loading' : ''}`}
                disabled={isLoading}
              >
                {isLoading ? settingsT('saving') : settingsT('save')}
              </button>
            </div>
          </form>
        </div>
      </div>

      {/* WhatsApp QR Code Section */}
      <div className="card bg-base-100 shadow-lg mb-6">
        <div className="card-body">
          <div className="flex items-center gap-2 mb-4">
            <QrCode size={20} className="text-primary" />
            <h3 className="text-lg font-medium">{settingsT('whatsappQrTitle') || 'WhatsApp QR Code'}</h3>
          </div>

          {whatsappQrCode ? (
            <div className="flex flex-col items-center">
              <p className="mb-2">{settingsT('lastQrCodeLabel') || 'Last available QR code:'}</p>
              <div className="bg-white p-4 rounded-md shadow-sm">
                <QRCode
                  value={whatsappQrCode}
                  size={256}
                  style={{ maxWidth: "100%", height: "auto" }}
                />
              </div>
              <p className="text-sm mt-2 text-gray-500">
                {settingsT('qrCodeInfo') || 'Scan this code with WhatsApp to connect to the system'}
              </p>
            </div>
          ) : (
            <p>{settingsT('noQrCode') || 'No WhatsApp QR code available. It will appear here when generated.'}</p>
          )}
        </div>
      </div>

      <div className="card bg-base-100 shadow-lg mb-6">
        <div className="card-body">
          <div className="flex items-center gap-2 mb-4">
            <BarChart2 size={20} className="text-primary" />
            <h3 className="text-lg font-medium">{settingsT('dashboardChartsTitle') || 'Dashboard Charts'}</h3>
          </div>

          <div className="form-control w-full mb-4">
            <label className="label">
              <span className="label-text">{settingsT('sourceLabel') || 'Data Source'}</span>
            </label>
            <select
              className="select select-bordered ml-4"
              value={selectedSource}
              onChange={(e) => setSelectedSource(e.target.value)}
              disabled={loadingSources}
            >
              {sources.map(source => (
                <option key={source} value={source}>{source}</option>
              ))}
            </select>
          </div>

          <div className="form-control w-full mb-4">
            <label className="label">
              <span className="label-text">{settingsT('chatLabel') || 'Chat for Dashboard Charts'}</span>
            </label>
            <select
              className="select select-bordered ml-4"
              value={dashboardChatId}
              onChange={(e) => setDashboardChatId(e.target.value)}
              disabled={loadingChats}
            >
              <option value="">{settingsT('selectChat') || 'Select a chat'}</option>
              {chats.map(chat => (
                <option key={chat.chat_id} value={chat.chat_id}>{chat.chat_name}</option>
              ))}
            </select>
          </div>

          <button
            onClick={saveDashboardChatId}
            className={`btn btn-primary ${isLoading ? 'loading' : ''}`}
            disabled={isLoading}
          >
            {settingsT('saveDashboardChat') || 'Save Dashboard Chat'}
          </button>
        </div>
      </div>

      {/* Report Settings Section */}
      <div className="card bg-base-100 shadow-lg mb-6">
        <div className="card-body">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-2">
              <Calendar size={20} className="text-primary" />
              <h3 className="text-lg font-medium">{settingsT('reportSettingsTitle') || 'Report Schedules'}</h3>
            </div>
            <button
              className="btn btn-sm btn-primary"
              onClick={() => {
                setIsAddingNew(true);
                setEditingSetting({
                  setting_name: '',
                  setting_description: '',
                  format_report: 'xlsx',
                  type: 'filesystem',
                  send_to: [],
                  minute: '0',
                  hour: '6',
                  day_of_month: '*',
                  month: '*',
                  day_of_week: '*',
                  extra: {}
                });
                fetchAvailableChats(); // Add this line to fetch chats
                setSelectedChats([]);
              }}
            >
              <Plus size={16} />
              {settingsT('addNewSetting') || 'Add New'}
            </button>
          </div>

          <div className="form-control mb-4">
            <label className="label cursor-pointer justify-start gap-2">
              <input
                type="checkbox"
                className="checkbox checkbox-primary"
                checked={showDeletedSettings}
                onChange={(e) => {
                  setShowDeletedSettings(e.target.checked);
                  fetchReportSettings();
                }}
              />
              <span className="label-text">{settingsT('showDeletedSettings') || 'Show deleted settings'}</span>
            </label>
          </div>

          {loadingSettings ? (
            <div className="flex justify-center my-4">
              <span className="loading loading-spinner loading-md"></span>
            </div>
          ) : reportSettings.length === 0 ? (
            <div className="alert">
              <span>{settingsT('noSettings') || 'No report schedules found'}</span>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="table table-zebra w-full">
                <thead>
                  <tr>
                    <th>{settingsT('name') || 'Name'}</th>
                    <th>{settingsT('description') || 'Description'}</th>
                    <th>{settingsT('schedule') || 'Schedule'}</th>
                    <th>{settingsT('type') || 'Type'}</th>
                    <th>{settingsT('actions') || 'Actions'}</th>
                  </tr>
                </thead>
                <tbody>
                  {reportSettings.map(setting => (
                    <tr key={setting.setting_id} className={setting.deleted ? "opacity-50" : ""}>
                      <td>{setting.setting_name}</td>
                      <td>{setting.setting_description}</td>
                      <td>
                        <code>{`${setting.minute} ${setting.hour} ${setting.day_of_month} ${setting.month} ${setting.day_of_week}`}</code>
                      </td>
                      <td>{setting.type}</td>
                      <td>
                        <div className="flex gap-2">
                          <button
                            className="btn btn-sm btn-ghost"
                            onClick={() => handleEditSetting(setting)}
                            disabled={setting.deleted}
                          >
                            <Edit size={16} />
                          </button>
                          {!setting.deleted && (
                            <button
                              className="btn btn-sm btn-ghost text-error"
                              onClick={() => handleDeleteSetting(setting.setting_id)}
                            >
                              <Trash2 size={16} />
                            </button>
                          )}
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          {/* Edit Setting Dialog */}
          {editingSetting && (
            <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
              <div className="bg-base-100 p-6 rounded-lg w-full max-w-2xl max-h-[90vh] overflow-y-auto">
                <div className="flex justify-between items-center mb-4">
                  <h3 className="text-lg font-medium">
                    {isAddingNew
                      ? (settingsT('addNewSetting') || 'Add New Report Schedule')
                      : (settingsT('editSetting') || 'Edit Report Schedule')}
                  </h3>
                  <button
                    className="btn btn-sm btn-ghost"
                    onClick={() => {
                      setEditingSetting(null);
                      setIsAddingNew(false);
                    }}
                  >
                    <X size={16} />
                  </button>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div className="form-control w-full">
                    <label className="label">
                      <span className="label-text">{settingsT('name') || 'Name'}</span>
                    </label>
                    <input
                      type="text"
                      className="input input-bordered w-full"
                      value={editingSetting.setting_name || ''}
                      onChange={(e) => setEditingSetting({ ...editingSetting, setting_name: e.target.value })}
                      required
                    />
                  </div>

                  <div className="form-control w-full">
                    <label className="label">
                      <span className="label-text">{settingsT('description') || 'Description'}</span>
                    </label>
                    <input
                      type="text"
                      className="input input-bordered w-full"
                      value={editingSetting.setting_description || ''}
                      onChange={(e) => setEditingSetting({ ...editingSetting, setting_description: e.target.value })}
                    />
                  </div>

                  <div className="form-control w-full">
                    <label className="label">
                      <span className="label-text">{settingsT('type') || 'Storage Type'}</span>
                    </label>
                    <select
                      className="select select-bordered w-full"
                      value={editingSetting.type || 'filesystem'}
                      onChange={(e) => setEditingSetting({
                        ...editingSetting,
                        type: e.target.value as 'filesystem' | 'google-drive' | 'yandex-disk'
                      })}
                    >
                      <option value="filesystem">Filesystem</option>
                      <option value="google-drive">Google Drive</option>
                      <option value="yandex-disk">Yandex Disk</option>
                    </select>
                  </div>

                  <div className="form-control w-full">
                    <label className="label">
                      <span className="label-text">{settingsT('format') || 'Report Format'}</span>
                    </label>
                    <select
                      className="select select-bordered w-full"
                      value={editingSetting.format_report || 'xlsx'}
                      onChange={(e) => setEditingSetting({ ...editingSetting, format_report: e.target.value as 'xlsx' })}
                    >
                      <option value="xlsx">Excel (XLSX)</option>
                    </select>
                  </div>
                </div>

                <div className="divider">{settingsT('cronSchedule') || 'Schedule (Cron Format)'}</div>

                <div className="grid grid-cols-1 md:grid-cols-5 gap-4">
                  <div className="form-control">
                    <label className="label">
                      <span className="label-text">{settingsT('minute') || 'Minute'}</span>
                    </label>
                    <input
                      type="text"
                      className="input input-bordered"
                      value={editingSetting.minute || '0'}
                      onChange={(e) => setEditingSetting({ ...editingSetting, minute: e.target.value })}
                      placeholder="0-59 or *"
                    />
                  </div>

                  <div className="form-control">
                    <label className="label">
                      <span className="label-text">{settingsT('hour') || 'Hour'}</span>
                    </label>
                    <input
                      type="text"
                      className="input input-bordered"
                      value={editingSetting.hour || '6'}
                      onChange={(e) => setEditingSetting({ ...editingSetting, hour: e.target.value })}
                      placeholder="0-23 or *"
                    />
                  </div>

                  <div className="form-control">
                    <label className="label">
                      <span className="label-text">{settingsT('dayOfMonth') || 'Day (Month)'}</span>
                    </label>
                    <input
                      type="text"
                      className="input input-bordered"
                      value={editingSetting.day_of_month || '*'}
                      onChange={(e) => setEditingSetting({ ...editingSetting, day_of_month: e.target.value })}
                      placeholder="1-31 or *"
                    />
                  </div>

                  <div className="form-control">
                    <label className="label">
                      <span className="label-text">{settingsT('month') || 'Month'}</span>
                    </label>
                    <input
                      type="text"
                      className="input input-bordered"
                      value={editingSetting.month || '*'}
                      onChange={(e) => setEditingSetting({ ...editingSetting, month: e.target.value })}
                      placeholder="1-12 or *"
                    />
                  </div>

                  <div className="form-control">
                    <label className="label">
                      <span className="label-text">{settingsT('dayOfWeek') || 'Day (Week)'}</span>
                    </label>
                    <input
                      type="text"
                      className="input input-bordered"
                      value={editingSetting.day_of_week || '*'}
                      onChange={(e) => setEditingSetting({ ...editingSetting, day_of_week: e.target.value })}
                      placeholder="0-6 or *"
                    />
                  </div>
                </div>

                <div className="divider">{settingsT('recipients') || 'Recipients'}</div>

                <div className="mb-4">
                  {(editingSetting.send_to || []).map((recipient, index) => (
                    <div key={index} className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-2 items-end">
                      <div className="form-control">
                        <label className="label">
                          <span className="label-text">{settingsT('phoneNumber') || 'Phone Number'}</span>
                        </label>
                        <input
                          type="text"
                          className="input input-bordered"
                          value={recipient.phone_number}
                          onChange={(e) => updatePhoneNumber(index, 'phone_number', e.target.value)}
                          placeholder="+1234567890"
                        />
                      </div>

                      <div className="form-control">
                        <label className="label">
                          <span className="label-text">{settingsT('platform') || 'Platform'}</span>
                        </label>
                        <select
                          className="select select-bordered"
                          value={recipient.messenger}  // Changed from platform to messenger
                          onChange={(e) => updatePhoneNumber(
                            index,
                            'messenger',  // Changed from 'platform' to 'messenger'
                            e.target.value as 'whatsapp' | 'telegram'
                          )}
                        >
                          <option value="whatsapp">WhatsApp</option>
                          <option value="telegram">Telegram</option>
                        </select>
                      </div>

                      <button
                        className="btn btn-error"
                        onClick={() => removePhoneNumber(index)}
                      >
                        <Trash2 size={16} />
                        {settingsT('remove') || 'Remove'}
                      </button>
                    </div>
                  ))}

                  <button
                    className="btn btn-outline btn-primary mt-2"
                    onClick={addPhoneNumber}
                  >
                    <Plus size={16} />
                    {settingsT('addRecipient') || 'Add Recipient'}
                  </button>
                </div>

                <div className="divider">{settingsT('associatedChats') || 'Associated Chats'}</div>

                <div className="mb-4">
                  {loadingAvailableChats ? (
                    <div className="flex justify-center py-4">
                      <span className="loading loading-spinner loading-md"></span>
                    </div>
                  ) : availableChats.length === 0 ? (
                    <p className="text-center py-2">{settingsT('noChatsAvailable') || 'No chats available'}</p>
                  ) : (
                    <div className="grid grid-cols-1 gap-2 max-h-60 overflow-y-auto p-2">
                      {availableChats.map(chat => (
                        <div key={chat.chat_id} className="form-control">
                          <label className="label cursor-pointer justify-start gap-2">
                            <input
                              type="checkbox"
                              className="checkbox checkbox-primary"
                              checked={selectedChats.includes(chat.chat_id)}
                              onChange={() => handleChatSelectionChange(chat.chat_id)}
                            />
                            <span className="label-text">
                              {chat.chat_name} ({chat.source_name})
                            </span>
                          </label>
                        </div>
                      ))}
                    </div>
                  )}
                  <p className="text-sm text-gray-500 mt-2">
                    {settingsT('chatsHelp') || 'Select chats that this report will process data from'}
                  </p>
                </div>

                <div className="flex justify-end gap-2 mt-4">
                  <button
                    className="btn btn-ghost"
                    onClick={() => {
                      setEditingSetting(null);
                      setIsAddingNew(false);
                    }}
                  >
                    {settingsT('cancel') || 'Cancel'}
                  </button>
                  <button
                    className={`btn btn-primary ${isLoading ? 'loading' : ''}`}
                    onClick={handleSaveSetting}
                    disabled={isLoading}
                  >
                    <Save size={16} className="mr-1" />
                    {isLoading
                      ? (settingsT('saving') || 'Saving...')
                      : (isAddingNew
                        ? (settingsT('create') || 'Create')
                        : (settingsT('update') || 'Update'))}
                  </button>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Cloud Storage Section */}
      <div className="card bg-base-100 shadow-lg mb-6">
        <div className="card-body">
          <div className="flex items-center gap-2 mb-4">
            <Cloud size={20} className="text-primary" />
            <h3 className="text-lg font-medium">{settingsT('cloudStorageTitle') || 'Cloud Storage'}</h3>
          </div>

          {loadingCloud ? (
            <div className="flex justify-center my-4">
              <span className="loading loading-spinner loading-md"></span>
            </div>
          ) : (
            <>
              {/* Yandex Disk Config */}
              <div className="mb-6">
                <h4 className="font-medium mb-2">{settingsT('yandexDiskTitle') || 'Yandex Disk'}</h4>

                {editingYandexConfig ? (
                  <div className="card bg-base-200 p-4">
                    <div className="form-control mb-4">
                      <label className="label">
                        <span className="label-text">{settingsT('token') || 'OAuth Token'}</span>
                      </label>
                      <input
                        type="text"
                        className="input input-bordered"
                        value={editingYandexConfig.token}
                        onChange={(e) => setEditingYandexConfig({
                          ...editingYandexConfig,
                          token: e.target.value
                        })}
                        placeholder="OAuth token from Yandex"
                      />
                    </div>

                    <div className="form-control mb-4">
                      <label className="label">
                        <span className="label-text">{settingsT('folderName') || 'Shared Folder Name'}</span>
                      </label>
                      <input
                        type="text"
                        className="input input-bordered"
                        value={editingYandexConfig.shared_folder_name}
                        onChange={(e) => setEditingYandexConfig({
                          ...editingYandexConfig,
                          shared_folder_name: e.target.value
                        })}
                        placeholder="Reports folder name"
                      />
                    </div>

                    <div className="flex justify-end gap-2">
                      <button
                        className="btn btn-ghost"
                        onClick={() => setEditingYandexConfig(null)}
                      >
                        {settingsT('cancel') || 'Cancel'}
                      </button>
                      <button
                        className={`btn btn-primary ${isLoading ? 'loading' : ''}`}
                        onClick={saveYandexConfig}
                        disabled={isLoading}
                      >
                        {settingsT('save') || 'Save'}
                      </button>
                    </div>
                  </div>
                ) : (
                  <div className="flex flex-col">
                    {yandexConfig ? (
                      <div className="bg-base-200 p-4 rounded-lg">
                        <div className="mb-2">
                          <span className="font-medium">{settingsT('token') || 'Token'}:</span>
                          <span className="ml-2">{yandexConfig.token.substring(0, 10)}...</span>
                        </div>
                        <div>
                          <span className="font-medium">{settingsT('folderName') || 'Folder'}:</span>
                          <span className="ml-2">{yandexConfig.shared_folder_name}</span>
                        </div>
                        <button
                          className="btn btn-sm btn-primary mt-2"
                          onClick={() => setEditingYandexConfig(yandexConfig)}
                        >
                          {settingsT('edit') || 'Edit'}
                        </button>
                      </div>
                    ) : (
                      <div className="flex flex-col">
                        <p className="mb-2">{settingsT('noYandexConfig') || 'No Yandex Disk configuration found.'}</p>
                        <button
                          className="btn btn-sm btn-primary self-start"
                          onClick={() => setEditingYandexConfig({
                            token: '',
                            shared_folder_name: 'agro_reports'
                          })}
                        >
                          {settingsT('configure') || 'Configure'}
                        </button>
                      </div>
                    )}
                  </div>
                )}
              </div>

              {/* Google Drive Config */}
              <div>
                <h4 className="font-medium mb-2">{settingsT('googleDriveTitle') || 'Google Drive'}</h4>

                {editingGoogleConfig ? (
                  <div className="card bg-base-200 p-4">
                    <div className="form-control mb-4">
                      <label className="label">
                        <span className="label-text">{settingsT('serviceAccount') || 'Service Account JSON'}</span>
                      </label>
                      <input
                        type="file"
                        className="file-input file-input-bordered w-full"
                        accept=".json"
                        onChange={handleJsonFileUpload}
                      />
                      {editingGoogleConfig.service_account_json && Object.keys(editingGoogleConfig.service_account_json).length > 0 && (
                        <div className="mt-2 p-2 bg-base-300 rounded text-xs overflow-x-auto">
                          <pre>{JSON.stringify(editingGoogleConfig.service_account_json, null, 2)}</pre>
                        </div>
                      )}
                    </div>

                    <div className="form-control mb-4">
                      <label className="label">
                        <span className="label-text">{settingsT('folderName') || 'Shared Folder Name'}</span>
                      </label>
                      <input
                        type="text"
                        className="input input-bordered"
                        value={editingGoogleConfig.shared_folder_name}
                        onChange={(e) => setEditingGoogleConfig({
                          ...editingGoogleConfig,
                          shared_folder_name: e.target.value
                        })}
                        placeholder="Reports folder name"
                      />
                    </div>

                    <div className="flex justify-end gap-2">
                      <button
                        className="btn btn-ghost"
                        onClick={() => setEditingGoogleConfig(null)}
                      >
                        {settingsT('cancel') || 'Cancel'}
                      </button>
                      <button
                        className={`btn btn-primary ${isLoading ? 'loading' : ''}`}
                        onClick={saveGoogleDriveConfig}
                        disabled={isLoading || !editingGoogleConfig.service_account_json}
                      >
                        {settingsT('save') || 'Save'}
                      </button>
                    </div>
                  </div>
                ) : (
                  <div className="flex flex-col">
                    {googleDriveConfig ? (
                      <div className="bg-base-200 p-4 rounded-lg">
                        <div className="mb-2">
                          <span className="font-medium">{settingsT('serviceAccount') || 'Service Account'}:</span>
                          <span className="ml-2">{googleDriveConfig.service_account_json.client_email || 'Configured'}</span>
                        </div>
                        <div>
                          <span className="font-medium">{settingsT('folderName') || 'Folder'}:</span>
                          <span className="ml-2">{googleDriveConfig.shared_folder_name}</span>
                        </div>
                        <button
                          className="btn btn-sm btn-primary mt-2"
                          onClick={() => setEditingGoogleConfig(googleDriveConfig)}
                        >
                          {settingsT('edit') || 'Edit'}
                        </button>
                      </div>
                    ) : (
                      <div className="flex flex-col">
                        <p className="mb-2">{settingsT('noGoogleConfig') || 'No Google Drive configuration found.'}</p>
                        <button
                          className="btn btn-sm btn-primary self-start"
                          onClick={() => setEditingGoogleConfig({
                            service_account_json: {},
                            shared_folder_name: 'agro_reports'
                          })}
                        >
                          {settingsT('configure') || 'Configure'}
                        </button>
                      </div>
                    )}
                  </div>
                )}
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
}