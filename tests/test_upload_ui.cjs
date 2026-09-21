const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const test = require('node:test');
const vm = require('node:vm');

// Ejecuta la interfaz con una selección de archivo y una red simuladas.
// No crea ni envía un ZIP de 170 MB para comprobar que se rechaza.
function screen(fetchResponse) {
  const elements = new Map();
  const element = (selector) => {
    if (!elements.has(selector)) elements.set(selector, {
      files: [], disabled: false, hidden: false, textContent: '', checked: false,
      classList: { toggle() {} },
      addEventListener() {},
    });
    return elements.get(selector);
  };
  let timer;
  let requests = 0;
  const context = vm.createContext({
    document: {querySelector: element, querySelectorAll: () => []},
    AbortController,
    setTimeout(callback) { timer = callback; return 1; },
    clearTimeout() { timer = undefined; },
    fetch(...args) { requests++; return fetchResponse(...args); },
  });
  const source = fs.readFileSync(path.join(__dirname,
    '../src/devsecops_initializer/static/app.js'), 'utf8');
  vm.runInContext(source, context);
  return {
    element,
    select(name, size) {
      element('#project').files = name ? [{name, size}] : [];
      context.resetPlan();
    },
    analyze: () => context.analyzeProject(),
    expire: () => timer(),
    requests: () => requests,
    hasTimer: () => Boolean(timer),
  };
}

test('rechaza 170 MB antes de enviar el archivo y permite elegir otro', async () => {
  const ui = screen(() => assert.fail('No debe enviar el ZIP grande'));
  ui.select('proyecto.zip', 170 * 1024 * 1024);
  assert.equal(ui.element('#analyze').disabled, true);
  assert.match(ui.element('#error').textContent, /25 MB/);
  await ui.analyze();
  assert.equal(ui.requests(), 0);
  assert.equal(ui.element('#project').disabled, false);
  assert.equal(ui.element('#generate').disabled, true);
  assert.equal(ui.element('#result').hidden, true);
  ui.select('proyecto.ZIP', 1024);
  assert.equal(ui.element('#analyze').disabled, false);
  assert.equal(ui.element('#error').textContent, '');
});

test('acepta el tamaño límite y recupera los controles si el servidor rechaza el ZIP', async () => {
  const ui = screen(async () => ({
    ok: false, json: async () => ({error: 'El archivo no es un ZIP válido.'}),
  }));
  ui.select('proyecto.zip', 25 * 1024 * 1024);
  await ui.analyze();
  assert.equal(ui.requests(), 1);
  assert.match(ui.element('#error').textContent, /ZIP válido/);
  assert.equal(ui.element('#analyze').textContent, 'Analizar proyecto');
  assert.equal(ui.element('#analyze').disabled, false);
  assert.equal(ui.hasTimer(), false);
});

test('rechaza otro formato y mantiene desactivado analizar sin archivo', async () => {
  const ui = screen(() => assert.fail('No debe enviar un formato no admitido'));
  ui.select('proyecto.rar', 1024);
  assert.match(ui.element('#error').textContent, /archivo ZIP/);
  await ui.analyze();
  ui.select(null);
  assert.equal(ui.element('#analyze').disabled, true);
  assert.equal(ui.element('#error').textContent, '');
  assert.equal(ui.requests(), 0);
});

test('cancela una petición que no responde y permite reintentar', async () => {
  const ui = screen((url, {signal}) => new Promise((resolve, reject) => {
    signal.addEventListener('abort', () => reject(new Error('Abortado')));
  }));
  ui.select('proyecto.zip', 1024);
  const pending = ui.analyze();
  assert.equal(ui.element('#project').disabled, true);
  ui.expire();
  await pending;
  assert.match(ui.element('#error').textContent, /dos minutos/);
  assert.equal(ui.element('#project').disabled, false);
  assert.equal(ui.element('#include-dashboard').disabled, false);
  assert.equal(ui.element('#analyze').disabled, false);
  assert.equal(ui.element('#analyze').textContent, 'Analizar proyecto');
  assert.equal(ui.hasTimer(), false);
});
