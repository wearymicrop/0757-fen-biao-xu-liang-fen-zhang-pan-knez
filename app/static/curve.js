const curve = document.querySelector('#demand-curve');
if (curve) {
  const choices = Array.from(document.querySelectorAll('[data-window-button]'));
  const cards = Array.from(document.querySelectorAll('[data-window]'));
  const context = curve.getContext('2d');
  const values = choices.map(button => button.dataset.kw ? Number(button.dataset.kw) : null);
  const high = Math.max(20, Math.ceil(Math.max(...values) / 20) * 20);

  function plot() {
    const {width, height} = curve.getBoundingClientRect();
    const density = window.devicePixelRatio || 1;
    curve.width = Math.round(width * density);
    curve.height = Math.round(height * density);
    context.scale(density, density);
    const left = 38, right = width - 12, bottom = height - 19, top = 16;
    const pointX = index => choices.length === 1 ? (right + left) / 2 : left + index * (right - left) / (choices.length - 1);
    const pointY = value => bottom - value * (bottom - top) / high;
    context.font = '12px monospace';
    for (let step = 0; step <= 4; step += 1) {
      const value = high * step / 4;
      const y = pointY(value);
      context.strokeStyle = '#d1e0e5';
      context.beginPath();
      context.moveTo(left, y);
      context.lineTo(right, y);
      context.stroke();
      context.fillStyle = '#4d6770';
      context.fillText(value.toString(), 3, y + 4);
    }
    values.forEach((value, index) => {
      const x = pointX(index);
      const button = choices[index];
      const valid = button.dataset.gap === 'false';
      const y = value === null ? bottom - 4 : pointY(value);
      if (valid && index > 0 && choices[index - 1].dataset.gap === 'false') {
        const dx = pointX(index - 1), dy = pointY(values[index - 1]);
        context.beginPath();
        context.moveTo(dx, bottom);
        context.lineTo(dx, dy);
        context.lineTo(x, y);
        context.lineTo(x, bottom);
        context.closePath();
        context.fillStyle = '#e2f4f7';
        context.fill();
        context.beginPath();
        context.moveTo(dx, dy);
        context.lineTo(x, y);
        context.strokeStyle = '#147d9b';
        context.lineWidth = 2;
        context.stroke();
        context.lineWidth = 1;
      }
      context.fillStyle = button.dataset.official === 'true' ? '#19684e' : '#147d9b';
      if (valid) {
        context.beginPath();
        context.arc(x, y, button.getAttribute('aria-pressed') === 'true' ? 6 : 3, 0, 2 * Math.PI);
        context.fill();
      } else {
        context.fillStyle = '#ac3c46';
        context.fillText('×', x - 4, y + 4);
      }
    });
  }

  choices.forEach((button, index) => {
    button.addEventListener('click', () => {
      choices.forEach((choice, active) => choice.setAttribute('aria-pressed', String(active === index)));
      cards.forEach((card, active) => { card.hidden = active !== index; });
      plot();
    });
  });
  new ResizeObserver(plot).observe(curve);
}
