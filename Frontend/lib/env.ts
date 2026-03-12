/**
 * Environment variables configuration
 * 
 * This file accesses environment variables that are:
 * 1. Defined in the system environment
 * 2. Set in next.config.ts 
 * 3. Or uses fallback defaults if nothing is set
 */

// Access environment variables as set in next.config.ts
// These values will be replaced at build time with values from the system environment
// or the defaults specified in next.config.ts
export const API_HOST = process.env.NEXT_PUBLIC_MEDSYNTHAI_FRONTEND_API_HOST || '127.0.0.1';
export const API_PORT = process.env.NEXT_PUBLIC_MEDSYNTHAI_FRONTEND_API_PORT || '8000';
export const TTS_PORT = process.env.NEXT_PUBLIC_MEDSYNTHAI_FRONTEND_TTS_PORT || '8003';

// Full API URL for HTTP requests
export const API_BASE_URL = `http://${API_HOST}:${API_PORT}`;

// WebSocket URLs
export const WS_BASE_URL = `ws://${API_HOST}:${API_PORT}`;
export const WS_TTS_URL = `ws://${API_HOST}:${TTS_PORT}`; 