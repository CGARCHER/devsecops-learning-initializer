# Flujo recomendado para una práctica

## 1. Preparar

El alumno crea el proyecto con Spring Initializr o parte de una aplicación existente. Después trabaja en una rama `feature/*` y conserva un punto de retorno antes de incorporar la configuración.

## 2. Importar y revisar

El ZIP se analiza localmente. Antes de descargar el resultado se revisa el perfil detectado y se comprueba que las rutas corresponden al proyecto real. El alumno debe poder explicar por qué cada control es aplicable.

## 3. Generar y comparar

El asistente genera una copia. Se comparan los dos árboles y se revisan de forma especial `.github/workflows/devsecops.yml`, `.devsecops/config.yml`, `.devsecops/manifest.json` y la guía generada. El manifiesto permite conocer la versión del paquete incorporado. No se sustituye el original sin revisar.

## 4. Ejecutar

La rama se publica y GitHub Actions analiza el SHA de esa rama. SAST, SCA y contenedores se leen por separado. Un error técnico se corrige antes de interpretar el resultado.

El análisis también se repite cada lunes, aunque no existan nuevos commits. Así se pueden detectar vulnerabilidades que hayan sido publicadas después de la última modificación del proyecto.

## 5. Corregir y comprobar

El alumno selecciona un hallazgo, consulta la evidencia y prepara una corrección pequeña. Después ejecuta pruebas y un nuevo análisis. La tarea termina cuando puede relacionar la corrección con una evidencia posterior, no cuando desaparece visualmente una tarjeta del panel.

## 6. Promover

El recorrido recomendado es `feature/* → develop → main`. El destino puede ser cualquier entorno: lo que se controla es el commit de `main` que se despliega. El workflow de despliegue debe llamar a `authorize-main.yml` y depender de su resultado, como explica el `SECURITY_SETUP.md` generado.

Un estado `APPROVED` permite continuar. Para `BLOCKED` o `REVIEW_REQUIRED`, quien fusionó la PR debe aceptar el riesgo mediante un comentario nuevo con el SHA completo y una justificación, después del último análisis de ese commit. Puede ser el propio alumno si trabaja solo. Los errores técnicos, informes ausentes o análisis incompletos detienen el despliegue. Aceptar el riesgo no elimina los hallazgos.
