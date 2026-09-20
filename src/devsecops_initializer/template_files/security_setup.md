# Configuración de seguridad en GitHub

El proyecto incluye dos rulesets para proteger las ramas `develop` y `main`. La importación es manual y no requiere entregar un token con permisos administrativos.

## 1. Publicar la configuración

Sube los archivos generados a GitHub. Si la rama `develop` todavía no existe, créala desde `main`.

## 2. Ejecutar el workflow

Abre la pestaña **Actions** y comprueba que el workflow `Seguridad DevSecOps` termina correctamente. Esta primera ejecución registra el check `security / aggregate` que utilizarán los rulesets.

El workflow y su núcleo se encuentran dentro del propio proyecto. GitHub Actions no necesita un token personal ni acceder al repositorio del inicializador.

## 3. Importar los rulesets

Accede a `Settings → Rules → Rulesets`, selecciona **New ruleset** y después **Import a ruleset**. Importa por separado:

- `.github/rulesets/develop-protection.json`
- `.github/rulesets/main-protection.json`

Antes de guardar, comprueba que cada ruleset protege la rama indicada.

## 4. Comprobar la protección

Crea una rama `feature/*` y abre una pull request hacia `develop`. GitHub debe exigir el check `security / aggregate` antes de permitir la integración. Después, la promoción a `main` se realiza mediante otra pull request.

Los rulesets impiden eliminar las ramas protegidas, evitan actualizaciones que no sean de avance rápido y obligan a utilizar pull requests con el análisis de seguridad superado.
