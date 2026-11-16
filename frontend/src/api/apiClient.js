/**
 * Centralized MachineSense API Client Module
 *
 * Provides pre-configured Axios instance with automatic JWT Bearer token attachment
 * and response interception for 401 Unauthorized handling.
 */

export * from '../services/api';
export { default, apiClient } from '../services/api';

