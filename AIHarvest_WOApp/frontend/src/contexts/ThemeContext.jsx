import React, {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
} from 'react';

/**
 * Keep this key in sync with the pre-hydration script in public/index.html —
 * that script reads the same value to stamp the theme onto <html> before the
 * first paint, which is what prevents a white flash on load in dark mode.
 */
const STORAGE_KEY = 'aiharvest-theme';

const THEME_COLOR = { light: '#f5f7fa', dark: '#0b1220' };

const ThemeContext = createContext(null);

const systemPrefersDark = () =>
  typeof window !== 'undefined' &&
  typeof window.matchMedia === 'function' &&
  window.matchMedia('(prefers-color-scheme: dark)').matches;

/** The user's explicit choice, or null if they've never touched the toggle. */
const readStoredTheme = () => {
  try {
    const stored = window.localStorage.getItem(STORAGE_KEY);
    return stored === 'dark' || stored === 'light' ? stored : null;
  } catch {
    // Storage can throw outright in Safari private mode.
    return null;
  }
};

const resolveInitialTheme = () =>
  readStoredTheme() || (systemPrefersDark() ? 'dark' : 'light');

const applyTheme = (theme) => {
  const root = document.documentElement;
  root.classList.toggle('dark', theme === 'dark');

  // Drives the browser's own widgets — most visibly the native date pickers in
  // WorkOrderView, which otherwise stay blinding white over a dark dialog.
  root.style.colorScheme = theme;

  document
    .querySelector('meta[name="theme-color"]')
    ?.setAttribute('content', THEME_COLOR[theme]);
};

export const ThemeProvider = ({ children }) => {
  const [theme, setThemeState] = useState(resolveInitialTheme);

  useEffect(() => {
    applyTheme(theme);
  }, [theme]);

  // Track the OS preference, but only until the user makes a choice of their
  // own — once localStorage holds a value this bails out and stays out.
  useEffect(() => {
    if (readStoredTheme()) return undefined;
    if (typeof window.matchMedia !== 'function') return undefined;

    const query = window.matchMedia('(prefers-color-scheme: dark)');
    const handleChange = (event) => setThemeState(event.matches ? 'dark' : 'light');

    query.addEventListener('change', handleChange);
    return () => query.removeEventListener('change', handleChange);
  }, [theme]);

  const setTheme = useCallback((next) => {
    try {
      window.localStorage.setItem(STORAGE_KEY, next);
    } catch {
      // Preference just won't survive a reload; not worth failing the click.
    }
    setThemeState(next);
  }, []);

  const toggleTheme = useCallback(
    () => setTheme(theme === 'dark' ? 'light' : 'dark'),
    [theme, setTheme]
  );

  const value = useMemo(
    () => ({ theme, isDark: theme === 'dark', setTheme, toggleTheme }),
    [theme, setTheme, toggleTheme]
  );

  return <ThemeContext.Provider value={value}>{children}</ThemeContext.Provider>;
};

export const useTheme = () => {
  const context = useContext(ThemeContext);
  if (!context) {
    throw new Error('useTheme must be used within ThemeProvider');
  }
  return context;
};

export default ThemeContext;
