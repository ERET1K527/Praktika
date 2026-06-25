(function () {
    "use strict";

    var TOKEN_KEY = "jobflow_token";
    var token = localStorage.getItem(TOKEN_KEY);
    var navRight = document.querySelector(".nav-right");
    if (!token || !navRight) return;

    // ── Inject panel styles + markup once ─────────────────────────────
    function injectStyles() {
        if (document.getElementById("jf-nav-styles")) return;
        var css =
            ".jf-search-panel{position:fixed;top:0;left:0;right:0;z-index:200;background:#ffffff;" +
            "box-shadow:0 14px 40px rgba(0,0,0,.18);border-bottom:1px solid rgba(0,0,0,.06);" +
            "transform:translateY(-110%);transition:transform .28s cubic-bezier(.2,.7,.3,1);}" +
            ".jf-search-panel.open{transform:translateY(0);}" +
            ".jf-search-panel-inner{max-width:1300px;margin:0 auto;padding:1rem 2rem;display:flex;gap:.8rem;flex-wrap:wrap;align-items:center;}" +
            ".jf-search-field{flex:1;min-width:200px;display:flex;align-items:center;gap:8px;background:#f3f6f9;border-radius:10px;padding:10px 14px;}" +
            ".jf-search-field i{color:#2f7eb6;}" +
            ".jf-search-field input{flex:1;border:none;background:transparent;outline:none;font-size:.95rem;color:#1f3e54;}" +
            ".jf-search-go{display:inline-flex;align-items:center;gap:8px;background:#1f6392;color:#fff;border:none;border-radius:10px;" +
            "padding:11px 20px;font-weight:600;font-size:.95rem;cursor:pointer;transition:background .2s;}" +
            ".jf-search-go:hover{background:#0e4a6e;}" +
            ".jf-search-close{background:none;border:none;color:#5d7387;font-size:1.3rem;cursor:pointer;padding:4px 8px;line-height:1;}";
        var st = document.createElement("style");
        st.id = "jf-nav-styles";
        st.textContent = css;
        document.head.appendChild(st);
    }

    function buildPanel() {
        if (document.getElementById("jfSearchPanel")) return;
        injectStyles();
        var panel = document.createElement("div");
        panel.className = "jf-search-panel";
        panel.id = "jfSearchPanel";
        panel.innerHTML =
            '<div class="jf-search-panel-inner">' +
                '<div class="jf-search-field"><i class="fas fa-search"></i>' +
                    '<input type="text" id="jfSearchQ" placeholder="Должность или профессия" autocomplete="off"></div>' +
                '<div class="jf-search-field"><i class="fas fa-map-marker-alt"></i>' +
                    '<input type="text" id="jfSearchCity" placeholder="Город" value="Брянск" autocomplete="off"></div>' +
                '<button type="button" class="jf-search-go" id="jfSearchGo"><i class="fas fa-search"></i> Найти вакансии</button>' +
                '<button type="button" class="jf-search-close" id="jfSearchClose" title="Закрыть">&times;</button>' +
            '</div>';
        document.body.appendChild(panel);

        var savedCity = localStorage.getItem("jobflow_city");
        if (savedCity) document.getElementById("jfSearchCity").value = savedCity;

        function go() {
            var s = document.getElementById("jfSearchQ").value.trim();
            var c = document.getElementById("jfSearchCity").value.trim();
            if (c) localStorage.setItem("jobflow_city", c);
            var p = new URLSearchParams();
            if (s) p.set("search", s);
            if (c) p.set("city", c);
            window.location.href = "vacancies.html" + (p.toString() ? "?" + p.toString() : "");
        }
        document.getElementById("jfSearchGo").addEventListener("click", go);
        document.getElementById("jfSearchCity").addEventListener("keydown", function (e) { if (e.key === "Enter") go(); });
        document.getElementById("jfSearchQ").addEventListener("keydown", function (e) { if (e.key === "Enter") go(); });
        document.getElementById("jfSearchClose").addEventListener("click", function () { togglePanel(false); });
    }

    function togglePanel(open) {
        var panel = document.getElementById("jfSearchPanel");
        if (!panel) return;
        if (typeof open === "boolean") {
            panel.classList.toggle("open", open);
        } else {
            panel.classList.toggle("open");
        }
        if (panel.classList.contains("open")) {
            setTimeout(function () { var q = document.getElementById("jfSearchQ"); if (q) q.focus(); }, 120);
        }
    }

    // ── Sync nav cleanup (before notifications.js runs so the bell anchors right)
    function removeByHref(hrefAttr) {
        var el = navRight.querySelector('a[href="' + hrefAttr + '"]');
        if (el && el.parentNode) el.parentNode.removeChild(el);
    }
    removeByHref("login.html");
    removeByHref("rezume.html");

    if (!navRight.querySelector('a[href="account.html"]')) {
        var acct = document.createElement("a");
        acct.href = "account.html";
        acct.innerHTML = '<i class="fas fa-user-circle"></i> Аккаунт';
        navRight.appendChild(acct);
    }

    // ── Async: validate token + apply role-based header ───────────────
    fetch("/api/auth/me", { headers: { "Authorization": "Bearer " + token } })
        .then(function (res) {
            if (res.status === 401) {
                localStorage.removeItem(TOKEN_KEY);
                window.location.replace("login.html");
                return null;
            }
            return res.json();
        })
        .then(function (user) {
            if (!user) return;
            window.jobflowUser = user;

            // ── Conditional nav: show ONLY the links allowed for this role ──
            // Allowlist (matched by visible text, which is consistent across pages
            // even where hrefs differ, e.g. Сервисы → servise.html vs "#").
            var navLinksEl = document.querySelector(".nav-links");
            if (navLinksEl) {
                var allowedLabels;
                if (user.role === "employer") {
                    allowedLabels = ["ищу сотрудника", "сервисы", "помощь"];
                } else if (user.role === "candidate") {
                    allowedLabels = ["ищу работу", "сервисы", "помощь"];
                } else {
                    // admin / unknown → keep the full menu visible.
                    allowedLabels = null;
                }

                if (allowedLabels) {
                    var navItems = navLinksEl.querySelectorAll("a");
                    Array.prototype.forEach.call(navItems, function (a) {
                        var text = (a.textContent || "").trim().toLowerCase();
                        var permitted = false;
                        for (var i = 0; i < allowedLabels.length; i++) {
                            if (text.indexOf(allowedLabels[i]) !== -1) { permitted = true; break; }
                        }
                        if (!permitted) a.style.display = "none";
                    });
                }
            }

            // "Ищу работу" navigates directly to the vacancies page (candidates only).
            if (user.role === "candidate") {
                var workLink = document.querySelector('.nav-links a[href="index.html"]');
                if (workLink) workLink.setAttribute("href", "vacancies.html");
            }

            // ── Role-based footer: hide the column that doesn't fit the role ──
            var footerCols = document.querySelectorAll("footer .footer-col");
            Array.prototype.forEach.call(footerCols, function (col) {
                var heading = (col.querySelector("h4") || {}).textContent || "";
                heading = heading.trim().toLowerCase();
                if (user.role === "candidate" && heading.indexOf("работодатель") !== -1) {
                    col.style.display = "none";
                } else if (user.role === "employer" && heading.indexOf("соискател") !== -1) {
                    col.style.display = "none";
                }
            });
        })
        .catch(function () { /* network hiccup — leave header as-is */ });

    // Public API for other scripts.
    window.JobFlowNav = {
        openSearchPanel: function () { buildPanel(); togglePanel(true); }
    };

    window.addEventListener('storage', function(e) {
        if (e.key === 'jobflow_city' && e.newValue) {
            var ci = document.getElementById('jfSearchCity');
            if (ci) ci.value = e.newValue;
        }
    });
})();
