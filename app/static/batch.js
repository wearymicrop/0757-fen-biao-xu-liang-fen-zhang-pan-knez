const batch = document.querySelector('#batch');
const sourceChoice = document.querySelector('#sample');
sourceChoice.addEventListener('change', () => {
  const url = new URL(location.href);
  url.searchParams.set('sample', sourceChoice.value);
  location.assign(url);
});

const info = document.querySelector('#run-info');
const exportBill = document.querySelector('#export');
const again = document.querySelector('#again');
let identifier;
async function retain(retry) {
  const submit = batch.querySelector('button');
  submit.disabled = again.disabled = true;
  info.textContent = '正在复核功率账…';
  try {
    const response = await fetch(retry ? `/api/runs/${identifier}/rerun` : '/api/runs', {
      method: 'POST', headers: {'Content-Type': 'application/json'},
      body: retry ? undefined : JSON.stringify({sample: batch.dataset.sample}),
    });
    const run = await response.json();
    if (!response.ok) throw new Error(run.message);
    identifier = run.id;
    info.textContent = `${run.reused ? '复算一致' : '已保存'} · ${identifier.slice(0, 10)}`;
    exportBill.href = `/api/runs/${identifier}/export`;
    exportBill.hidden = again.hidden = false;
  } catch (error) {
    info.textContent = error.message || '证据保存失败。';
  } finally {
    submit.disabled = again.disabled = false;
  }
}

batch.addEventListener('submit', event => { event.preventDefault(); retain(false); });
again.addEventListener('click', () => retain(true));
