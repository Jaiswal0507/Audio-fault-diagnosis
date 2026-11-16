/**
 * MachineSense API Client Service
 *
 * Configures Axios HTTP connection to the FastAPI backend (http://localhost:8000/api/v1)
 * and exposes methods for audio analysis, authentication, and health monitoring.
 * 
 */

import axios from 'axios';

const API_BASE_URL =
  (typeof import.meta !== 'undefined' &&
    import.meta.env &&
    import.meta.env.VITE_API_URL) ||
  'http://localhost:8000/api/v1';

export const apiClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000, // 30-second timeout for audio upload and DSP processing
  headers: {
    Accept: 'application/json',
  },
});

// Request interceptor to automatically attach Authorization Bearer token from localStorage
apiClient.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// Response interceptor to catch 401 Unauthorized errors and automatically clear token / redirect to login
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response && error.response.status === 401) {
      localStorage.removeItem('token');
      localStorage.removeItem('user');
      if (typeof window !== 'undefined' && window.location.pathname !== '/' && window.location.pathname !== '/login') {
        window.location.href = '/';
      }
    }
    return Promise.reject(error);
  }
);

/**
 * Register a new Organization and Admin User.
 *
 * @param {string} email - Administrator email
 * @param {string} password - Account password (min 6 chars)
 * @param {string} organizationName - Tenant organization title
 * @returns {Promise<Object>} Registration response containing token and user profile
 */
export async function registerUser(email, password, organizationName) {
  try {
    const response = await apiClient.post('/auth/register', {
      email: email.trim().toLowerCase(),
      password,
      organization_name: organizationName.trim(),
    });
    return response.data;
  } catch (error) {
    const message =
      error.response?.data?.detail ||
      error.message ||
      'Registration failed. Please try again.';
    throw new Error(typeof message === 'string' ? message : JSON.stringify(message));
  }
}

/**
 * Authenticate user and receive JWT access token using OAuth2PasswordRequestForm.
 *
 * @param {string} email - User email (as OAuth2 username)
 * @param {string} password - User password
 * @returns {Promise<Object>} Token response containing access_token and user info
 */
export async function loginUser(email, password) {
  const formData = new URLSearchParams();
  formData.append('username', email.trim().toLowerCase());
  formData.append('password', password);

  try {
    const response = await apiClient.post('/auth/login', formData, {
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded',
      },
    });
    return response.data;
  } catch (error) {
    const message =
      error.response?.data?.detail ||
      error.message ||
      'Invalid email or password.';
    throw new Error(typeof message === 'string' ? message : JSON.stringify(message));
  }
}

/**
 * Fetch authenticated current user profile.
 *
 * @returns {Promise<Object>} Current user data
 */
export async function getCurrentUser() {
  try {
    const response = await apiClient.get('/auth/me');
    return response.data;
  } catch (error) {
    const message = error.response?.data?.detail || error.message || 'Failed to fetch user profile';
    throw new Error(typeof message === 'string' ? message : JSON.stringify(message));
  }
}

/**
 * Upload an audio recording (Blob or File) and trigger DSP feature extraction & ML diagnosis.
 *
 * @param {Blob|File} audioBlob - Raw audio blob or file recorded from browser or uploaded
 * @param {string} machineId - Machine identifier (e.g. 'MCH-001')
 * @param {string} [machineType='bearing'] - Optional machine category
 * @returns {Promise<Object>} Analysis result JSON conforming to PRD Section 50
 */
export async function analyzeMachineAudio(audioBlob, machineId, machineType = 'bearing') {
  if (!audioBlob) {
    throw new Error('Audio recording data is required for analysis.');
  }

  if (!machineId || typeof machineId !== 'string' || !machineId.trim()) {
    throw new Error('Valid machineId is required.');
  }

  const formData = new FormData();

  // Determine appropriate filename with audio extension
  let filename = 'recording.wav';
  if (audioBlob instanceof File && audioBlob.name) {
    filename = audioBlob.name;
  } else if (audioBlob.type && audioBlob.type.includes('webm')) {
    filename = 'recording.webm';
  } else if (audioBlob.type && audioBlob.type.includes('ogg')) {
    filename = 'recording.ogg';
  }

  formData.append('file', audioBlob, filename);
  formData.append('machine_id', machineId.trim());
  if (machineType) {
    formData.append('machine_type', machineType.trim());
  }

  try {
    const response = await apiClient.post('/analyze', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    return response.data;
  } catch (error) {
    let errorMessage = 'Audio diagnosis failed';
    if (error.response) {
      // Backend returned HTTP error status (400, 422, 500)
      const detail = error.response.data?.detail;
      errorMessage = typeof detail === 'string' ? detail : JSON.stringify(detail || error.response.data);
    } else if (error.request) {
      // Network unreachable
      errorMessage = 'Unable to reach MachineSense backend at ' + API_BASE_URL;
    } else {
      errorMessage = error.message;
    }

    const enhancedError = new Error(errorMessage);
    enhancedError.originalError = error;
    enhancedError.status = error.response?.status;
    throw enhancedError;
  }
}

/**
 * Query backend health status.
 *
 * @returns {Promise<Object>} Health check status response
 */
export async function checkHealth() {
  try {
    const response = await apiClient.get('/health');
    return response.data;
  } catch (error) {
    throw new Error(`Health check failed: ${error.message}`);
  }
}

/**
 * Fetch analysis history records for a specific machine.
 * 
 *
 * @param {string} machineId - Machine identifier (e.g. 'MCH-001')
 * @param {number} [limit=50] - Maximum records to return
 * @param {number} [offset=0] - Offset
 * @returns {Promise<Object>} History data containing analyses array and total count
 */
export async function getMachineHistory(machineId = 'MCH-001', limit = 50, offset = 0) {
  const targetId = (machineId && String(machineId).trim()) || 'MCH-001';
  try {
    const response = await apiClient.get(`/machines/${encodeURIComponent(targetId)}/history`, {
      params: { limit, offset },
    });
    return response.data;
  } catch (error) {
    const message =
      error.response?.data?.detail ||
      error.message ||
      `Failed to fetch history for machine ${targetId}`;
    const err = new Error(typeof message === 'string' ? message : JSON.stringify(message));
    err.status = error.response?.status;
    throw err;
  }
}

/**
 * Fetch all diagnosis records across all machines.
 *
 * @param {number} [limit=50] - Maximum records
 * @param {number} [offset=0] - Offset
 * @param {string|null} [condition=null] - Optional condition filter ('normal', 'anomaly', 'fault')
 * @returns {Promise<Object>} History data
 */
export async function getAllHistory(limit = 50, offset = 0, condition = null) {
  try {
    const params = { limit, offset };
    if (condition) params.condition = condition;
    const response = await apiClient.get('/history', { params });
    return response.data;
  } catch (error) {
    const message = error.response?.data?.detail || error.message || 'Failed to fetch global history';
    throw new Error(typeof message === 'string' ? message : JSON.stringify(message));
  }
}

export default {
  apiClient,
  registerUser,
  loginUser,
  getCurrentUser,
  analyzeMachineAudio,
  checkHealth,
  getMachineHistory,
  getAllHistory,
};
