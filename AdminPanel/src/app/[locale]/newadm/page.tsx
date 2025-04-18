"use client";

import { useState } from 'react';

export default function NewAdminPage() {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [name, setName] = useState('');
  const [secretKey, setSecretKey] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');

  // Very basic security - require a secret key to create admin (in a real app, use better security)
  const ADMIN_SECRET_KEY = "super_secret_admin_key"; // This should come from environment variables in real scenarios

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);
    setError('');
    setMessage('');

    // Verify secret key
    if (secretKey !== ADMIN_SECRET_KEY) {
      setError('Invalid secret key');
      setIsLoading(false);
      return;
    }

    try {
      const response = await fetch('/api/users', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          username,
          password,
          name,
          role: 'admin', // Automatically setting the role to admin
        }),
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.error || 'Failed to create admin user');
      }

      setMessage('Admin user created successfully!');
      // Clear form
      setUsername('');
      setPassword('');
      setName('');
      setSecretKey('');
    } catch (error) {
      setError(error instanceof Error ? error.message : 'An unknown error occurred');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-base-200 flex items-center justify-center p-4">
      <div className="card w-full max-w-md bg-base-100 shadow-xl">
        <div className="card-body">
          <h1 className="text-2xl font-bold text-center">Create Admin User</h1>
          
          {message && (
            <div className="alert alert-success">
              <span>{message}</span>
            </div>
          )}
          
          {error && (
            <div className="alert alert-error">
              <span>{error}</span>
            </div>
          )}
          
          <form onSubmit={handleSubmit}>
            <div className="form-control">
              <label className="label">
                <span className="label-text">Secret Key</span>
              </label>
              <input
                type="password"
                placeholder="Enter secret key"
                className="input input-bordered"
                value={secretKey}
                onChange={(e) => setSecretKey(e.target.value)}
                required
              />
            </div>

            <div className="form-control">
              <label className="label">
                <span className="label-text">Username</span>
              </label>
              <input
                type="text"
                placeholder="Enter username"
                className="input input-bordered"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                required
              />
            </div>
            
            <div className="form-control">
              <label className="label">
                <span className="label-text">Password</span>
              </label>
              <input
                type="password"
                placeholder="Enter password"
                className="input input-bordered"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
              />
            </div>
            
            <div className="form-control">
              <label className="label">
                <span className="label-text">Full Name</span>
              </label>
              <input
                type="text"
                placeholder="Enter full name"
                className="input input-bordered"
                value={name}
                onChange={(e) => setName(e.target.value)}
                required
              />
            </div>
            
            <div className="form-control mt-6">
              <button
                type="submit"
                className="btn btn-primary"
                disabled={isLoading}
              >
                {isLoading ? <span className="loading loading-spinner"></span> : 'Create Admin'}
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  );
}