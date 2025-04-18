'use client'

import { useState, FormEvent } from 'react'
import { signIn } from 'next-auth/react'
import { useRouter } from 'next/navigation'
import { useTranslations } from 'next-intl'

export default function SignIn() {
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const router = useRouter()
  const t = useTranslations('signin')

  const handleSubmit = async (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault()
    setLoading(true)
    setError('')

    try {
      const result = await signIn('credentials', {
        username,
        password,
        redirect: false,
      })

      if (result?.error) {
        setError(t('invalidCredentials'))
        setLoading(false)
      } else {
        router.push('/dashboard')
      }
    } catch {
      setError(t('errorMessage'))
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-base-200 flex items-center justify-center px-4">
      <div className="card w-full max-w-md bg-base-100 shadow-xl">
        <div className="card-body ">
          <div className="text-center mb-4">
            <h1 className="text-3xl font-bold text-primary">{t('welcomeBack')}</h1>
            <p className="text-base-content mt-2">{t('signInContinue')}</p>
          </div>

          {error && (
            <div className="alert alert-error mb-4">
              <svg xmlns="http://www.w3.org/2000/svg" className="stroke-current shrink-0 h-6 w-6" fill="none" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M10 14l2-2m0 0l2-2m-2 2l-2-2m2 2l2 2m7-2a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              <span>{error}</span>
            </div>
          )}

          <form onSubmit={handleSubmit} className='w-full'>
            <div className="form-control">
              <input
                type="text"
                placeholder={t('usernamePlaceholder')}
                className="input input-bordered text-base-content w-100"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                required
              />
            </div>
            
            <div className="form-control mt-4">
              <input
                type="password"
                placeholder={t('passwordPlaceholder')}
                className="input input-bordered text-base-content w-100"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
              />
            </div>
            
            <div className="form-control mt-6 flex w-100">
              <button
                className={`flex-1 btn btn-primary`}
                type="submit"
                disabled={loading}
              >
                {loading ? t('signingIn') : t('signIn')}
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  )
}