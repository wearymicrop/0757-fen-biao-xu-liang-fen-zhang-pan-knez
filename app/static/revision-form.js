const revisionForm = document.querySelector('#revision-form');

if (revisionForm) {
  const status = revisionForm.querySelector('#revision-status');
  revisionForm.addEventListener('submit', async event => {
    event.preventDefault();
    const data = new FormData(revisionForm);
    let lateReadings;
    let mappingReplacements;
    try {
      lateReadings = JSON.parse(data.get('late_readings') || '[]');
      mappingReplacements = JSON.parse(data.get('mapping_replacements') || '[]');
    } catch (error) {
      status.textContent = 'JSON 格式有误，请检查补录内容。';
      return;
    }
    const payload = {
      base_run_id: data.get('base_run_id').trim(),
      late_readings: lateReadings,
      mapping_replacements: mappingReplacements,
      note: data.get('note').trim() || null,
    };
    status.textContent = '正在合并补录并复算…';
    try {
      const response = await fetch('/api/revisions', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify(payload),
      });
      const body = await response.json();
      if (!response.ok) throw new Error(body.message);
      location.assign(`/revisions/${body.id}`);
    } catch (error) {
      status.textContent = error.message || '修订生成失败。';
    }
  });
}
