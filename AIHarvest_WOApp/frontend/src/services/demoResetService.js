import api from './api';

/**
 * Client for the demo reset endpoints.
 *
 * The passphrase is passed per call rather than installed on the shared axios
 * instance: every other request in the app goes through the same instance, and
 * an interceptor would attach the reset token to all of them.
 */

const TOKEN_HEADER = 'X-Demo-Reset-Token';

// sessionStorage, not localStorage: the passphrase should not outlive the tab.
// The form values are remembered separately, and those are not secret.
const TOKEN_KEY = 'aiharvest.demoReset.token';

// A reset is a few thousand inserts through the ORM. 75 machines lands in about
// two seconds, but 500 is a different proposition, and the shared axios default
// of 30s would abort a request the server is still happily working on.
const RESET_TIMEOUT_MS = 300000;

export const tokenStore = {
  get: () => {
    try {
      return sessionStorage.getItem(TOKEN_KEY) || '';
    } catch {
      // Private browsing modes can throw on storage access.
      return '';
    }
  },
  set: (token) => {
    try {
      sessionStorage.setItem(TOKEN_KEY, token);
    } catch {
      /* held in component state for this page view either way */
    }
  },
  clear: () => {
    try {
      sessionStorage.removeItem(TOKEN_KEY);
    } catch {
      /* nothing to do */
    }
  },
};

const authHeader = (token) => ({ headers: { [TOKEN_HEADER]: token } });

const demoResetService = {
  /**
   * Prefill values plus current row counts.
   *
   * The page also uses this to check the passphrase before showing the form --
   * a 200 here means the token is good.
   */
  getDefaults: async (token) => {
    const response = await api.get('/admin/demo-reset/defaults', authHeader(token));
    return response.data;
  },

  /** Run the reset. Destructive. */
  runReset: async (token, payload) => {
    const response = await api.post('/admin/demo-reset', payload, {
      ...authHeader(token),
      timeout: RESET_TIMEOUT_MS,
    });
    return response.data;
  },
};

/**
 * Turn an axios error into one sentence worth showing.
 *
 * FastAPI's `detail` is a string for HTTPException but an array of objects for
 * a 422, so a naive render puts "[object Object]" in front of the user at
 * exactly the moment they need to know which field is wrong.
 */
export const describeError = (error) => {
  const detail = error?.response?.data?.detail;

  if (typeof detail === 'string') return detail;

  if (Array.isArray(detail)) {
    return detail
      .map((item) => {
        // Strip pydantic's "Value error, " prefix -- the message after it is
        // already written for a human.
        const msg = (item?.msg || '').replace(/^Value error,\s*/, '');
        const field = Array.isArray(item?.loc)
          ? item.loc.filter((part) => part !== 'body').join('.')
          : '';
        return field && field !== msg ? `${field}: ${msg}` : msg;
      })
      .filter(Boolean)
      .join(' ');
  }

  if (error?.code === 'ECONNABORTED') {
    return 'The reset timed out. It may still be running -- check the row counts before trying again.';
  }

  return error?.message || 'Something went wrong.';
};

export default demoResetService;
