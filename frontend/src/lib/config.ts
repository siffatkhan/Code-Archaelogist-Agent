/**
 * Central switch for mock vs. real data. Pages/components should branch on
 * this rather than importing mocks directly into services/*.ts.
 *
 * Defaults to mock data whenever the API base URL isn't configured, so the
 * app remains demoable before the FastAPI backend is wired up. Set
 * VITE_USE_MOCK_DATA=false explicitly once the backend is ready, or simply
 * configure VITE_API_BASE_URL — either is sufficient to go live.
 */
const explicitFlag = import.meta.env.VITE_USE_MOCK_DATA as string | undefined;
const hasApiBaseUrl = Boolean(import.meta.env.VITE_API_BASE_URL);

export const USE_MOCK_DATA = explicitFlag ? explicitFlag === "true" : !hasApiBaseUrl;
