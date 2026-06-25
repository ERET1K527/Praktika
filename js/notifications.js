(function () {
    'use strict';

    var TOKEN_KEY = 'jobflow_token';
    var POLL_INTERVAL = 30000;     // fallback poll interval (ms)
    var WS_RETRY_INTERVAL = 3000;  // initial reconnect delay (ms)
    var WS_RETRY_MAX = 30000;      // cap for exponential backoff (ms)

    var token = localStorage.getItem(TOKEN_KEY);
    var navRight = document.querySelector('.nav-right');
    if (!token || !navRight) return;

    var notifications = [];
    var unreadCount = 0;
    var dropdownOpen = false;
    var ws = null;
    var wsRetry = null;
    var pollTimer = null;
    var heartbeatTimer = null;
    var wsRetryDelay = WS_RETRY_INTERVAL;
    var loggedOut = false;

    // ── Build UI ──────────────────────────────────────────────────────
    var wrapper = document.createElement('div');
    wrapper.className = 'jf-notif';
    wrapper.innerHTML =
        '<button type="button" class="jf-notif-bell" aria-label="Уведомления">' +
            '<i class="fas fa-bell"></i>' +
            '<span class="jf-notif-badge" style="display:none;">0</span>' +
        '</button>' +
        '<div class="jf-notif-dropdown" style="display:none;">' +
            '<div class="jf-notif-head">' +
                '<span>Уведомления</span>' +
                '<button type="button" class="jf-notif-readall">Прочитать все</button>' +
            '</div>' +
            '<div class="jf-notif-list"></div>' +
            '<a class="jf-notif-foot" href="account.html#applications">Все уведомления</a>' +
        '</div>';

    // Insert the bell right before the account/login link, fallback to first.
    var anchorLink = navRight.querySelector('a[href*="account.html"], a[href="login.html"]');
    if (anchorLink) {
        navRight.insertBefore(wrapper, anchorLink);
    } else {
        navRight.insertBefore(wrapper, navRight.firstChild);
    }

    var bellBtn = wrapper.querySelector('.jf-notif-bell');
    var badge = wrapper.querySelector('.jf-notif-badge');
    var dropdown = wrapper.querySelector('.jf-notif-dropdown');
    var listEl = wrapper.querySelector('.jf-notif-list');
    var readAllBtn = wrapper.querySelector('.jf-notif-readall');

    // ── Helpers ───────────────────────────────────────────────────────
    function authHeaders() {
        return { 'Authorization': 'Bearer ' + token };
    }

    function handleUnauthorized() {
        if (loggedOut) return;
        loggedOut = true;
        if (pollTimer) clearInterval(pollTimer);
        if (wsRetry) clearTimeout(wsRetry);
        stopHeartbeat();
        if (ws) { try { ws.close(); } catch (e) {} }
        localStorage.removeItem(TOKEN_KEY);
        window.location.href = 'login.html';
    }

    function escapeHtml(str) {
        var div = document.createElement('div');
        div.textContent = str == null ? '' : String(str);
        return div.innerHTML;
    }

    function timeAgo(dateStr) {
        if (!dateStr) return '';
        var d = new Date(dateStr);
        var diff = Math.floor((Date.now() - d.getTime()) / 1000);
        if (diff < 60) return 'только что';
        if (diff < 3600) return Math.floor(diff / 60) + ' мин назад';
        if (diff < 86400) return Math.floor(diff / 3600) + ' ч назад';
        return d.toLocaleDateString('ru-RU');
    }

    function notifyIcon(type) {
        if (type === 'new_application') return 'fa-paper-plane';
        if (type === 'chat_message') return 'fa-comment';
        if (type === 'application_status') return 'fa-check-circle';
        if (type === 'resume_view') return 'fa-eye';
        if (type === 'moderation_approved') return 'fa-check-double';
        if (type === 'moderation_rejected') return 'fa-exclamation-triangle';
        if (type === 'vacancy_deleted') return 'fa-ban';
        if (type === 'resume_deleted') return 'fa-ban';
        return 'fa-bell';
    }

    // ── Render ────────────────────────────────────────────────────────
    function renderBadge() {
        if (unreadCount > 0) {
            badge.textContent = unreadCount > 99 ? '99+' : String(unreadCount);
            badge.style.display = '';
            bellBtn.classList.add('jf-notif-has');
        } else {
            badge.style.display = 'none';
            bellBtn.classList.remove('jf-notif-has');
        }
    }

    function renderList() {
        if (!notifications.length) {
            listEl.innerHTML =
                '<div class="jf-notif-empty">' +
                    '<i class="far fa-bell-slash"></i><p>Нет уведомлений</p>' +
                '</div>';
            return;
        }
        listEl.innerHTML = notifications.map(function (n) {
            var unread = !n.is_read;
            return '<div class="jf-notif-item' + (unread ? ' unread' : '') + '" data-id="' + n.id + '" data-link="' + escapeHtml(n.link || '') + '">' +
                '<div class="jf-notif-item-icon"><i class="fas ' + notifyIcon(n.type) + '"></i></div>' +
                '<div class="jf-notif-item-body">' +
                    '<div class="jf-notif-item-title">' + escapeHtml(n.title) + '</div>' +
                    (n.body ? '<div class="jf-notif-item-text">' + escapeHtml(n.body) + '</div>' : '') +
                    '<div class="jf-notif-item-time">' + escapeHtml(timeAgo(n.created_at)) + '</div>' +
                '</div>' +
                (unread ? '<span class="jf-notif-dot"></span>' : '') +
            '</div>';
        }).join('');
    }

    // ── Data ──────────────────────────────────────────────────────────
    function loadNotifications() {
        fetch('/api/notifications/', { headers: authHeaders() })
            .then(function (res) {
                if (res.status === 401) { handleUnauthorized(); return []; }
                return res.ok ? res.json() : [];
            })
            .then(function (data) {
                notifications = data || [];
                renderList();
            })
            .catch(function () {});
    }

    function loadUnreadCount() {
        fetch('/api/notifications/unread-count', { headers: authHeaders() })
            .then(function (res) {
                if (res.status === 401) { handleUnauthorized(); return { count: 0 }; }
                return res.ok ? res.json() : { count: 0 };
            })
            .then(function (data) {
                var c = data && data.count ? data.count : 0;
                if (c !== unreadCount) {
                    unreadCount = c;
                    renderBadge();
                    if (dropdownOpen) loadNotifications();
                }
            })
            .catch(function () {});
    }

    function markRead(id, link) {
        fetch('/api/notifications/' + id + '/read', { method: 'POST', headers: authHeaders() })
            .then(function () {
                loadUnreadCount();
                if (dropdownOpen) loadNotifications();
            })
            .catch(function () {});
        if (link) {
            closeDropdown();
            window.location.href = link;
        }
    }

    function markAllRead() {
        fetch('/api/notifications/read-all', { method: 'POST', headers: authHeaders() })
            .then(function () {
                unreadCount = 0;
                renderBadge();
                loadNotifications();
            })
            .catch(function () {});
    }

    // ── Dropdown behaviour ────────────────────────────────────────────
    function openDropdown() {
        dropdownOpen = true;
        dropdown.style.display = '';
        loadNotifications();
    }

    function closeDropdown() {
        dropdownOpen = false;
        dropdown.style.display = 'none';
    }

    bellBtn.addEventListener('click', function (e) {
        e.stopPropagation();
        if (dropdownOpen) closeDropdown();
        else openDropdown();
    });

    document.addEventListener('click', function (e) {
        if (dropdownOpen && !wrapper.contains(e.target)) closeDropdown();
    });

    listEl.addEventListener('click', function (e) {
        var item = e.target.closest('.jf-notif-item');
        if (!item) return;
        var id = item.getAttribute('data-id');
        var link = item.getAttribute('data-link') || '';
        markRead(id, link);
    });

    readAllBtn.addEventListener('click', function (e) {
        e.stopPropagation();
        markAllRead();
    });

    // ── Toast for live notifications ──────────────────────────────────
    function showToast(n) {
        var toast = document.createElement('div');
        toast.className = 'jf-notif-toast';
        toast.innerHTML =
            '<div class="jf-notif-toast-icon"><i class="fas ' + notifyIcon(n.type) + '"></i></div>' +
            '<div class="jf-notif-toast-body">' +
                '<div class="jf-notif-toast-title">' + escapeHtml(n.title) + '</div>' +
                (n.body ? '<div class="jf-notif-toast-text">' + escapeHtml(n.body) + '</div>' : '') +
            '</div>';
        document.body.appendChild(toast);
        setTimeout(function () { toast.classList.add('show'); }, 10);
        setTimeout(function () {
            toast.classList.remove('show');
            setTimeout(function () { if (toast.parentNode) toast.parentNode.removeChild(toast); }, 300);
        }, 4500);
        toast.addEventListener('click', function () {
            if (n.id) markRead(n.id, n.link || '');
        });
    }

    function handleIncoming(n) {
        if (!n) return;
        notifications.unshift(n);
        if (notifications.length > 30) notifications.pop();
        if (!n.is_read) {
            unreadCount += 1;
            renderBadge();
            showToast(n);
        }
        if (dropdownOpen) renderList();
    }

    // ── WebSocket (real-time) with reconnect ──────────────────────────
    function connectWs() {
        if (loggedOut) return;
        if (ws && (ws.readyState === WebSocket.OPEN || ws.readyState === WebSocket.CONNECTING)) return;
        // Fetch a short-lived ticket so the long-lived JWT never goes in the URL.
        fetch('/api/notifications/ws-ticket', { method: 'POST', headers: authHeaders() })
            .then(function (res) {
                if (res.status === 401) { handleUnauthorized(); return null; }
                return res.ok ? res.json() : null;
            })
            .then(function (data) {
                if (!data || !data.ticket) { scheduleReconnect(); return; }
                openSocket(data.ticket);
            })
            .catch(function () { scheduleReconnect(); });
    }

    function openSocket(ticket) {
        var scheme = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        var url = scheme + '//' + window.location.host + '/ws/notifications?ticket=' + encodeURIComponent(ticket);
        try {
            ws = new WebSocket(url);
        } catch (err) {
            scheduleReconnect();
            return;
        }

        ws.onmessage = function (event) {
            try {
                var data = JSON.parse(event.data);
                if (data && (data.type === 'user_online' || data.type === 'user_offline' || data.type === 'presence_init')) {
                    if (typeof window.onPresenceWsEvent === 'function') window.onPresenceWsEvent(data);
                    return;
                }
                handleIncoming(data);
            } catch (err) { /* ignore malformed frames */ }
        };

        ws.onopen = function () {
            wsRetryDelay = WS_RETRY_INTERVAL;
            if (heartbeatTimer) clearInterval(heartbeatTimer);
            heartbeatTimer = setInterval(function () {
                if (ws && ws.readyState === WebSocket.OPEN) {
                    try { ws.send('ping'); } catch (err) {}
                }
            }, 25000);
        };

        ws.onclose = function () {
            stopHeartbeat();
            scheduleReconnect();
        };

        ws.onerror = function () {
            try { ws.close(); } catch (err) {}
        };
    }

    function scheduleReconnect() {
        if (loggedOut || wsRetry) return;
        var delay = wsRetryDelay;
        wsRetryDelay = Math.min(wsRetryDelay * 2, WS_RETRY_MAX);
        wsRetry = setTimeout(function () {
            wsRetry = null;
            connectWs();
        }, delay);
    }

    function stopHeartbeat() {
        if (heartbeatTimer) { clearInterval(heartbeatTimer); heartbeatTimer = null; }
    }

    // ── Init ──────────────────────────────────────────────────────────
    function init() {
        renderList();
        loadUnreadCount();
        loadNotifications();
        connectWs();
        // Polling fallback in case the WebSocket is unavailable.
        pollTimer = setInterval(loadUnreadCount, POLL_INTERVAL);
        document.addEventListener('visibilitychange', function () {
            if (!document.hidden) loadUnreadCount();
        });
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }

    // Public hook (optional) so other scripts can force-refresh the bell.
    window.JobFlowNotifications = {
        refresh: function () { loadUnreadCount(); loadNotifications(); }
    };
})();
