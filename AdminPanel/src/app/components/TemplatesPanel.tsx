'use client'; // This component uses client-side hooks (useState, useEffect)

import React, { useState, useEffect, useCallback, ChangeEvent, FormEvent } from 'react';
import { useTranslations } from 'next-intl'; // Add this import

// --- Type Definitions ---
// Keep types within the same file as requested

// Type for the template data structure used in the component state
interface Template {
    _id: string; // Use string for client-side state, ObjectId is handled server-side
    name: string;
    columns: string[];
    taskSplitPrompt: string;
    systemPrompt: string;
    // Add createdAt/updatedAt if needed in the UI, otherwise keep them server-side
}

// Type for the list of templates fetched for the dropdown
interface TemplateListItem {
    _id: string;
    name: string;
}

// New type for chat data
interface Chat {
    chat_id: string;
    chat_name: string;
    source_name: string;
    active: boolean;
    template_id?: string; // Added for template association
}

// Group chats by source for better organization
interface GroupedChats {
    [sourceName: string]: Chat[];
}


// --- Default empty template state ---
const defaultTemplateState: Omit<Template, '_id'> = {
    name: '',
    columns: ['Column 1', 'Column 2'], // Start with some defaults?
    taskSplitPrompt: '',
    systemPrompt: '',
};

// --- Component ---
const TemplatesPanel: React.FC = () => {
    const t = useTranslations('templates');

    const [templatesList, setTemplatesList] = useState<TemplateListItem[]>([]);
    const [selectedTemplateId, setSelectedTemplateId] = useState<string | null>(null);
    const [currentTemplate, setCurrentTemplate] = useState<Partial<Template> | null>(null); // Partial allows for creation state
    const [newColumnName, setNewColumnName] = useState<string>('');
    const [isLoadingList, setIsLoadingList] = useState<boolean>(true);
    const [isLoadingDetails, setIsLoadingDetails] = useState<boolean>(false);
    const [isSaving, setIsSaving] = useState<boolean>(false);
    const [error, setError] = useState<string | null>(null);
    const [isCreating, setIsCreating] = useState<boolean>(false);
    
    // New state for chats
    const [availableChats, setAvailableChats] = useState<GroupedChats>({});
    const [selectedChats, setSelectedChats] = useState<string[]>([]);
    const [isLoadingChats, setIsLoadingChats] = useState<boolean>(false);
    const [sources, setSources] = useState<string[]>([]);
    const [expandedSources, setExpandedSources] = useState<Set<string>>(new Set());

    // --- Data Fetching ---
    const fetchTemplatesList = useCallback(async () => {
        setIsLoadingList(true);
        setError(null);
        try {
            const response = await fetch('/api/templates');
            if (!response.ok) {
                throw new Error(`Failed to fetch templates list: ${response.statusText}`);
            }
            const data: TemplateListItem[] = await response.json();
            setTemplatesList(data);
        } catch (err: any) {
            console.error("Error fetching templates list:", err);
            setError(err.message || 'Could not load templates.');
        } finally {
            setIsLoadingList(false);
        }
    }, []);

    const fetchTemplateDetails = useCallback(async (id: string) => {
        if (!id) return;
        setIsLoadingDetails(true);
        setError(null);
        try {
            const response = await fetch(`/api/templates?id=${id}`);
            if (!response.ok) {
                if (response.status === 404) {
                    throw new Error(`Template not found.`);
                }
                throw new Error(`Failed to fetch template details: ${response.statusText}`);
            }
            const data: Template = await response.json();
            setCurrentTemplate(data);
            setIsCreating(false);
            
            // Fetch chats associated with this template
            await fetchTemplateChats(id);
        } catch (err: any) {
            console.error("Error fetching template details:", err);
            setError(err.message || 'Could not load template details.');
            setCurrentTemplate(null);
            setSelectedTemplateId(null);
        } finally {
            setIsLoadingDetails(false);
        }
    }, []);

    // Fetch all available chats
    const fetchAvailableChats = useCallback(async () => {
        setIsLoadingChats(true);
        try {
            
            const sourceNames = ["whatsapp", "telegram"]
            setSources(sourceNames);
            
            // Fetch chats for each source
            const groupedChats: GroupedChats = {};
            
            for (const source of sourceNames) {
                const response = await fetch(`/api/chats?source_name=${source}`);
                if (!response.ok) {
                    console.error(`Failed to fetch chats for source ${source}`);
                    continue;
                }
                const data = await response.json();
                groupedChats[source] = data.chats;
            }
            
            setAvailableChats(groupedChats);
        } catch (err: any) {
            console.error("Error fetching available chats:", err);
            setError(err.message || 'Could not load available chats.');
        } finally {
            setIsLoadingChats(false);
        }
    }, []);

    // Fetch chats associated with a template
    const fetchTemplateChats = useCallback(async (templateId: string) => {
        try {
            // First ensure we have all available chats
            if (Object.keys(availableChats).length === 0) {
                await fetchAvailableChats();
            }
            
            // Find all chats that have this template_id
            const selected: string[] = [];
            
            for (const source in availableChats) {
                for (const chat of availableChats[source]) {
                    if (chat.template_id === templateId) {
                        selected.push(chat.chat_id);
                    }
                }
            }
            
            setSelectedChats(selected);
        } catch (err: any) {
            console.error("Error fetching template chats:", err);
        }
    }, [availableChats, fetchAvailableChats]);

    // Initial fetch of templates list and available chats
    useEffect(() => {
        fetchTemplatesList();
        fetchAvailableChats();
    }, [fetchTemplatesList, fetchAvailableChats]);

    useEffect(() => {
        if (selectedTemplateId && selectedTemplateId !== 'new') {
            fetchTemplateDetails(selectedTemplateId);
        } else if (!selectedTemplateId) {
            setCurrentTemplate(null);
            setIsCreating(false);
            setSelectedChats([]);
        }
    }, [selectedTemplateId, fetchTemplateDetails]);

    // --- Event Handlers ---
    const handleSelectChange = (e: ChangeEvent<HTMLSelectElement>) => {
        const id = e.target.value;
        if (id === 'new') {
            handleCreateNewClick();
        } else {
            setSelectedTemplateId(id || null);
            setIsCreating(false);
        }
    };

    const handleCreateNewClick = () => {
        setSelectedTemplateId('new');
        setCurrentTemplate({ ...defaultTemplateState });
        setIsCreating(true);
        setError(null);
        setSelectedChats([]);
    };

    const handleInputChange = (e: ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => {
        const { name, value } = e.target;
        setCurrentTemplate(prev => prev ? { ...prev, [name]: value } : null);
    };

    const handleAddColumn = () => {
        if (newColumnName.trim() && currentTemplate?.columns) {
            if (currentTemplate.columns.some(col => col.toLowerCase() === newColumnName.trim().toLowerCase())) {
                setError(t('columnExists', { name: newColumnName.trim() }));
                return;
            }
            setError(null);
            setCurrentTemplate(prev => prev ? {
                ...prev,
                columns: [...(prev.columns || []), newColumnName.trim()]
            } : null);
            setNewColumnName('');
        } else if (!newColumnName.trim()) {
            setError(t('columnNameEmpty'));
        }
    };

    const handleRemoveColumn = (indexToRemove: number) => {
        setCurrentTemplate(prev => prev ? {
            ...prev,
            columns: (prev.columns || []).filter((_, index) => index !== indexToRemove)
        } : null);
        setError(null);
    };

    const handleColumnNameChange = (indexToChange: number, newName: string) => {
        setCurrentTemplate(prev => {
            if (!prev || !prev.columns) return prev;

            const lowerNewName = newName.trim().toLowerCase();
            if (lowerNewName && prev.columns.some((col, idx) => idx !== indexToChange && col.toLowerCase() === lowerNewName)) {
                setError(`Column name "${newName.trim()}" already exists.`);
                return prev;
            }
            setError(null);

            const updatedColumns = [...prev.columns];
            updatedColumns[indexToChange] = newName.trim();
            return { ...prev, columns: updatedColumns };
        });
    };

    // Handle toggling a chat selection
    const handleChatSelect = (chatId: string) => {
        setSelectedChats(prev => {
            if (prev.includes(chatId)) {
                return prev.filter(id => id !== chatId);
            } else {
                return [...prev, chatId];
            }
        });
    };

    // Toggle source expansion
    const toggleSourceExpansion = (sourceName: string) => {
        setExpandedSources(prev => {
            const newSet = new Set(prev);
            if (newSet.has(sourceName)) {
                newSet.delete(sourceName);
            } else {
                newSet.add(sourceName);
            }
            return newSet;
        });
    };

    // Update chats with template association
    const updateChatTemplateAssociations = async (templateId: string) => {
        // For each available chat, check if it should be associated with this template
        for (const source in availableChats) {
            for (const chat of availableChats[source]) {
                const isSelected = selectedChats.includes(chat.chat_id);
                const hasTemplateAlready = chat.template_id === templateId;
                
                // Only update if the selection state differs from current state
                if (isSelected !== hasTemplateAlready) {
                    try {
                        await fetch(`/api/chats/${chat.chat_id}`, {
                            method: 'PATCH',
                            headers: { 'Content-Type': 'application/json' },
                            body: JSON.stringify({
                                template_id: isSelected ? templateId : null,
                                active: chat.active // Maintain current active status
                            })
                        });
                    } catch (err) {
                        console.error(`Failed to update template association for chat ${chat.chat_id}:`, err);
                    }
                }
            }
        }
    };

    const handleSaveTemplate = async (e: FormEvent) => {
        e.preventDefault();
        if (!currentTemplate || !currentTemplate.name?.trim()) {
            setError(t('templateNameRequired'));
            return;
        }
        if (!currentTemplate.columns || currentTemplate.columns.length === 0) {
            setError(t('columnRequired'));
            return;
        }
        if (currentTemplate.columns.some(col => !col.trim())) {
            setError(t('emptyColumnsNotAllowed'));
            return;
        }

        setIsSaving(true);
        setError(null);

        const method = isCreating ? 'POST' : 'PUT';
        const url = isCreating ? '/api/templates' : `/api/templates?id=${selectedTemplateId}`;

        try {
            const response = await fetch(url, {
                method: method,
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(currentTemplate),
            });

            if (!response.ok) {
                const errorData = await response.json().catch(() => ({ error: 'Save operation failed.' }));
                throw new Error(errorData.error || `Failed to save template: ${response.statusText}`);
            }

            const savedTemplate: Template = await response.json();

            // Update chat associations with this template
            await updateChatTemplateAssociations(savedTemplate._id);

            // Update state after successful save
            setCurrentTemplate(savedTemplate);
            setSelectedTemplateId(savedTemplate._id);
            setIsCreating(false);

            // Refresh the list to include the new/updated template
            await fetchTemplatesList();
            
            // Refresh chat associations
            await fetchTemplateChats(savedTemplate._id);

            console.log("Template saved successfully!");

        } catch (err: any) {
            console.error("Error saving template:", err);
            setError(err.message || 'Could not save template.');
        } finally {
            setIsSaving(false);
        }
    };

    const handleDeleteTemplate = async () => {
        if (!selectedTemplateId || selectedTemplateId === 'new' || isCreating) {
            setError(t('noTemplateSelected'));
            return;
        }
    
        if (!window.confirm(t('confirmDelete', { name: currentTemplate?.name || 'this template' }))) {
            return;
        }

        setIsSaving(true);
        setError(null);

        try {
            // First, remove template associations from all chats
            await updateChatTemplateAssociations(''); // Empty string to remove associations
            
            const response = await fetch(`/api/templates?id=${selectedTemplateId}`, {
                method: 'DELETE',
            });

            if (!response.ok) {
                const errorData = await response.json().catch(() => ({ error: 'Delete operation failed.' }));
                throw new Error(errorData.error || `Failed to delete template: ${response.statusText}`);
            }

            setSelectedTemplateId(null);
            setCurrentTemplate(null);
            setSelectedChats([]);
            await fetchTemplatesList();
            await fetchAvailableChats(); // Refresh chats to update template associations

            console.log("Template deleted successfully!");

        } catch (err: any) {
            console.error("Error deleting template:", err);
            setError(err.message || 'Could not delete template.');
        } finally {
            setIsSaving(false);
        }
    };

    return (
        <div className="p-4 md:p-6 lg:p-8 bg-base-100 text-base-content rounded-lg shadow-md">
            {/* --- Template Selection / Creation --- */}
            <div className="flex flex-wrap items-center gap-4 mb-6">
                <div className="form-control w-full sm:w-auto sm:min-w-[200px]">
                    <label className="label pb-1">
                        <span className="label-text">{t('selectTemplate')}</span>
                    </label>
                    <select
                        className={`select select-bordered w-full ${isLoadingList ? 'opacity-50' : ''}`}
                        value={selectedTemplateId ?? ''}
                        onChange={handleSelectChange}
                        disabled={isLoadingList || isSaving}
                    >
                        <option value="" disabled={!isCreating}>
                            {isLoadingList ? t('loading') : t('selectOrCreate')}
                        </option>
                        <option value="new">{t('createNewTemplate')}</option>
                        {templatesList.map(template => (
                            <option key={template._id} value={template._id}>
                                {template.name}
                            </option>
                        ))}
                    </select>
                </div>
            </div>
    
            {/* --- Loading/Error States --- */}
            {error && (
                <div role="alert" className="alert alert-error mb-4">
                    <svg xmlns="http://www.w3.org/2000/svg" className="stroke-current shrink-0 h-6 w-6" fill="none" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M10 14l2-2m0 0l2-2m-2 2l-2-2m2 2l2 2m7-2a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>
                    <span>{t('error')}: {error}</span>
                    <button className="btn btn-xs btn-ghost" onClick={() => setError(null)}>✕</button>
                </div>
            )}
            {isLoadingDetails && (
                <div className="text-center p-4"><span className="loading loading-spinner text-primary"></span> {t('loadingTemplateDetails')}</div>
            )}
    
            {/* --- Template Edit Form --- */}
            {currentTemplate && !isLoadingDetails && (
                <form onSubmit={handleSaveTemplate} className="space-y-6">
                    {/* --- Template Name --- */}
                    <div className="form-control">
                        <label htmlFor="templateName" className="label">
                            <span className="label-text text-lg font-semibold">{t('templateName')}</span>
                        </label>
                        <input
                            type="text"
                            id="templateName"
                            name="name"
                            placeholder={t('enterTemplateName')}
                            className="input input-bordered w-full"
                            value={currentTemplate.name ?? ''}
                            onChange={handleInputChange}
                            required
                            disabled={isSaving}
                        />
                    </div>
    
                    {/* --- Columns Management --- */}
                    <div className="form-control">
                        <label className="label">
                            <span className="label-text text-lg font-semibold">{t('tableColumns')}</span>
                        </label>
                        <div className="space-y-2 mb-3">
                            {(currentTemplate.columns ?? []).map((col, index) => (
                                <div key={index} className="flex items-center gap-2">
                                    <input
                                        type="text"
                                        value={col}
                                        onChange={(e) => handleColumnNameChange(index, e.target.value)}
                                        className="input input-bordered input-sm flex-grow"
                                        placeholder={t('columnPlaceholder', { number: index + 1 })}
                                        disabled={isSaving}
                                        required
                                    />
                                    <button
                                        type="button"
                                        onClick={() => handleRemoveColumn(index)}
                                        className="btn btn-error btn-outline btn-sm btn-square"
                                        aria-label={t('removeColumn', { name: col || index + 1 })}
                                        disabled={isSaving}
                                    >
                                        ✕
                                    </button>
                                </div>
                            ))}
                            {(currentTemplate.columns ?? []).length === 0 && <p className="text-sm text-warning">{t('addAtLeastOneColumn')}</p>}
                        </div>
                        <div className="flex items-center gap-2">
                            <input
                                type="text"
                                value={newColumnName}
                                onChange={(e) => setNewColumnName(e.target.value)}
                                placeholder={t('newColumnName')}
                                className="input input-bordered input-sm flex-grow"
                                disabled={isSaving}
                                onKeyDown={(e) => { if (e.key === 'Enter') { e.preventDefault(); handleAddColumn(); } }}
                            />
                            <button
                                type="button"
                                onClick={handleAddColumn}
                                className="btn btn-secondary btn-sm"
                                disabled={!newColumnName.trim() || isSaving}
                            >
                                {t('addColumn')}
                            </button>
                        </div>
                    </div>
    
                    {/* --- Task Split Prompt --- */}
                    <div className="form-control">
                        <label htmlFor="taskSplitPrompt" className="label">
                            <span className="label-text text-lg font-semibold">{t('taskSplitPrompt')}</span>
                            <span className="label-text-alt">{t('taskSplitInstructions')}</span>
                        </label>
                        <textarea
                            id="taskSplitPrompt"
                            name="taskSplitPrompt"
                            className="textarea textarea-bordered w-full h-32"
                            placeholder={t('enterTaskSplitPrompt')}
                            value={currentTemplate.taskSplitPrompt ?? ''}
                            onChange={handleInputChange}
                            disabled={isSaving}
                        ></textarea>
                    </div>
    
                    {/* --- System Prompt --- */}
                    <div className="form-control">
                        <label htmlFor="systemPrompt" className="label">
                            <span className="label-text text-lg font-semibold">{t('systemPrompt')}</span>
                            <span className="label-text-alt">{t('systemPromptInstructions')}</span>
                        </label>
                        <textarea
                            id="systemPrompt"
                            name="systemPrompt"
                            className="textarea textarea-bordered w-full h-48"
                            placeholder={t('enterSystemPrompt')}
                            value={currentTemplate.systemPrompt ?? ''}
                            onChange={handleInputChange}
                            disabled={isSaving}
                        ></textarea>
                    </div>
    
                    {/* --- Associated Chats Section --- */}
                    <div className="form-control">
                        <label className="label">
                            <span className="label-text text-lg font-semibold">{t('associatedChats')}</span>
                            <span className="label-text-alt">{t('selectChatsForTemplate')}</span>
                        </label>
                        
                        {isLoadingChats ? (
                            <div className="p-4 text-center">
                                <span className="loading loading-spinner loading-sm"></span> {t('loadingChats')}
                            </div>
                        ) : Object.keys(availableChats).length === 0 ? (
                            <div className="p-4 text-center text-base-content/70 border border-dashed border-base-300 rounded-md">
                                {t('noChats')}
                            </div>
                        ) : (
                            <div className="space-y-4 mt-2 p-4 border border-base-300 rounded-md bg-base-200/50">
                                {sources.map(sourceName => (
                                    <div key={sourceName} className="border border-base-300 rounded-lg bg-base-100 overflow-hidden">
                                        <button 
                                            type="button"
                                            className="w-full flex justify-between items-center p-3 text-left font-medium hover:bg-base-200 transition-colors"
                                            onClick={() => toggleSourceExpansion(sourceName)}
                                        >
                                            <span>
                                                {sourceName} 
                                                <span className="text-sm text-base-content/70 ml-2">
                                                    ({availableChats[sourceName]?.length || 0} {t('chats')})
                                                </span>
                                            </span>
                                            <span>{expandedSources.has(sourceName) ? '▼' : '►'}</span>
                                        </button>
                                        
                                        {expandedSources.has(sourceName) && (
                                            <div className="p-3 pt-0 space-y-1">
                                                {availableChats[sourceName]?.length > 0 ? (
                                                    availableChats[sourceName].map(chat => (
                                                        <label key={chat.chat_id} className="flex items-center gap-2 p-2 hover:bg-base-200 rounded">
                                                            <input
                                                                type="checkbox"
                                                                className="checkbox checkbox-sm"
                                                                checked={selectedChats.includes(chat.chat_id)}
                                                                onChange={() => handleChatSelect(chat.chat_id)}
                                                                disabled={isSaving}
                                                            />
                                                            <span className="flex-grow">
                                                                {chat.chat_name}
                                                                {!chat.active && (
                                                                    <span className="ml-2 badge badge-warning badge-sm">{t('inactive')}</span>
                                                                )}
                                                            </span>
                                                        </label>
                                                    ))
                                                ) : (
                                                    <p className="py-2 text-sm text-base-content/70 italic">
                                                        {t('noChatsForSource')}
                                                    </p>
                                                )}
                                            </div>
                                        )}
                                    </div>
                                ))}
                                
                                <div className="flex items-center justify-between pt-2">
                                    <span className="text-sm text-base-content/70">
                                        {t('chatsSelected', { count: selectedChats.length })}
                                    </span>
                                    <div className="space-x-2">
                                        <button
                                            type="button"
                                            className="btn btn-xs btn-outline"
                                            onClick={() => setSelectedChats([])}
                                            disabled={selectedChats.length === 0 || isSaving}
                                        >
                                            {t('clearAll')}
                                        </button>
                                    </div>
                                </div>
                            </div>
                        )}
                    </div>
    
                    {/* --- Action Buttons --- */}
                    <div className="flex flex-wrap justify-between items-center gap-4 pt-4 border-t border-base-300">
                        <button
                            type="submit"
                            className="btn btn-primary"
                            disabled={isSaving || isLoadingDetails}
                        >
                            {isSaving ? <span className="loading loading-spinner loading-xs"></span> : ''}
                            {isCreating ? t('createTemplate') : t('saveChanges')}
                        </button>
                        {!isCreating && selectedTemplateId && (
                            <button
                                type="button"
                                onClick={handleDeleteTemplate}
                                className="btn btn-error btn-outline"
                                disabled={isSaving || isLoadingDetails}
                            >
                                {t('deleteTemplate')}
                            </button>
                        )}
                    </div>
                </form>
            )}
    
            {/* --- Placeholder when nothing is selected --- */}
            {!selectedTemplateId && !isCreating && !isLoadingList && !error && (
                <div className="text-center p-6 border border-dashed border-base-300 rounded-md mt-6">
                    <p className="text-base-content/70">{t('selectTemplateMessage')}</p>
                </div>
            )}
        </div>
    );
};

export default TemplatesPanel;