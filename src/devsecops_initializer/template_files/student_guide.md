# Guía DevSecOps del proyecto

Paquete DevSecOps instalado: **{devsecops_version}**.

## Qué se ha detectado

- Perfil: {facts_profile_name}
- Construcción: {facts_build_system}
- Java: {facts_java_version}
- Contenedores: {container}

## Cuándo se ejecuta

El workflow se ejecuta con cada cambio y también cada lunes a las 06:00 UTC. La ejecución semanal permite detectar vulnerabilidades publicadas después del último commit.

## Flujo de trabajo recomendado

1. Trabaja en una rama `feature/*` y sube cambios pequeños.
2. Revisa SAST, SCA y contenedores como controles distintos.
3. Corrige primero los hallazgos críticos y confirma la solución con una nueva ejecución.
4. Integra en `develop` cuando el informe sea válido y la política esté aprobada.
5. Promueve a `main` y producción únicamente el mismo commit que ha superado los controles.

## Cómo leer el informe

Un hallazgo incluye tecnología, herramienta, severidad, componente o regla y ubicación. Si una remediación modifica `pom.xml` o `Dockerfile`, debe mostrar la línea localizada, el contenido eliminado y el contenido añadido. “No aplicable” no significa “cero vulnerabilidades”: significa que ese control no corresponde al proyecto detectado.

## Comprobación

Abre la ejecución de GitHub Actions, descarga el artefacto `devsecops-security-report-*` y confirma que los resultados pertenecen al SHA analizado. Después de una corrección, vuelve a ejecutar el análisis; no cierres un hallazgo solo porque el código haya cambiado.
