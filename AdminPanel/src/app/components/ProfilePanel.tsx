'use client';

import { useState, useEffect, FormEvent } from 'react';
import { useSession } from 'next-auth/react';
import { useTranslations } from 'next-intl';

export default function ProfilePanel() {
    const { data: session, status, update: updateSession } = useSession();
    const t = useTranslations('profile');

    const [name, setName] = useState('');
    const [password, setPassword] = useState('');
    const [confirmPassword, setConfirmPassword] = useState('');
    const [currentName, setCurrentName] = useState('');

    const [isLoading, setIsLoading] = useState(false);
    const [isFetching, setIsFetching] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [successMessage, setSuccessMessage] = useState<string | null>(null);

    // Fetch user data from API when component mounts
    useEffect(() => {
        const fetchUserData = async () => {
            if (status !== 'authenticated' || !session?.user?.id) return;
            
            setIsFetching(true);
            try {
                const response = await fetch(`/api/users/${session.user.id}`);
                
                if (!response.ok) {
                    throw new Error(t('errorFetchingProfile'));
                }
                
                const userData = await response.json();
                setName(userData.name);
                setCurrentName(userData.name);
                
            } catch (err: any) {
                console.error("Failed to fetch user profile:", err);
                setError(err.message || t('errorFetchingProfile'));
            } finally {
                setIsFetching(false);
            }
        };

        fetchUserData();
    }, [session, status, t]);

    const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
        event.preventDefault();
        setError(null);
        setSuccessMessage(null);

        if (status !== 'authenticated' || !session?.user?.id) {
            setError(t('errorMissingUserId'));
            return;
        }

        if (password && password !== confirmPassword) {
            setError(t('errorPasswordMismatch'));
            return;
        }

        setIsLoading(true);

        const userId = session.user.id;
        const payload: { name: string; password?: string } = { name };

        // Only include password if it's being changed
        if (password) {
            payload.password = password;
        }

        try {
            const response = await fetch(`/api/users/${userId}`, {
                method: 'PATCH',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(payload),
            });

            const result = await response.json();

            if (!response.ok) {
                throw new Error(result.error || t('errorUpdateFailed'));
            }

            setSuccessMessage(t('successUpdate'));
            
            if (payload.name !== currentName) {
                setCurrentName(payload.name);
                
                // Update the session data so other components get the new name
                await updateSession({
                    ...session,
                    user: {
                        ...session.user,
                        name: payload.name
                    }
                });
            }
            
            // Clear password fields after successful update
            setPassword('');
            setConfirmPassword('');

        } catch (err: any) {
            console.error("Profile update failed:", err);
            setError(err.message || t('errorUpdateFailed'));
        } finally {
            setIsLoading(false);
        }
    };

    // Handle loading states
    if (status === 'loading' || isFetching) {
        return <div className="text-center text-base-content p-4">{t('loadingUser')}</div>;
    }

    if (status === 'unauthenticated' || !session?.user) {
        return <div className="text-center text-error p-4">{t('sessionError')}</div>;
    }

    return (
        <div className="card bg-base-100 shadow-xl w-full max-w-lg mx-auto">
            <div className="card-body">
                <h2 className="card-title text-base-content mb-4">{t('title')}</h2>

                {/* Display Current Name */}
                <p className="mb-4">
                    <span className="font-semibold text-base-content">{t('currentNameLabel')}:</span>
                    <span className="ml-2 text-base-content">{currentName || 'N/A'}</span>
                </p>

                <form onSubmit={handleSubmit} className="space-y-4">
                    {/* Name Input */}
                    <div className="form-control">
                        <label className="label">
                            <span className="label-text text-base-content">{t('nameLabel')}</span>
                        </label>
                        <input
                            type="text"
                            placeholder={t('namePlaceholder')}
                            className="input input-bordered w-full text-base-content"
                            value={name}
                            onChange={(e) => setName(e.target.value)}
                            required
                            disabled={isLoading}
                        />
                    </div>

                    {/* Password Input */}
                    <div className="form-control">
                        <label className="label">
                            <span className="label-text text-base-content">{t('passwordLabel')}</span>
                        </label>
                        <input
                            type="password"
                            placeholder={t('passwordPlaceholder')}
                            className="input input-bordered w-full text-base-content"
                            value={password}
                            onChange={(e) => setPassword(e.target.value)}
                            disabled={isLoading}
                            autoComplete="new-password"
                        />
                    </div>

                    {/* Confirm Password Input */}
                    {password && (
                        <div className="form-control">
                            <label className="label">
                                <span className="label-text text-base-content">{t('confirmPasswordLabel')}</span>
                            </label>
                            <input
                                type="password"
                                placeholder={t('confirmPasswordPlaceholder')}
                                className="input input-bordered w-full text-base-content"
                                value={confirmPassword}
                                onChange={(e) => setConfirmPassword(e.target.value)}
                                required
                                disabled={isLoading}
                                autoComplete="new-password"
                            />
                        </div>
                    )}

                    {/* Error Message */}
                    {error && (
                        <div role="alert" className="alert alert-error text-sm p-2">
                            <svg xmlns="http://www.w3.org/2000/svg" className="stroke-current shrink-0 h-6 w-6" fill="none" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M10 14l2-2m0 0l2-2m-2 2l-2-2m2 2l2 2m7-2a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>
                            <span className="text-error-content">{error}</span>
                        </div>
                    )}

                    {/* Success Message */}
                    {successMessage && (
                         <div role="alert" className="alert alert-success text-sm p-2">
                            <svg xmlns="http://www.w3.org/2000/svg" className="stroke-current shrink-0 h-6 w-6" fill="none" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>
                            <span className="text-success-content">{successMessage}</span>
                        </div>
                    )}

                    {/* Submit Button */}
                    <div className="card-actions justify-end mt-6">
                        <button
                            type="submit"
                            className="btn btn-primary text-base-content"
                            disabled={isLoading || status !== 'authenticated'}
                        >
                            {isLoading ? (
                                <>
                                    <span className="loading loading-spinner loading-xs"></span>
                                    {t('updatingButton')}
                                </>
                            ) : (
                                t('updateButton')
                            )}
                        </button>
                    </div>
                </form>
            </div>
        </div>
    );
}