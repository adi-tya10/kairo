/**
 * Resolves the KAIRO Backend API base URL for both local development and production deployments.
 */
export const getApiBaseUrl = (): string => {
  if (typeof process !== "undefined" && process.env.NEXT_PUBLIC_API_URL) {
    const envUrl = process.env.NEXT_PUBLIC_API_URL.trim().replace(/\/$/, "");
    return envUrl.endsWith("/api/v1") ? envUrl : `${envUrl}/api/v1`;
  }
  if (typeof window !== "undefined") {
    if (window.location.hostname === "localhost" || window.location.hostname === "127.0.0.1") {
      return "http://localhost:8000/api/v1";
    }
  }
  return "https://kairo-api-ufca.onrender.com/api/v1";
};

export const API_BASE = getApiBaseUrl();
