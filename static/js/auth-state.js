(() => {
  const scope = location.pathname.startsWith('/school/') ? 'school' : location.pathname.startsWith('/admin/') ? 'admin' : 'student';
  const loginUrl = scope === 'school' ? '/school/login/' : scope === 'admin' ? '/admin/login/' : '/accounts/login/';
  window.addEventListener('pageshow', (event) => {
    if (event.persisted) location.reload();
  });
  window.addEventListener('storage', (event) => {
    if (event.key === `mid-logout-${scope}` && location.pathname !== loginUrl) location.assign(loginUrl);
  });
  document.querySelectorAll('form[action$="/logout/"]').forEach((form) => {
    form.addEventListener('submit', () => {
      try {
        localStorage.setItem(`mid-logout-${scope}`, String(Date.now()));
      } catch (_) {
        return;
      }
    });
  });
  const error = document.querySelector('[data-auth-error]');
  const success = document.querySelector('[data-auth-success]');
  const dialog = document.getElementById('signin-error-dialog');
  if ((error || success) && dialog && typeof dialog.showModal === 'function') {
    document.getElementById('signin-error-title').textContent = error ? '登入未完成' : '操作完成';
    document.getElementById('signin-error-message').textContent = (error || success).textContent.trim();
    document.getElementById('signin-error-close').textContent = error ? '重新輸入' : '知道了';
    dialog.showModal();
    document.getElementById('signin-error-close').addEventListener('click', () => {
      dialog.close();
      document.getElementById('id_username')?.focus();
    });
  }
})();
