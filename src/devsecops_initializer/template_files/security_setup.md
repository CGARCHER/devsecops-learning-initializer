# Configuración de seguridad en GitHub y despliegue en Dokploy

El proyecto incluye reglas para proteger `develop` y `main`. La importación es manual y no requiere entregar un token administrativo al inicializador.

## Por dónde empezar

Sigue los apartados 1 a 4 para dejar preparado el repositorio. Solo se hacen una vez. Después, el trabajo habitual es subir cambios, revisar los análisis y abrir una PR.

- **Análisis en GitHub:** no necesitan tokens personales ni un servidor.
- **Panel local e IA:** son opcionales. Si los has incluido, sigue `docs/devsecops/dashboard.md`.
- **Despliegue en un servidor:** es opcional. Los apartados 5 y 6 solo se aplican cuando lo conectes.

No necesitas configurar etiquetas de despliegue para empezar a utilizar los análisis.

## 1. Publicar la configuración

Si empiezas desde cero:

1. Crea un repositorio vacío en GitHub, sin añadir README, licencia ni `.gitignore`: usarás los archivos del proyecto descargado.
2. Descomprime el ZIP generado y abre la carpeta del proyecto con tu herramienta de Git, por ejemplo GitHub Desktop.
3. Guarda el primer commit en `main` y publica los archivos en ese repositorio. Incluye las carpetas `.github` y `.devsecops`; no subas credenciales.
4. Crea la rama `develop` desde `main` y publícala también.

Si el repositorio ya existe, incorpora los archivos generados mediante una PR y conserva su historial. Si `develop` no existe, créala desde `main`.

## 2. Ejecutar el workflow

Abre **Actions** y revisa la ejecución de `Seguridad DevSecOps`. El check `security / aggregate` exige que el análisis termine sin errores técnicos. Puede estar verde aunque el informe indique `BLOCKED` o `REVIEW_REQUIRED`: estos estados conservan los hallazgos y requieren una decisión del responsable antes de desplegar `main`. Un check verde no significa que no existan vulnerabilidades.

El workflow y su núcleo se encuentran dentro del propio proyecto. GitHub Actions no necesita un token personal ni acceder al repositorio del inicializador.

## 3. Importar los rulesets

Accede a `Settings → Rules → Rulesets`, selecciona **New ruleset** y después **Import a ruleset**. Importa por separado:

- `.github/rulesets/develop-protection.json`
- `.github/rulesets/main-protection.json`

Antes de guardar, comprueba que cada ruleset protege la rama indicada. Si ya existe una regla anterior, actualízala; evita mantener reglas duplicadas. Conserva también los checks de compilación y pruebas que tenga el proyecto.

## 4. Comprobar la protección

Crea una rama `feature/*` y abre una pull request hacia `develop`. GitHub debe exigir el check `security / aggregate` antes de permitir la integración. Después, la promoción a `main` se realiza mediante otra pull request. Un error técnico impide integrar; los hallazgos se revisan y conservan en el informe.

Los rulesets impiden eliminar las ramas protegidas, evitan actualizaciones que no sean de avance rápido y obligan a utilizar PR con un análisis válido. Las aprobaciones antiguas se descartan cuando cambia el código.

La configuración permite trabajar solo: no exige aprobaciones de otra persona. En equipo se puede aumentar el número de revisiones obligatorias.

## 5. Opcional: configurar el despliegue en Dokploy

Los rulesets protegen la integración en GitHub. La autorización comprueba el informe de seguridad. Dokploy construye y despliega el commit que el workflow le indica. Son controles distintos.

El ZIP ya incorpora estos archivos, sin necesitar otra opción en el inicializador:

| Archivo | Función |
| --- | --- |
| `.github/workflows/authorize-main.yml` | Comprueba el informe del commit de `main` y devuelve si está autorizado. No llama a Dokploy. |
| `.github/workflows/deploy-dokploy.yml` | Llama al autorizador y solicita el despliegue solo si devuelve `allowed=true`. |
| `.devsecops/engine/scripts/deploy_dokploy.cjs` | Crea una etiqueta del commit autorizado, configura esa referencia en Dokploy y espera la confirmación del despliegue. |

**La integración está desactivada mientras `DOKPLOY_DEPLOY_ENABLED` no valga exactamente `true`.** Puedes usar los análisis, los rulesets y el panel sin configurar Dokploy. El workflow aparecerá omitido y no solicitará credenciales ni enviará peticiones al servidor.

### 5.1. Preparar el Compose de la aplicación

1. Conserva o crea el Dockerfile y el Compose de tu aplicación. El inicializador no los genera ni los sustituye. Prueba la aplicación con `docker compose up --build`.
2. La ruta predeterminada es `./compose.yml`. Si utilizas `docker-compose.yml`, `compose.main.yml` u otra ruta del repositorio, indícala mediante `DOKPLOY_COMPOSE_PATH` en GitHub.
3. Utiliza el Compose de la aplicación, **no `compose.security.yml`**, que corresponde al panel local. Solo se admite un archivo Compose por esta integración; si necesitas combinar varios archivos, prepara primero uno para el despliegue.
4. Para desplegar el código analizado, el servicio debe construir la aplicación desde este repositorio (`build`) y su Dockerfile. Una imagen externa con etiqueta mutable no queda vinculada al commit por crear `deploy-<SHA>`. Evita montajes de carpetas del ordenador local y guarda los secretos fuera de Git.

Si no tienes Compose, deja la integración desactivada. Los análisis siguen funcionando.

### 5.2. Crear el servicio en Dokploy

1. En Dokploy crea o selecciona un proyecto y su entorno.
2. Añade un servicio de tipo **Docker Compose**, no un servicio Application. Conecta tu cuenta o GitHub App y concede acceso al repositorio, también si es privado.
3. Selecciona el propietario y repositorio del proyecto. Puedes indicar `main` inicialmente. El workflow cambiará esa referencia por `deploy-<SHA>` antes de cada despliegue autorizado.
4. Indica la misma ruta Compose que usarás en GitHub y deja el comando de despliegue predeterminado, sin un comando personalizado.
5. **Desactiva Auto Deploy en Dokploy.** El despliegue lo solicitará GitHub después de la autorización. Desactiva también otros workflows o webhooks que desplieguen esta misma aplicación sin pasar por el control. Si ya tienes una integración propia, utiliza solo una para evitar solicitudes duplicadas.
6. Configura las variables de ejecución de tu aplicación en Dokploy (base de datos, claves u otras que necesite). Son diferentes de las variables de conexión de GitHub del apartado siguiente.
7. Guarda la configuración. No pulses Deploy para probar la autorización: ese botón es una vía manual independiente del workflow de GitHub.

### 5.3. Configurar GitHub

Abre **Settings → Secrets and variables → Actions** en el repositorio del proyecto. Usa variables y secretos de **repositorio**: este workflow no declara un GitHub Environment y no recibe sus valores.

En **Variables → New repository variable**, añade:

| Nombre | Valor |
| --- | --- |
| `DOKPLOY_URL` | URL HTTPS de tu panel de Dokploy, por ejemplo `https://deploy.ejemplo.dev`. No es el dominio de la aplicación ni debe incluir `/dashboard/...` o credenciales. |
| `DOKPLOY_COMPOSE_ID` | Identificador del servicio Compose de este proyecto. En la URL del servicio es el segmento después de `/services/compose/`, sin `?tab=...`. No copies el de otro proyecto. |
| `DOKPLOY_COMPOSE_PATH` | Opcional. Ruta relativa del Compose, por ejemplo `./docker-compose.yml`. Si no se configura, se usa `./compose.yml`. |
| `DOKPLOY_DEPLOY_ENABLED` | Déjala sin crear o con `false` hasta terminar la configuración. Luego establece `true`. |

En Dokploy, genera una API key desde la configuración de tu cuenta y comprueba que permite consultar y desplegar el servicio. En GitHub, **Secrets → New repository secret**, guarda esa clave como `DOKPLOY_API_KEY`. No la pegues en una variable pública, en el Compose ni en un archivo del repositorio.

El workflow utiliza el `GITHUB_TOKEN` automático con permisos de lectura de Actions y escritura de contenido para crear la etiqueta. No necesita un token personal de GitHub. Si una política de la organización impide esos permisos, debe revisarse esa política antes de habilitar la integración.

### 5.4. Configurar el dominio

1. Crea el registro DNS del dominio o subdominio de la aplicación para dirigirlo a tu servidor, según tu configuración de red.
2. En **Domains** del servicio Compose selecciona el servicio de la aplicación y su **puerto interno**, por ejemplo `8080` si Spring Boot escucha en ese puerto. No uses el puerto publicado en el equipo local, como `8082`.
3. Configura la ruta `/` y HTTPS según el proveedor de certificados y el proxy del servidor. Guarda los cambios.
4. Comprueba que la aplicación escucha en `0.0.0.0` dentro del contenedor y que el proxy puede alcanzarla. El dominio y los certificados se comprueban después del despliegue; el workflow no crea DNS ni certificados.

### 5.5. Habilitar y comprobar el recorrido

1. Revisa que los archivos generados estén publicados en `main` y que `main` sea la rama predeterminada. Configura también la protección de etiquetas descrita abajo.
2. Establece `DOKPLOY_DEPLOY_ENABLED=true` en las variables del repositorio.
3. Prepara un cambio en una rama `feature/*` y abre una PR. Puedes seguir `feature → develop → main`; los rulesets no obligan a que la PR hacia `main` proceda de `develop`.
4. Comprueba `security / aggregate` y fusiona la PR cuando corresponda. Espera al análisis del **nuevo commit de `main`**, aunque el análisis de la PR ya hubiera terminado.
5. Con `APPROVED`, se activa **Desplegar en Dokploy** automáticamente. El trabajo de autorización comprueba el informe y el de despliegue crea `deploy-<SHA>`, selecciona esa referencia en Dokploy y solicita la construcción.
6. En Actions comprueba que ambos trabajos terminan correctamente. El script espera un registro nuevo de Dokploy asociado al commit, con estado `done`; un despliegue antiguo no sirve como confirmación.
7. Abre la aplicación por HTTPS y comprueba sus funciones o su endpoint de salud. Un despliegue terminado en Dokploy no demuestra por sí solo que el dominio o todas las funciones respondan correctamente.

Cambiar la variable a `true` no inicia por sí solo un despliegue. Si el análisis del último commit de `main` ya terminó, puedes abrir **Actions → Desplegar en Dokploy → Run workflow**, elegir `main` y dejar la aceptación desmarcada si está `APPROVED`.

Para desactivar futuros despliegues cambia `DOKPLOY_DEPLOY_ENABLED` a `false`. Si ya hay una ejecución en curso, revisa su estado: cambiar la variable no deshace un despliegue solicitado.

### 5.6. Resolver problemas habituales

| Situación | Comprobación |
| --- | --- |
| El workflow está omitido | Revisar que la variable de repositorio `DOKPLOY_DEPLOY_ENABLED` sea `true`. Solo admite `main` y análisis de un push del propio repositorio. |
| Falta configuración | Revisar los nombres y el ámbito de las variables y de `DOKPLOY_API_KEY`. La integración habilitada falla de forma explícita si falta algo. |
| No encuentra el Compose | Comprobar `DOKPLOY_COMPOSE_PATH` en el commit publicado, no solo en el disco local. |
| Dokploy devuelve 401 o 403 | Revisar la API key y sus permisos. No publicar la clave en logs o incidencias. |
| Repositorio o Auto Deploy incorrectos | Seleccionar el mismo propietario/repositorio y desactivar Auto Deploy y los comandos personalizados. |
| Informe ausente, antiguo o incompleto | Esperar al análisis del último commit de `main`. No basta el informe de la PR. |
| Fallo o espera agotada en Dokploy | Revisar los logs del nuevo despliegue y su estado antes de reintentar. No lanzar otra solicitud mientras sigue construyendo. |
| El despliegue termina pero la web no responde | Revisar DNS, HTTPS, servicio elegido, puerto interno y logs de arranque. |

### Otros proveedores o un workflow propio

Puedes seguir utilizando `authorize-main.yml` desde un workflow reutilizable. El trabajo de despliegue debe depender del autorizador con `needs` y comprobar `allowed == 'true'`, además de utilizar su salida `sha` en el checkout y en el proveedor. No habilites simultáneamente la integración generada si ya tienes otra que despliega el mismo servicio. No utilices `always()` ni `continue-on-error` para eludir la decisión.

### Solo si tu despliegue utiliza etiquetas `deploy-*`

Una etiqueta identifica el commit que debe desplegarse. Para impedir que después se cambie o se borre, configura una vez esta protección en el repositorio:

1. Abre **Settings → Rules → Rulesets → New ruleset → New tag ruleset**.
2. Escribe **Proteger etiquetas de despliegue** y selecciona **Active**.
3. En **Add target → Include by pattern**, añade `deploy-*`.
4. Marca **Restrict updates**, **Restrict deletions** y **Block force pushes**.
5. Deja **Restrict creations** desmarcado y la lista de excepciones vacía. Guarda con **Create**.

Esto permite crear etiquetas nuevas y protege las existentes. No añade pasos a cada despliegue. Si tu integración no utiliza estas etiquetas, omite este apartado.

## 6. Revisar y aceptar el riesgo

Antes de fusionar la PR, revisa los hallazgos y decide cuáles corregir. Después de fusionarla, espera al análisis del commit final de `main`:

- `APPROVED`: el despliegue continúa automáticamente al terminar el análisis del push a `main`, si has conectado el workflow como indica el apartado anterior.
- `BLOCKED` o `REVIEW_REQUIRED`: no despliega automáticamente. Puedes corregir los hallazgos y repetir el análisis o aceptar explícitamente el riesgo en una ejecución manual.
- Error técnico, informe ausente o análisis en curso: el despliegue se detiene.

Si decides continuar con los hallazgos, abre **Actions → Desplegar en Dokploy → Run workflow**, selecciona `main` y marca **Acepto los hallazgos del análisis**. La casilla está desmarcada por defecto y solo permite aceptar riesgos en una ejecución manual.

Espera a que terminen todos los analizadores, incluido `container`, y se genere el informe final antes de lanzar el despliegue manual. Poder fusionar una PR no sustituye el análisis del nuevo commit de `main`.

No necesitas copiar el SHA ni escribir comentarios. El workflow comprueba automáticamente el commit y registra en su resumen quién lanzó la ejecución, el commit y el resultado del análisis. Los hallazgos se conservan en el informe.
