import { useEffect, useState } from 'react'

type Theme = 'dark' | 'light'
const STORAGE_KEY = 'life100-theme'

function applyTheme(theme: Theme) {
  document.documentElement.setAttribute('data-theme', theme)
}

export function useTheme() {
  const [theme, setThemeState] = useState<Theme>(() => (localStorage.getItem(STORAGE_KEY) as Theme) || 'dark')

  useEffect(() => {
    applyTheme(theme)
  }, [theme])

  function setTheme(t: Theme) {
    localStorage.setItem(STORAGE_KEY, t)
    setThemeState(t)
  }

  return { theme, toggle: () => setTheme(theme === 'dark' ? 'light' : 'dark'), setTheme }
}
