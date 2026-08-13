# Flujo recomendado para una práctica

## 1. Preparar

El alumno crea el proyecto con Spring Initializr o parte de una aplicación existente. Después trabaja en una rama `feature/*` y conserva un punto de retorno antes de incorporar la configuración.

## 2. Importar y revisar

El ZIP se analiza localmente. Antes de descargar el resultado se revisa el perfil detectado y se comprueba que las rutas corresponden al proyecto real. El alumno debe poder explicar por qué cada control es aplicable.

## 3. Generar y comparar

El asistente genera una copia. Se comparan los dos árboles y se revisan de forma especial `.github/workflows/devsecops.yml`, `.devsecops/config.yml` y la guía generada. No se sustituye el original sin revisar.

## 4. Ejecutar

La rama se publica y GitHub Actions analiza el SHA de esa rama. SAST, SCA y contenedores se leen por separado. Un error técnico se corrige antes de interpretar el resultado.

## 5. Corregir y comprobar

El alumno selecciona un hallazgo, consulta la evidencia y prepara una corrección pequeña. Después ejecuta pruebas y un nuevo análisis. La tarea termina cuando puede relacionar la corrección con una evidencia posterior, no cuando desaparece visualmente una tarjeta del panel.

## 6. Promover

El recorrido recomendado es `feature/* → develop → main → producción`. La promoción utiliza el mismo SHA que ha superado la política. Un estado `BLOCKED`, `REVIEW_REQUIRED` o `ANALYSIS_ERROR` no se despliega.

