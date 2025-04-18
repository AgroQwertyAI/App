'use client';

import { useState, useEffect } from 'react';
import { useSession } from 'next-auth/react';
import { PlusCircle, Trash2, Save } from 'lucide-react';
import { useTranslations } from 'next-intl';

// Types
interface User {
  id: string;
  username: string;
  name: string;
  role: 'admin' | 'user';
}

interface NewUserForm {
  username: string;
  name: string;
  password: string;
  role: 'admin' | 'user';
}

export default function UsersPanel() {
  const t = useTranslations('users');
  const { data: session, status } = useSession();
  const [users, setUsers] = useState<User[]>([]);
  const [isAdmin, setIsAdmin] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showAddUser, setShowAddUser] = useState(false);
  const [newUser, setNewUser] = useState<NewUserForm>({
    username: '',
    name: '',
    password: '',
    role: 'user'
  });

  // Fetch current user and all users
  useEffect(() => {
    async function fetchData() {
      if (status !== 'authenticated' || !session?.user?.id) {
        setIsLoading(false);
        return;
      }

      setIsLoading(true);
      setError(null);

      try {
        // 1. Get current user to check if admin
        const currentUserResponse = await fetch(`/api/users/${session.user.id}`);
        if (!currentUserResponse.ok) {
          throw new Error(t('errorFetchingCurrentUser'));
        }
        const currentUser = await currentUserResponse.json();
        const userIsAdmin = currentUser.role === 'admin';
        setIsAdmin(userIsAdmin);

        // 2. Get all users
        const allUsersResponse = await fetch('/api/users');
        if (!allUsersResponse.ok) {
          throw new Error(t('errorFetchingUsers'));
        }
        const allUsers = await allUsersResponse.json();
        setUsers(allUsers);
      } catch (err: any) {
        setError(err.message || t('errorGenericFetch'));
        console.error(err);
      } finally {
        setIsLoading(false);
      }
    }

    fetchData();
  }, [session, status, t]);

  const handleAddUser = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!isAdmin) return;

    setIsLoading(true);
    setError(null);

    try {
      // Create user
      const createUserResponse = await fetch('/api/users', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(newUser),
      });

      if (!createUserResponse.ok) {
        const errorData = await createUserResponse.json().catch(() => ({ error: t('errorCreateUser') }));
        throw new Error(errorData.error || t('errorCreateUser'));
      }

      const createdUser = await createUserResponse.json();

      // Reset form and add new user to the list
      setNewUser({ username: '', name: '', password: '', role: 'user' });
      setShowAddUser(false);
      setUsers(prevUsers => [...prevUsers, createdUser]);
    } catch (err: any) {
      setError(err.message || t('errorGenericAction'));
      console.error(err);
    } finally {
      setIsLoading(false);
    }
  };

  const handleDeleteUser = async (userIdToDelete: string) => {
    if (!isAdmin || userIdToDelete === session?.user?.id) return;

    if (!confirm(t('deleteConfirm'))) return;

    setIsLoading(true);
    setError(null);

    try {
      const deleteUserResponse = await fetch(`/api/users?id=${userIdToDelete}`, {
        method: 'DELETE',
      });

      if (!deleteUserResponse.ok) {
        throw new Error(t('errorDeleteUserAccount'));
      }

      // Update local state
      setUsers(prevUsers => prevUsers.filter(u => u.id !== userIdToDelete));
    } catch (err: any) {
      setError(err.message || t('errorGenericAction'));
      console.error(err);
    } finally {
      setIsLoading(false);
    }
  };

  // --- Render Logic ---

  if (status === 'loading' || (status === 'authenticated' && isLoading)) {
    return (
      <div className="flex justify-center items-center min-h-[300px]">
        <span className="loading loading-spinner loading-lg text-base-content" aria-label={t('loading')}></span>
      </div>
    );
  }

  if (status === 'unauthenticated') {
    return (
      <div className="card bg-base-200 shadow-xl">
        <div className="card-body">
          <h2 className="card-title text-base-content">{t('accessDeniedTitle')}</h2>
          <p className="text-base-content">{t('accessDeniedMessage')}</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="card bg-base-200 shadow-xl">
        <div className="card-body">
          <div className="alert alert-error">
            <span className="text-error-content">{error}</span>
          </div>
        </div>
      </div>
    );
  }

  // --- Main Content Render ---
  return (
    <div className="card bg-base-100 shadow-lg mb-6">
      <div className="card-body">

        {!isAdmin && (
          <div className="alert alert-info mt-4">
            <span className="text-info-content">{t('viewOnlyMessage')}</span>
          </div>
        )}

        {/* User list */}
        <div className="overflow-x-auto mt-4">
          <table className="table w-full">
            <thead>
              <tr>
                <th className="text-base-content">{t('table.username')}</th>
                <th className="text-base-content">{t('table.name')}</th>
                <th className="text-base-content">{t('table.role')}</th>
                {isAdmin && <th className="text-base-content">{t('table.actions')}</th>}
              </tr>
            </thead>
            <tbody>
              {users.map((user) => {
                const roleText = user.role === 'admin'
                  ? t('table.roleAdmin')
                  : t('table.roleUser');

                const canDelete = isAdmin && user.role !== 'admin' && user.id !== session?.user?.id;

                return (
                  <tr key={user.id}>
                    <td className="text-base-content">{user.username}</td>
                    <td className="text-base-content">{user.name}</td>
                    <td className="text-base-content">{roleText}</td>
                    {isAdmin && (
                      <td>
                        {canDelete ? (
                          <button
                            key={`delete-btn-${user.id}`}
                            onClick={() => handleDeleteUser(user.id)}
                            className="btn btn-xs btn-error btn-outline"
                            aria-label={t('buttons.deleteUserAriaLabel', { username: user.username })}
                          >
                            <Trash2 size={14} />
                          </button>
                        ) : (
                          <span
                            key={`status-${user.id}`}
                            className="text-xs text-base-content/70 italic"
                          >
                            {user.id === session?.user?.id
                              ? t('table.currentUser')
                              : t('table.adminUser')}
                          </span>
                        )}
                      </td>
                    )}
                  </tr>
                );
              })}
              {users.length === 0 && (
                <tr key="no-users-row">
                  <td colSpan={isAdmin ? 4 : 3} className="text-center text-base-content/70 italic py-4">
                    {t('table.noUsers')}
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>

        {/* Add user section (only for admins) */}
        {isAdmin && (
          <>
            {!showAddUser ? (
              <button
                className="btn btn-primary mt-6"
                onClick={() => setShowAddUser(true)}
              >
                <PlusCircle size={18} className="mr-2" /> {t('buttons.addUser')}
              </button>
            ) : (
              <div className="card bg-base-100 shadow-md mt-6 p-4">
                <h3 className="font-semibold text-lg mb-3 text-base-content">{t('addUserForm.title')}</h3>
                <form onSubmit={handleAddUser}>
                  <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-4">
                    <div className="form-control">
                      <label className="label pb-1">
                        <span className="label-text text-base-content font-medium">{t('addUserForm.usernameLabel')}</span>
                      </label>
                      <input
                        type="text"
                        placeholder={t('addUserForm.usernamePlaceholder')}
                        className="text-base-content input input-bordered input-sm w-full"
                        value={newUser.username}
                        onChange={(e) => setNewUser({ ...newUser, username: e.target.value })}
                        required
                        autoComplete="off"
                      />
                    </div>

                    <div className="form-control">
                      <label className="label pb-1">
                        <span className="label-text text-base-content font-medium">{t('addUserForm.nameLabel')}</span>
                      </label>
                      <input
                        type="text"
                        placeholder={t('addUserForm.namePlaceholder')}
                        className="text-base-content input input-bordered input-sm w-full"
                        value={newUser.name}
                        onChange={(e) => setNewUser({ ...newUser, name: e.target.value })}
                        required
                        autoComplete="off"
                      />
                    </div>

                    <div className="form-control">
                      <label className="label pb-1">
                        <span className="label-text text-base-content font-medium">{t('addUserForm.passwordLabel')}</span>
                      </label>
                      <input
                        type="password"
                        placeholder={t('addUserForm.passwordPlaceholder')}
                        className="text-base-content input input-bordered input-sm w-full"
                        value={newUser.password}
                        onChange={(e) => setNewUser({ ...newUser, password: e.target.value })}
                        required
                        minLength={8}
                        autoComplete="new-password"
                      />
                    </div>

                    <div className="form-control">
                      <label className="label pb-1">
                        <span className="label-text text-base-content font-medium">{t('addUserForm.roleLabel')}</span>
                      </label>
                      <select
                        className="text-base-content select select-bordered select-sm w-full"
                        value={newUser.role}
                        onChange={(e) => setNewUser({ ...newUser, role: e.target.value as 'admin' | 'user' })}
                        required
                      >
                        <option value="user">{t('addUserForm.roleUser')}</option>
                        <option value="admin">{t('addUserForm.roleAdmin')}</option>
                      </select>
                    </div>
                  </div>

                  <div className="flex flex-wrap gap-2 mt-4">
                    <button type="submit" className="btn btn-sm btn-primary">
                      <Save size={16} className="mr-1" /> {t('buttons.saveUser')}
                    </button>
                    <button
                      type="button"
                      className="btn btn-sm"
                      onClick={() => {
                        setShowAddUser(false);
                        setNewUser({ username: '', name: '', password: '', role: 'user' });
                      }}
                    >
                      {t('buttons.cancel')}
                    </button>
                  </div>
                </form>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}