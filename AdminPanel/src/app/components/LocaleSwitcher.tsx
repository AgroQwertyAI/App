'use client';

import { useParams } from 'next/navigation';
import { Locale } from 'next-intl';
import { useTransition } from 'react';
import { usePathname, useRouter } from '@/i18n/navigation';

type Language = {
  code: Locale;
  name: string;
  emoji: string;
};

const languages: Language[] = [
  {
    code: 'en',
    name: 'English',
    emoji: '🇬🇧',
  },
  {
    code: 'ru',
    name: 'Русский',
    emoji: '🇷🇺',
  },
];

export default function LocaleSwitcher() {
  const router = useRouter();
  const [isPending, startTransition] = useTransition();
  const pathname = usePathname();
  const params = useParams();
  
  // Get current locale from params or default to 'en'
  const currentLocale = (params.locale as Locale) || 'en';
  
  // Find current language
  const currentLanguage = languages.find(lang => lang.code === currentLocale) || languages[0];

  // Function to change the locale
  const handleLocaleChange = (nextLocale: Locale) => {
    if (nextLocale !== currentLocale) {
      startTransition(() => {
        router.replace(
          // @ts-expect-error -- TypeScript will validate that only known `params`
          // are used in combination with a given `pathname`. Since the two will
          // always match for the current route, we can skip runtime checks.
          { pathname, params },
          { locale: nextLocale }
        );
      });
    }
  };

  return (
    <div className="dropdown dropdown-end">
      {/* The button that opens the dropdown */}
      <div tabIndex={0} role="button" className="btn btn-ghost rounded-btn">
        <span className="text-xl mr-2">{currentLanguage.emoji}</span>
        <span className="text-sm text-base-content">{currentLanguage.name}</span>
        <svg 
          xmlns="http://www.w3.org/2000/svg" 
          fill="none" 
          viewBox="0 0 24 24" 
          strokeWidth={2} 
          stroke="currentColor" 
          className="w-4 h-4 ml-1 text-base-content"
        >
          <path strokeLinecap="round" strokeLinejoin="round" d="M19.5 8.25l-7.5 7.5-7.5-7.5" />
        </svg>
      </div>
      
      {/* The dropdown menu */}
      <ul tabIndex={0} className="dropdown-content menu p-2 shadow-lg bg-base-100 rounded-box z-10 w-48 mt-2">
        {languages.map((language) => (
          <li key={language.code}>
            <button
              onClick={() => handleLocaleChange(language.code)}
              className={`flex items-center gap-2 ${currentLocale === language.code ? 'bg-base-200' : ''}`}
              disabled={isPending}
            >
              <span className="text-xl">{language.emoji}</span>
              <span className='text-base-content'>{language.name}</span>
              {currentLocale === language.code && (
                <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor" className="w-4 h-4 ml-auto">
                  <path strokeLinecap="round" strokeLinejoin="round" d="M4.5 12.75l6 6 9-13.5" />
                </svg>
              )}
            </button>
          </li>
        ))}
      </ul>
    </div>
  );
}