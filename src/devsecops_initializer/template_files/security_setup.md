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

En tu workflow de despliegue, añade este trabajo bajo `jobs`:

```yaml
  seguridad:
    permissions:
      contents: read
      actions: read
      pull-requests: read
    uses: ./.github/workflows/authorize-main.yml
```

En el trabajo que realiza el despliegue añade `needs: [seguridad]`. Si ya tiene dependencias, conserva las anteriores y añade `seguridad`. Mantén la condición normal de éxito: no utilices `always()` ni `continue-on-error` para eludir el resultado.

El despliegue debe utilizar exactamente `${{ github.sha }}`, no volver a resolver la punta de `main`. Todos los despliegues de `main` deben pasar por esta comprobación; un autodespliegue independiente del proveedor no queda protegido. En otras ramas, este workflow termina sin exigir aceptación, para permitir las pruebas de desarrollo.

Añadir los archivos al ZIP no conecta automáticamente un despliegue existente: hay que incorporar esa dependencia. La conexión sigue el mecanismo de [workflows reutilizables de GitHub](https://docs.github.com/en/actions/how-tos/reuse-automations/reuse-workflows).

## 6. Revisar y aceptar el riesgo

Antes de fusionar la PR, revisa los hallazgos y decide cuáles corregir. Después de fusionarla, espera al análisis del commit final de `main`:

- `APPROVED`: no requiere aceptación adicional.
- `BLOCKED` o `REVIEW_REQUIRED`: requiere un comentario de aceptación.
- Error técnico, informe ausente o análisis en curso: el despliegue se detiene.

Si se decide aceptar el riesgo, quien fusionó la PR debe añadir en esa misma PR un comentario nuevo, después del análisis:

```text
Acepto el riesgo de SHA_COMPLETO: justificación.
```

Sustituye `SHA_COMPLETO` por los 40 caracteres del commit final de `main`. La persona debe conservar permisos de escritura, mantenimiento o administración. Puede ser el propio autor si trabaja solo; en equipo será la persona responsable que fusionó la PR.

Explica el motivo y, si procede, cuándo revisarás los hallazgos. La fecha de revisión es una indicación para el equipo y no se comprueba automáticamente. El comentario no debe editarse: otro commit o un análisis nuevo requiere otra aceptación. Los hallazgos y su estado original se conservan en el informe.

Después ejecuta el workflow de despliegue desde `main`. Comprueba que un riesgo sin aceptar se detiene y que una aceptación válida permite continuar con ese mismo commit.
