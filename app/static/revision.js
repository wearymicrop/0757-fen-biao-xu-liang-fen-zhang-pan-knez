const form = document.querySelector('#revision-publish');
const info = document.querySelector('#publish-info');

form.addEventListener('submit', async event => {
  event.preventDefault();
  const button = form.querySelector('button');
  const revisionId = form.dataset.revision;
  button.disabled = true;
  info.textContent = '正在复核对平与旧归档…';
  try {
    const response = await fetch(`/api/revisions/${revisionId}/publish`, {method: 'POST'});
    const body = await response.json();
    if (!response.ok) throw new Error(body.message);
    info.textContent = `已发布 · ${body.id.slice(0, 10)}，旧版仍可追回`;
    form.querySelector('.state-badge').textContent = '已发布';
    button.textContent = '已成为唯一发布版';
  } catch (error) {
    info.textContent = error.message || '发布被拦截。';
    button.disabled = false;
  }
});
