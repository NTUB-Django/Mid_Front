(() => {
  const notices = [...document.querySelectorAll('[data-operation-success]')];
  const dialog = document.getElementById('operation-dialog');
  if (!notices.length || !dialog || typeof dialog.showModal !== 'function') return;
  document.getElementById('operation-dialog-message').textContent = notices.map((item) => item.textContent.trim()).join('\n');
  document.getElementById('operation-dialog-close').addEventListener('click', () => dialog.close());
  dialog.showModal();
})();
