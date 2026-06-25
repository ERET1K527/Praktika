(function () {
    "use strict";

    var TOKEN_KEY = "jobflow_token";
    var path = window.location.pathname.split("/").pop() || "index.html";
    var isAuthPage = (path === "login.html" || path === "register.html");

    function tokenExpired(t) {
        try {
            var parts = t.split(".");
            if (parts.length !== 3) return false;
            var payload = JSON.parse(atob(parts[1].replace(/-/g, "+").replace(/_/g, "/")));
            if (!payload.exp) return false;
            return (payload.exp * 1000) < Date.now();
        } catch (e) {
            return false;
        }
    }

    var token = localStorage.getItem(TOKEN_KEY);
    var authenticated = token && !tokenExpired(token);

    if (!authenticated) {
        if (token) localStorage.removeItem(TOKEN_KEY);
        if (!isAuthPage) {
            window.location.replace("login.html");
        }
        return;
    }

    // Already logged in — never show the auth pages again.
    if (isAuthPage) {
        window.location.replace("index.html");
    }
})();
