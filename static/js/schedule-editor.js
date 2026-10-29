(() => {
  const panel = document.getElementById('add-custom');
  const form = document.getElementById('schedule-editor-form');
  if (!panel || !form || !window.HTMLDialogElement) return;
  const dialog = document.createElement('dialog');
  dialog.className = 'schedule-editor-dialog';
  dialog.setAttribute('aria-labelledby', 'schedule-editor-title');
  document.body.append(dialog);
  dialog.append(panel);
  const records = JSON.parse(document.getElementById('schedule-editor-data').textContent);
  const palette = JSON.parse(document.getElementById('event-color-palette').textContent);
  const inputs = Object.fromEntries(['title', 'weekday', 'start', 'end', 'location', 'color', 'period', 'note', 'visibility'].map(name => [name, form.elements.namedItem(name)]));
  const groupInputs = [...form.querySelectorAll('input[name="shared_groups"]')];
  function updateAppearance() {
    const selected = palette[inputs.color.value] || palette.blue;
    const preview = document.getElementById('editor-color-preview');
    preview.style.backgroundColor = selected.hex;
    preview.setAttribute('aria-label', `${selected.label}預覽 ${selected.hex}`);
    document.getElementById('editor-group-permissions').hidden = inputs.visibility.value !== 'groups';
  }
  inputs.color.addEventListener('change', updateAppearance);
  inputs.visibility.addEventListener('change', updateAppearance);
  const heading = document.getElementById('schedule-editor-title');
  const deleteButton = document.getElementById('editor-delete');
  const deleteForm = document.getElementById('editor-delete-form');
  const summary = document.getElementById('editor-time-summary');
  let returnFocus;
  const minutes = value => value ? Number(value.slice(0, 2)) * 60 + Number(value.slice(3, 5)) : NaN;
  const format = value => `${String(Math.floor(value / 60)).padStart(2, '0')}:${String(value % 60).padStart(2, '0')}`;
  function updateSummary() {
    const duration = minutes(inputs.end.value) - minutes(inputs.start.value);
    const valid = duration > 0;
    inputs.end.setCustomValidity(valid ? '' : '結束時間必須晚於開始時間');
    summary.textContent = `${inputs.weekday.selectedOptions[0]?.textContent || ''} · ${inputs.start.value || '--:--'}–${inputs.end.value || '--:--'}${valid ? ` · ${duration} 分鐘` : ' · 請調整結束時間'}`;
  }
  function showEditor(values = {}, record = null) {
    returnFocus = document.activeElement;
    form.reset();
    panel.querySelectorAll('.errorlist, .alert-error').forEach(node => node.remove());
    Object.entries({...Object.fromEntries(Object.keys(inputs).map(key => [key, ''])), weekday: new Date().getDay() || 7, start: '09:00', end: '10:00', color: 'blue', visibility: 'inherit', ...values}).forEach(([key, value]) => {
      if (inputs[key]) inputs[key].value = value;
    });
    groupInputs.forEach(input => { input.checked = (values.sharedGroups || []).map(String).includes(input.value); });
    updateAppearance();
    heading.textContent = record ? '編輯行程' : '新增行程';
    form.action = record ? record.updateUrl : panel.dataset.createUrl;
    deleteButton.hidden = !record;
    deleteForm.action = record ? record.deleteUrl : '';
    document.getElementById('editor-details').open = Boolean(values.note || values.period);
    updateSummary();
    if (!dialog.open) dialog.showModal();
    document.body.classList.add('schedule-editor-open');
    inputs.title.focus();
  }
  function edit(id) {
    const record = records.find(item => item.id === Number(id));
    if (record) showEditor(record, record);
  }
  panel.querySelectorAll('[data-close-editor]').forEach(button => {
    button.hidden = false;
    button.addEventListener('click', () => dialog.close());
  });
  dialog.addEventListener('close', () => {
    document.body.classList.remove('schedule-editor-open');
    returnFocus?.focus();
  });
  dialog.addEventListener('click', event => { if (event.target === dialog) dialog.close(); });
  document.addEventListener('click', event => {
    const add = event.target.closest('a[href="#add-custom"], [data-open-schedule]');
    const existing = event.target.closest('[data-edit-schedule]');
    if (existing) { event.preventDefault(); edit(existing.dataset.editSchedule); }
    else if (add) { event.preventDefault(); showEditor({weekday: add.dataset.weekday || new Date().getDay() || 7}); }
  });
  document.addEventListener('schedule:create', event => showEditor(event.detail || {}));
  document.addEventListener('schedule:edit', event => edit(event.detail.id));
  Object.values(inputs).forEach(input => input.addEventListener('input', updateSummary));
  panel.querySelectorAll('[data-duration]').forEach(button => button.addEventListener('click', () => {
    const start = minutes(inputs.start.value);
    if (!Number.isFinite(start)) { inputs.start.focus(); return; }
    inputs.end.value = format(Math.min(start + Number(button.dataset.duration), 1439));
    updateSummary();
  }));
  deleteButton.addEventListener('click', () => {
    if (window.confirm(`確定刪除「${inputs.title.value}」？`)) deleteForm.requestSubmit();
  });
  let drag = null;
  let dragged = false;
  function clearSelection() { document.querySelectorAll('.tt-cell.is-selecting').forEach(cell => cell.classList.remove('is-selecting')); }
  document.addEventListener('pointerdown', event => {
    const button = event.target.closest('.tt-create-event');
    if (!button || event.button !== 0 || event.pointerType === 'touch') return;
    const cell = button.closest('.tt-cell');
    drag = {weekday: cell.dataset.weekday, start: cell.dataset.start, end: cell.dataset.end, cell};
    dragged = false;
  });
  document.addEventListener('pointerover', event => {
    const cell = event.target.closest('.tt-cell[data-weekday]');
    if (!drag || !cell || cell.dataset.weekday !== drag.weekday) return;
    dragged = cell !== drag.cell || dragged;
    drag.last = cell;
    clearSelection();
    const start = Math.min(minutes(drag.start), minutes(cell.dataset.start));
    const end = Math.max(minutes(drag.end), minutes(cell.dataset.end));
    document.querySelectorAll(`.tt-cell[data-weekday="${drag.weekday}"]`).forEach(item => {
      if (minutes(item.dataset.start) >= start && minutes(item.dataset.end) <= end) item.classList.add('is-selecting');
    });
  });
  document.addEventListener('pointerup', () => {
    if (!drag) return;
    const last = drag.last || drag.cell;
    const values = {weekday: drag.weekday, start: format(Math.min(minutes(drag.start), minutes(last.dataset.start))), end: format(Math.max(minutes(drag.end), minutes(last.dataset.end)))};
    const wasDragged = dragged;
    drag = null;
    clearSelection();
    if (wasDragged) { showEditor(values); setTimeout(() => { dragged = false; }, 0); }
  });
  document.addEventListener('pointercancel', () => { drag = null; clearSelection(); });
  document.querySelectorAll('.tt-create-event').forEach(button => button.addEventListener('click', () => {
    if (dragged) return;
    showEditor({...button.closest('.tt-cell').dataset});
  }));
  updateAppearance();
  if (panel.dataset.open === 'true') {
    returnFocus = document.querySelector('a[href="#add-custom"]');
    deleteButton.hidden = !form.action.includes('/update/');
    const record = records.find(item => item.updateUrl === new URL(form.action).pathname);
    if (record) deleteForm.action = record.deleteUrl;
    updateSummary();
    dialog.showModal();
    document.body.classList.add('schedule-editor-open');
    (panel.querySelector('.errorlist')?.closest('.form-group')?.querySelector('input,select,textarea') || inputs.title).focus();
  }
})();
