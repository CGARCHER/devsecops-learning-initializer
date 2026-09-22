const fileInput = document.querySelector('#project');
const analyzeButton = document.querySelector('#analyze');
const generateButton = document.querySelector('#generate');
const errorMessage = document.querySelector('#error');
const dashboardCheckbox = document.querySelector('#include-dashboard');
const helpTitle = document.querySelector('#help-title');
const helpTool = document.querySelector('#help-tool');
const helpText = document.querySelector('#help-text');
const helpFile = document.querySelector('#help-file');
const helpStudent = document.querySelector('#help-student');
const dashboardNextSteps = document.querySelector('#dashboard-next-steps');
const ANALYZE_LABEL = 'Analizar proyecto';
const DOWNLOAD_LABEL = 'Descargar proyecto preparado';
const MAX_ZIP_BYTES = 25 * 1024 * 1024;
const ANALYZE_TIMEOUT_MS = 120000;
let session = '';
let dashboardIncluded = false;

// Las explicaciones se mantienen junto a la interfaz para que puedan leerse
// antes de generar ningún archivo.
const helpContent = {
  workflow: {
    title: 'Integración continua',
    tool: 'Herramienta: GitHub Actions',
    text: 'El workflow se ejecuta al subir cambios, abrir una pull request o iniciarlo manualmente. Su función es coordinar los análisis sin que el alumno tenga que lanzar cada herramienta por separado.',
    file: '.github/workflows/devsecops.yml',
    student: 'Abrir la pestaña Actions, comprobar que todos los trabajos terminan y consultar el informe generado.'
  },
  sast: {
    title: 'Análisis estático del código (SAST)',
    tool: 'Herramienta: Semgrep',
    text: 'Semgrep revisa el código Java sin ejecutar la aplicación. Aplica reglas que permiten localizar patrones de programación inseguros e indica el archivo y la línea relacionados.',
    file: 'Código fuente del proyecto',
    student: 'Leer la regla detectada, revisar la línea indicada y repetir el análisis después de corregir el código.'
  },
  sca: {
    title: 'Análisis de dependencias (SCA)',
    tool: 'Herramientas: CycloneDX y Trivy',
    text: 'CycloneDX genera un inventario de las dependencias del proyecto y Trivy busca vulnerabilidades conocidas en él. El inventario se obtiene desde Maven o Gradle, según la estructura detectada.',
    file: 'pom.xml, build.gradle o build.gradle.kts',
    student: 'Comprobar qué componente es vulnerable, revisar la versión corregida y validar que la actualización no rompe la aplicación.'
  },
  container: {
    title: 'Análisis de la imagen de contenedor',
    tool: 'Herramienta: Trivy',
    text: 'Cuando el proyecto contiene un Dockerfile, el pipeline construye la imagen y revisa sus paquetes del sistema operativo y sus bibliotecas. Si no existe Dockerfile, este control se marca como no aplicable.',
    file: 'Dockerfile',
    student: 'Distinguir si la corrección corresponde a la imagen base, a un paquete del sistema o a una dependencia de la aplicación.'
  },
  policy: {
    title: 'Política de seguridad',
    tool: 'Componente: evaluación del pipeline',
    text: 'La política agrupa los hallazgos por severidad y toma una decisión común. Los hallazgos críticos, altos y de gravedad desconocida (UNKNOWN) requieren corrección o aceptación explícita del responsable antes de desplegar main. Los errores técnicos del análisis sí bloquean el proceso.',
    file: '.devsecops/engine/security/policy.json',
    student: 'Una comprobación verde indica que el análisis ha terminado sin errores técnicos. Revisa también el estado de seguridad para saber si hay que aceptar los hallazgos antes de desplegar main.'
  },
  rulesets: {
    title: 'Protección de ramas en GitHub',
    tool: 'Herramienta: GitHub Rulesets',
    text: 'El inicializador prepara dos rulesets para develop y main. Exigen una pull request y que el análisis termine sin errores técnicos, pero no se activan automáticamente: deben importarse y revisarse desde la configuración del repositorio.',
    file: '.github/rulesets/*.json y SECURITY_SETUP.md',
    student: 'Importar cada ruleset manualmente y comprobar mediante una pull request que la protección funciona.'
  },
  dashboard: {
    title: 'Panel local de seguridad',
    tool: 'Componente: panel local',
    text: 'El panel descarga el último artefacto del workflow y presenta el estado, las severidades y el detalle de los hallazgos. Está pensado para ejecutarse en local, no como servicio público.',
    file: '.devsecops/dashboard/ y compose.security.yml',
    student: 'Configurar el repositorio y un token personal de GitHub con permisos de lectura antes de arrancar el panel.'
  },
  ai: {
    title: 'Remediación asistida por IA',
    tool: 'Componente: API de remediación desplegada',
    text: 'La API ya está desplegada y no requiere instalar ni configurar modelos. Al pulsar «Cómo corregirlo», el panel envía a la API el hallazgo seleccionado y el contexto disponible. La IA lo explica y propone un cambio de código cuando dispone de información suficiente. No deben incluirse credenciales ni información sensible.',
    file: '.devsecops/dashboard.env',
    student: 'Entender la propuesta, comprobar que corresponde al archivo real, aplicarla manualmente y volver a ejecutar los análisis.'
  },
  compose: {
    title: 'Docker Compose',
    tool: 'Herramienta: Docker Compose',
    text: 'Define cómo construir y ejecutar el panel, cómo montar los informes y cómo leer la configuración local sin incluir los tokens en la imagen. No sustituye al Compose propio de la aplicación del alumno.',
    file: 'compose.security.yml',
    student: 'Crear los archivos de configuración local y arrancar el panel con el comando explicado en la guía generada.'
  },

};

function showHelp(concept) {
  const help = helpContent[concept];
  if (!help) return;
  helpTitle.textContent = help.title;
  helpTool.textContent = help.tool;
  helpText.textContent = help.text;
  helpFile.textContent = help.file;
  helpStudent.textContent = help.student;
}

document.querySelectorAll('.help-link').forEach(button => {
  button.addEventListener('click', () => showHelp(button.dataset.help));
});

dashboardCheckbox.addEventListener('change', () => {
  resetPlan();
  document.querySelector('.optional-selection').classList.toggle('selected', dashboardCheckbox.checked);
  const concept = dashboardCheckbox.checked ? 'dashboard' : 'workflow';
  showHelp(concept);
});

// Marcar la opción no debe cerrar accidentalmente su apartado desplegable.
dashboardCheckbox.addEventListener('click', event => event.stopPropagation());

showHelp('workflow');

fileInput.addEventListener('change', resetPlan);
analyzeButton.addEventListener('click', analyzeProject);
generateButton.addEventListener('click', downloadProject);

function resetPlan() {
  // El resultado solo sirve para el ZIP y las opciones que se analizaron.
  session = '';
  document.querySelector('#result').hidden = true;
  dashboardNextSteps.hidden = true;
  errorMessage.textContent = uploadError();
  setButtonState(generateButton, true, DOWNLOAD_LABEL);
  analyzeButton.disabled = fileInput.files.length === 0 || Boolean(errorMessage.textContent);
}

function uploadError() {
  // Rechaza el archivo antes de enviarlo; el servidor mantiene su propio límite.
  const file = fileInput.files[0];
  if (!file) return '';
  if (!/\.zip$/i.test(file.name)) return 'Selecciona un archivo ZIP.';
  if (file.size > MAX_ZIP_BYTES) {
    return 'El ZIP supera el límite de 25 MB. Crea una copia sin .git, target, build ni informes generados.';
  }
  return '';
}

function setBusy(busy) {
  // Impide cambiar de proyecto mientras se analiza o se prepara la descarga.
  fileInput.disabled = busy;
  dashboardCheckbox.disabled = busy;
  analyzeButton.disabled = busy || fileInput.files.length === 0 || Boolean(uploadError());
}

async function analyzeProject() {
  resetPlan();
  if (analyzeButton.disabled) return;
  setBusy(true);
  setButtonState(analyzeButton, true, 'Analizando…');
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), ANALYZE_TIMEOUT_MS);

  try {
    const requestedDashboard = dashboardCheckbox.checked;
    const response = await fetch(`/api/analyze?dashboard=${requestedDashboard}`, {
      method: 'POST',
      headers: {'Content-Type': 'application/zip'},
      body: fileInput.files[0],
      signal: controller.signal
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || 'No se ha podido analizar el proyecto.');

    // El servidor conserva temporalmente el ZIP y devuelve una sesión de un solo uso.
    dashboardIncluded = data.changes.some(change => change.path === '.devsecops/dashboard');
    renderPlan(data);
  } catch (error) {
    showError(controller.signal.aborted
      ? new Error('El análisis ha superado los dos minutos de espera. Comprueba la conexión y vuelve a intentarlo.')
      : error);
  } finally {
    clearTimeout(timeout);
    analyzeButton.textContent = ANALYZE_LABEL;
    setBusy(false);
  }
}

async function downloadProject() {
  if (!session) return;
  errorMessage.textContent = '';
  setBusy(true);
  setButtonState(generateButton, true, 'Generando…');

  try {
    const response = await fetch(`/api/generate?session=${encodeURIComponent(session)}`, {method: 'POST'});
    if (!response.ok) {
      const data = await response.json();
      throw new Error(data.error || 'No se ha podido generar el proyecto.');
    }

    downloadBlob(await response.blob(), preparedFilename());
    dashboardNextSteps.hidden = !dashboardIncluded;
  } catch (error) {
    showError(error);
  } finally {
    // La sesión es de un solo uso; incluso tras un error hay que analizar de nuevo.
    session = '';
    setButtonState(generateButton, true, 'Analiza de nuevo para descargar otra copia');
    setBusy(false);
  }
}

function setButtonState(button, disabled, text) {
  button.disabled = disabled;
  button.textContent = text;
}

function showError(error) {
  errorMessage.textContent = error instanceof Error ? error.message : 'Se ha producido un error inesperado.';
}

function preparedFilename() {
  const originalName = fileInput.files[0]?.name || 'proyecto.zip';
  return `${originalName.replace(/\.zip$/i, '')}-devsecops.zip`;
}

function downloadBlob(blob, filename) {
  // El enlace temporal permite descargar el ZIP sin conservarlo en el navegador.
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = filename;
  link.click();
  URL.revokeObjectURL(url);
}

function renderPlan(data) {
  session = data.session;
  setButtonState(generateButton, false, DOWNLOAD_LABEL);
  document.querySelector('#result').hidden = false;
  document.querySelector('#profile').textContent = data.facts.profile_name;
  document.querySelector('#evidence').textContent = `Evidencias: ${data.facts.evidence.join(', ')}`;

  renderVersion(data.version);
  renderFacts(data.facts);
  renderChanges(data.changes);
  renderLearning(data.learning);
  document.querySelector('#result').scrollIntoView({behavior: 'smooth'});
}

function renderVersion(version) {
  const element = document.querySelector('#version-status');
  const messages = {
    not_installed: `Se incorporará el paquete DevSecOps ${version.current}.`,
    current: `El proyecto ya utiliza DevSecOps ${version.current}.`,
    update_available: `Actualización disponible: ${version.installed} → ${version.current}. La copia incluirá la versión nueva.`,
    newer: `El proyecto utiliza DevSecOps ${version.installed}, una versión más reciente que este inicializador.`
  };
  element.textContent = messages[version.status] || `Versión DevSecOps: ${version.current}.`;
  element.className = `version-status ${version.status}`;
}

function renderFacts(facts) {
  document.querySelector('#facts').innerHTML = [
    ['Construcción', facts.build_system],
    ['Java', facts.java_version],
    ['Dockerfile', facts.dockerfile || 'No detectado']
  ].map(([label, value]) => `<div class="fact"><small>${label}</small><strong>${escapeHtml(value)}</strong></div>`).join('');
}

function renderChanges(changes) {
  const labels = {add: 'Se añadirá', modify: 'Se sustituirá', delete: 'Se eliminará', not_applicable: 'Control no aplicable'};
  document.querySelector('#changes').innerHTML = changes.map(change => `
    <article class="change ${change.kind}">
      <div><span class="badge">${labels[change.kind]}</span><div class="path">${escapeHtml(change.path)}${change.line ? ` · línea ${change.line}` : ''}</div></div>
      <div><strong>${escapeHtml(change.title)}</strong><p>${escapeHtml(change.reason)}</p></div>
      ${change.before || change.after ? `<div class="diff">${change.before ? `<div class="minus">− ${escapeHtml(change.before)}</div>` : ''}${change.after ? `<div class="plus">+ ${escapeHtml(change.after)}</div>` : ''}</div>` : ''}
    </article>`).join('');
}

function renderLearning(cards) {
  document.querySelector('#learning').innerHTML = cards.map(card => `
    <article class="card"><h3>${escapeHtml(card.title)}</h3><p>${escapeHtml(card.summary)}</p><ul>${card.checks.map(check => `<li>${escapeHtml(check)}</li>`).join('')}</ul></article>`).join('');
}

function escapeHtml(value) {
  const element = document.createElement('div');
  element.textContent = String(value);
  return element.innerHTML;
}
