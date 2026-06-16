(function() {
    var token = localStorage.getItem('jobflow_token');
    var navRight = document.querySelector('.nav-right');
    if (!navRight || !token) return;

    var loginLink = navRight.querySelector('a[href="login.html"]');
    if (loginLink) {
        loginLink.href = 'account.html';
        loginLink.innerHTML = '<i class="fas fa-user-circle"></i> Аккаунт';
    }
})();
