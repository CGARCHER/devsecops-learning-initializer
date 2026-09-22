// Fija el commit antes de desplegar y espera al resultado de esa solicitud.
module.exports = async ({github, context, core}) => {
  if (process.env.DOKPLOY_DEPLOY_ENABLED !== 'true') {
    core.info('Despliegue Dokploy desactivado. Sigue SECURITY_SETUP.md para activarlo.');
    return;
  }
  if (context.ref !== 'refs/heads/main' || !/^[0-9a-f]{40}$/.test(context.sha)) {
    throw new Error('Solo se permite desplegar un commit autorizado de main.');
  }
  const {DOKPLOY_URL, DOKPLOY_API_KEY, DOKPLOY_COMPOSE_ID} = process.env;
  if (!DOKPLOY_URL || !DOKPLOY_API_KEY || !DOKPLOY_COMPOSE_ID) {
    throw new Error('Configura DOKPLOY_URL, DOKPLOY_API_KEY y DOKPLOY_COMPOSE_ID.');
  }
  const path = require('node:path');
  const fs = require('node:fs');
  const composePath = process.env.DOKPLOY_COMPOSE_PATH || './compose.yml';
  const root = fs.realpathSync(process.cwd());
  if (path.isAbsolute(composePath) || composePath.includes('\\') ||
      composePath.split('/').includes('..') || !/\.ya?ml$/.test(composePath) ||
      path.basename(composePath) === 'compose.security.yml') {
    throw new Error('DOKPLOY_COMPOSE_PATH debe apuntar al Compose de la aplicación dentro del repositorio.');
  }
  const resolved = path.resolve(root, composePath);
  if (!fs.existsSync(resolved) || !fs.statSync(resolved).isFile() ||
      !fs.realpathSync(resolved).startsWith(root + path.sep)) {
    throw new Error('No existe un Compose válido en DOKPLOY_COMPOSE_PATH. Revisa SECURITY_SETUP.md.');
  }
  const base = new URL(DOKPLOY_URL);
  if (base.protocol !== 'https:' || base.username || base.password) {
    throw new Error('DOKPLOY_URL debe ser una dirección HTTPS sin credenciales.');
  }
  const composeId = DOKPLOY_COMPOSE_ID;
  const query = new URLSearchParams({composeId});
  const tag = `deploy-${context.sha}`;
  const title = `GitHub ${context.runId}-${process.env.GITHUB_RUN_ATTEMPT}`;

  const description = `Commit: ${context.sha}`;

  async function api(route, body) {
    const response = await fetch(new URL(`/api/${route}`, base), {
      method: body ? 'POST' : 'GET',
      headers: {'x-api-key': DOKPLOY_API_KEY, 'Content-Type': 'application/json'},
      body: body ? JSON.stringify(body) : undefined,
      signal: AbortSignal.timeout(30000),
      redirect: 'error',
    });
    // No se vuelca la respuesta: puede contener configuración privada.
    if (!response.ok) throw new Error(`Dokploy respondió HTTP ${response.status}.`);
    return response.json();
  }

  // Comprueba el destino antes de cambiar su configuración.
  const config = await api(`compose.one?${query}`);
  if (config.sourceType !== 'github' || config.owner !== context.repo.owner ||
      config.repository !== context.repo.repo || config.autoDeploy || config.command) {
    throw new Error('Revisa el repositorio de Dokploy, desactiva Autodeploy y usa el comando predeterminado.');
  }
  const previous = await api(`deployment.allByCompose?${query}`);
  if (!Array.isArray(previous) || previous.some(item => item.status === 'running')) {
    throw new Error('No se puede iniciar mientras haya otro despliegue en curso.');
  }

  // La etiqueta identifica este commit. Nunca se mueve una etiqueta existente.
  try {
    await github.rest.git.createRef({...context.repo, ref: `refs/tags/${tag}`, sha: context.sha});
  } catch (error) {
    if (error.status !== 422) throw error;
    const {data} = await github.rest.git.getRef({...context.repo, ref: `tags/${tag}`});
    if (data.object.type !== 'commit' || data.object.sha !== context.sha) {
      throw new Error('La etiqueta de despliegue no coincide con el commit aprobado.');
    }
  }
  // Dokploy construirá esta etiqueta aunque main reciba nuevos commits.
  await api('compose.update', {composeId, branch: tag, composePath});
  await api('compose.deploy', {composeId, title, description});
  core.info(`Solicitado el despliegue de ${context.sha}.`);

  // Un registro antiguo con estado Done no sirve como confirmación.
  const previousIds = new Set(previous.map(item => item.deploymentId));
  let deploymentId;
  for (let attempt = 0; attempt < 120; attempt++) {
    const deployments = await api(`deployment.allByCompose?${query}`);
    if (!Array.isArray(deployments)) throw new Error('Respuesta de despliegues inválida.');
    // Dokploy sustituye título y descripción. Conserva "Commit: <sha>".
    // Solo seguimos un registro nuevo del commit solicitado, siempre por su ID.
    const matches = deployments.filter(item => item.description === description && !previousIds.has(item.deploymentId));
    if (matches.length > 1) throw new Error('Hay varios despliegues nuevos del mismo commit. Revisa Dokploy.');
    deploymentId ??= matches[0]?.deploymentId;
    const deployment = matches.find(item => item.deploymentId === deploymentId);
    if (deployment?.status === 'error') throw new Error('El despliegue ha fallado en Dokploy. Revisa su registro.');
    if (deployment?.status === 'done') {
      core.info(`Dokploy ha terminado el despliegue ${deployment.deploymentId}.`);
      return;
    }
    await new Promise(resolve => setTimeout(resolve, 5000));
  }
  throw new Error('Dokploy no ha confirmado el despliegue en diez minutos. Revisa su estado antes de repetirlo.');
};
