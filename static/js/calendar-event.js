(() => {
  const colors = {red: '#dc2626', orange: '#ea580c', yellow: '#eab308', green: '#16a34a', blue: '#2563eb', indigo: '#4338ca', purple: '#9333ea'};
  const field = document.getElementById('id_color');
  const preview = document.getElementById('calendar-color-preview');
  if (!field || !preview) return;
  const update = () => {
    const option = field.options[field.selectedIndex];
    preview.style.setProperty('--event-color', colors[field.value] || colors.blue);
    preview.textContent = `${option.textContent}預覽`;
  };
  field.addEventListener('change', update);
  update();
  const params = new URLSearchParams(location.search);
  const date = params.get('date');
  if (date && !document.querySelector('input[name="starts_at_0"]').value) {
    document.querySelector('input[name="starts_at_0"]').value = date;
    document.querySelector('input[name="ends_at_0"]').value = date;
  }
})();
