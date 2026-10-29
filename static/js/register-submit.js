(() => {
  const form = document.getElementById('register-form');
  if (!form) return;
  const button = form.querySelector('button[type="submit"]');
  const dialog = document.getElementById('register-status-dialog');
  const title = document.getElementById('register-status-title');
  const message = document.getElementById('register-status-message');
  const close = document.getElementById('register-status-close');
  close?.addEventListener('click', () => dialog.close());
  form.addEventListener('submit', (event) => {
    if (form.dataset.submitting === 'yes') {
      event.preventDefault();
      if (dialog && typeof dialog.showModal === 'function' && !dialog.open) dialog.showModal();
      return;
    }
    form.dataset.submitting = 'yes';
    button.disabled = true;
    button.textContent = '建立中…';
    title.textContent = '帳號建立中';
    message.textContent = '正在建立帳號並登入，請勿重複送出。';
    close.hidden = true;
    if (dialog && typeof dialog.showModal === 'function') dialog.showModal();
  });
  window.addEventListener('pageshow', () => {
    form.dataset.submitting = 'no';
    button.disabled = false;
    button.textContent = '建立帳號並登入';
    if (dialog?.open) dialog.close();
    const error = document.querySelector('[data-register-error]');
    if (error && dialog && typeof dialog.showModal === 'function') {
      title.textContent = '請重新確認註冊資料';
      message.textContent = error.textContent.trim();
      close.hidden = false;
      dialog.showModal();
    }
  });
})();
