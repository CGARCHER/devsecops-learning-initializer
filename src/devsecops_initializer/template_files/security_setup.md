# Configuración de seguridad en GitHub

El proyecto incluye reglas para proteger `develop` y `main`. La importación es manual y no requiere entregar un token administrativo al inicializador.

## 1. Publicar la configuración

Sube los archivos generados a GitHub. Si la rama `develop` todavía no existe, créala desde `main`.

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

## 5. Conectar la autorización al despliegue

El inicializador incluye `.github/workflows/authorize-main.yml`. Comprueba el último análisis del commit de `main`, independientemente del entorno de destino. No despliega ni configura Dokploy u otro proveedor.

En tu workflow de despliegue, añade el disparador al terminar el análisis, la casilla y el trabajo de seguridad (conserva los demás inputs y trabajos). Publica este workflow en la rama predeterminada:

```yaml
on:
  workflow_run:
    workflows: ["Seguridad DevSecOps"]
    types: [completed]
    branches: [main]
  workflow_dispatch:
    inputs:
      accept_risk:
        description: Acepto los hallazgos del análisis
        type: boolean
        default: false

jobs:
  seguridad:
    if: >-
      github.event_name == 'workflow_dispatch' ||
      (github.event.workflow_run.conclusion == 'success' &&
       github.event.workflow_run.head_branch == 'main' &&
       github.event.workflow_run.event == 'push' &&
       github.event.workflow_run.head_repository.full_name == github.repository)
    permissions:
      contents: read
      actions: read
    uses: ./.github/workflows/authorize-main.yml
    with:
      accept_risk: ${{ inputs.accept_risk }}
```

En el trabajo que realiza el despliegue añade `needs: [seguridad]` e `if: needs.seguridad.outputs.allowed == 'true'`. Si ya tiene dependencias o condiciones, conserva las anteriores y añade estas comprobaciones. No utilices `always()` ni `continue-on-error` para eludir el resultado. Sin comprobar `allowed`, el trabajo podría continuar aunque la autorización automática deje los hallazgos pendientes de aceptación.

El despliegue y su checkout deben utilizar exactamente `${{ needs.seguridad.outputs.sha }}`, no volver a resolver la punta de `main`. En una ejecución automática, `github.sha` puede ser distinto del commit analizado. Todos los despliegues de `main` deben pasar por esta comprobación; un autodespliegue independiente del proveedor no queda protegido. En otras ramas, este workflow permite las pruebas de desarrollo sin exigir aceptación.

Añadir los archivos al ZIP no conecta automáticamente un despliegue existente: hay que incorporar esa dependencia. La conexión sigue el mecanismo de [workflows reutilizables de GitHub](https://docs.github.com/en/actions/how-tos/reuse-automations/reuse-workflows).

## 6. Revisar y aceptar el riesgo

Antes de fusionar la PR, revisa los hallazgos y decide cuáles corregir. Después de fusionarla, espera al análisis del commit final de `main`:

- `APPROVED`: el despliegue continúa automáticamente al terminar el análisis del push a `main`, si has conectado el workflow como indica el apartado anterior.
- `BLOCKED` o `REVIEW_REQUIRED`: requiere marcar la casilla de aceptación.
- Error técnico, informe ausente o análisis en curso: el despliegue se detiene.

Si decides continuar con los hallazgos, abre **Run workflow**, selecciona `main` y marca **Acepto los hallazgos del análisis**. La casilla está desmarcada por defecto y solo permite aceptar riesgos en una ejecución manual.

Espera a que terminen todos los analizadores, incluido `container`, y se genere el informe final antes de lanzar el despliegue manual. Poder fusionar una PR no sustituye el análisis del nuevo commit de `main`.

No necesitas copiar el SHA ni escribir comentarios. El workflow comprueba automáticamente el commit y registra en su resumen quién lanzó la ejecución, el commit y el resultado del análisis. Los hallazgos se conservan en el informe.
