(() => {
  const notices = [...document.querySelectorAll('[data-schedule-conflict]')];
  const dialog = document.getElementById('schedule-conflict-dialog');
  if (!notices.length || !dialog || typeof dialog.showModal !== 'function') return;
  const blocked = notices.some(item => item.dataset.conflictKind === 'blocked');
  const saved = notices.some(item => item.dataset.conflictKind === 'saved');
  document.getElementById('conflict-dialog-title').textContent = blocked ? '無法加入：課程衝堂' : saved ? '行程時間重疊' : '部分課程因衝堂未匯入';
  document.getElementById('conflict-dialog-intro').textContent = blocked ? '這門課尚未加入，請先調整目前課表。' : saved ? '個人行程已儲存。請確認以下重疊時段，並視需要編輯行程。' : '其他可加入的課程已處理，以下衝堂課程維持未加入。';
  const list = document.getElementById('conflict-dialog-list');
  notices.forEach(notice => {
    const item = document.createElement('li');
    item.textContent = notice.textContent.trim();
    list.append(item);
  });
  dialog.addEventListener('click', event => { if (event.target === dialog) dialog.close(); });
  dialog.showModal();
})();
