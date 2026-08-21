const fileInput = document.querySelector('#project');
const analyzeButton = document.querySelector('#analyze');
const generateButton = document.querySelector('#generate');
const errorMessage = document.querySelector('#error');
let session = '';

fileInput.addEventListener('change', () => {
  analyzeButton.disabled = !fileInput.files.length;
});

analyzeButton.addEventListener('click', async () => {
  errorMessage.textContent = '';
  analyzeButton.disabled = true;
  analyzeButton.textContent = 'Analizando…';
  try {
    const includeDashboard = document.querySelector('#include-dashboard').checked;
    const response = await fetch(`/api/analyze?dashboard=${includeDashboard}`, {
      method: 'POST',
      headers: {'Content-Type': 'application/zip'},
      body: fileInput.files[0]
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || 'No se ha podido analizar el proyecto.');
    // El servidor conserva temporalmente el ZIP y devuelve una sesión de un solo uso.
    render(data);
  } catch (error) {
    errorMessage.textContent = error.message;
  } finally {
    analyzeButton.disabled = false;
    analyzeButton.textContent = 'Analizar proyecto';
  }
});

generateButton.addEventListener('click', async () => {
  errorMessage.textContent = '';
  generateButton.disabled = true;
  generateButton.textContent = 'Generando…';
  try {
    const response = await fetch(`/api/generate?session=${encodeURIComponent(session)}`, {method: 'POST'});
    if (!response.ok) {
      const data = await response.json();
      throw new Error(data.error || 'No se ha podido generar el proyecto.');
    }
    const url = URL.createObjectURL(await response.blob());
    // Se crea un enlace temporal para descargar el ZIP sin guardar datos en el navegador.
    const link = document.createElement('a');
    link.href = url;
    link.download = 'proyecto-devsecops.zip';
    link.click();
    URL.revokeObjectURL(url);
    session = '';
  } catch (error) {
    errorMessage.textContent = error.message;
  } finally {
    generateButton.disabled = false;
    generateButton.textContent = 'Descargar proyecto';
  }
});

function render(data) {
  session = data.session;
  document.querySelector('#result').hidden = false;
  document.querySelector('#profile').textContent = `${data.facts.profile_name} · ${data.facts.confidence}%`;
  document.querySelector('#evidence').textContent = `Evidencias: ${data.facts.evidence.join(', ')}`;
  document.querySelector('#facts').innerHTML = [
    ['Construcción', data.facts.build_system],
    ['Java', data.facts.java_version],
    ['Dockerfile', data.facts.dockerfile || 'No detectado']
  ].map(([label, value]) => `<div class="fact"><small>${label}</small><strong>${escapeHtml(value)}</strong></div>`).join('');

  const labels = {add: 'Se añade', modify: 'Se modifica', not_applicable: 'No aplicable'};
  document.querySelector('#changes').innerHTML = data.changes.map(change => `
    <article class="change ${change.kind}">
      <div><span class="badge">${labels[change.kind]}</span><div class="path">${escapeHtml(change.path)}${change.line ? ` · línea ${change.line}` : ''}</div></div>
      <div><strong>${escapeHtml(change.title)}</strong><p>${escapeHtml(change.reason)}</p></div>
      ${change.before || change.after ? `<div class="diff">${change.before ? `<div class="minus">− ${escapeHtml(change.before)}</div>` : ''}${change.after ? `<div class="plus">+ ${escapeHtml(change.after)}</div>` : ''}</div>` : ''}
    </article>`).join('');

  document.querySelector('#learning').innerHTML = data.learning.map(card => `
    <article class="card"><h3>${escapeHtml(card.title)}</h3><p>${escapeHtml(card.summary)}</p><ul>${card.checks.map(check => `<li>${escapeHtml(check)}</li>`).join('')}</ul></article>`).join('');
  document.querySelector('#result').scrollIntoView({behavior: 'smooth'});
}

function escapeHtml(value) {
  const element = document.createElement('div');
  element.textContent = String(value);
  return element.innerHTML;
}
