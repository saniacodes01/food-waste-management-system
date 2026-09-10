/* Tiny API client + session helpers for the Food Waste Management backend.
   Everything is namespaced under window.FW to avoid clashing with page scripts. */
(function () {
  // Where the FastAPI backend lives. Override by setting window.API_BASE before
  // this script loads, or with ?api=... in the URL (handy for testing).
  const API_BASE = (() => {
    const q = new URLSearchParams(location.search).get("api");
    if (q) localStorage.setItem("fw_api", q);
    return window.API_BASE || localStorage.getItem("fw_api") || "http://localhost:8000";
  })();

  const TOKEN_KEY = "fw_token";
  const USER_KEY = "fw_user";

  const session = {
    get token() { return localStorage.getItem(TOKEN_KEY); },
    get user() {
      try { return JSON.parse(localStorage.getItem(USER_KEY)); }
      catch { return null; }
    },
    set({ access_token, user }) {
      localStorage.setItem(TOKEN_KEY, access_token);
      localStorage.setItem(USER_KEY, JSON.stringify(user));
    },
    patchUser(u) { localStorage.setItem(USER_KEY, JSON.stringify(u)); },
    clear() { localStorage.removeItem(TOKEN_KEY); localStorage.removeItem(USER_KEY); },
    get role() { return this.user && this.user.role; },
  };

  class ApiError extends Error {
    constructor(message, status) { super(message); this.status = status; }
  }

  async function request(method, path, body) {
    const headers = { "Content-Type": "application/json" };
    if (session.token) headers.Authorization = `Bearer ${session.token}`;
    let res;
    try {
      res = await fetch(API_BASE + path, {
        method,
        headers,
        body: body === undefined ? undefined : JSON.stringify(body),
      });
    } catch {
      throw new ApiError(`Can't reach the server at ${API_BASE}. Is the backend running?`, 0);
    }
    if (res.status === 204) return null;
    const data = await res.json().catch(() => ({}));
    if (!res.ok) {
      if (res.status === 401 && session.token) session.clear();
      const detail = Array.isArray(data.detail)
        ? data.detail.map((d) => d.msg).join(", ")
        : data.detail;
      throw new ApiError(detail || `Request failed (${res.status})`, res.status);
    }
    return data;
  }

  const api = {
    base: API_BASE,
    get: (p) => request("GET", p),
    post: (p, b) => request("POST", p, b),
    patch: (p, b) => request("PATCH", p, b),
    register: (b) => request("POST", "/api/auth/register", b),
    login: (b) => request("POST", "/api/auth/login", b),
    me: () => request("GET", "/api/auth/me"),
    updateMe: (b) => request("PATCH", "/api/auth/me", b),
  };

  /** Ask the browser for the current location. Resolves {lat,lng} or null. */
  function getLocation() {
    return new Promise((resolve) => {
      if (!navigator.geolocation) return resolve(null);
      navigator.geolocation.getCurrentPosition(
        (pos) => resolve({
          lat: +pos.coords.latitude.toFixed(6),
          lng: +pos.coords.longitude.toFixed(6),
        }),
        () => resolve(null),
        { enableHighAccuracy: true, timeout: 8000 },
      );
    });
  }

  function requireAuth(role) {
    if (!session.token) { location.href = "login.html"; return false; }
    if (role && session.role !== role) { location.href = "app.html"; return false; }
    return true;
  }

  function logout() { session.clear(); location.href = "index.html"; }

  window.FW = { api, session, ApiError, getLocation, requireAuth, logout };
})();
