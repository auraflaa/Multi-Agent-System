/**
 * API Helper - Centralized API key management for frontend
 * Stores API key in localStorage and includes it in all requests
 */

// Get API key from localStorage
function getApiKey() {
    return localStorage.getItem('api_key') || '';
}

// Set API key in localStorage
function setApiKey(key) {
    if (key) {
        localStorage.setItem('api_key', key);
    } else {
        localStorage.removeItem('api_key');
    }
}

// Create headers with API key if available
function getApiHeaders(additionalHeaders = {}) {
    const headers = { ...additionalHeaders };
    const apiKey = getApiKey();
    if (apiKey) {
        headers['X-API-Key'] = apiKey;
    }
    return headers;
}

// Wrapper for fetch with API key
async function apiFetch(url, options = {}) {
    const headers = getApiHeaders(options.headers || {});
    return fetch(url, {
        ...options,
        headers: {
            ...headers,
            ...(options.headers || {})
        }
    });
}

