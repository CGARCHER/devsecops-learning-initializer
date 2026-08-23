# DevSecOps Learning Initializer

Prototipo educativo que incorpora una base DevSecOps en proyectos existentes sin obligar a adaptar manualmente cada repositorio. Spring Boot es el primer perfil implementado, pero el núcleo no depende de un framework concreto.

El asistente:

- importa un ZIP o analiza una carpeta local;
- detecta el framework, el gestor de construcción y la presencia de contenedores;
- presenta un plan antes de escribir, distinguiendo archivos añadidos, modificados y no aplicables;
- genera un ZIP nuevo y conserva intacto el original;
- añade un workflow autónomo, su núcleo de análisis, rulesets para `develop` y `main` y una guía breve para el estudiante;
- registra la versión del paquete DevSecOps y avisa al volver a importar una configuración anterior;
- deja las decisiones específicas del framework en perfiles ampliables.

## Probar la interfaz

```bash
python -m devsecops_initializer.web --port 8080
```

Abre `http://localhost:8080`, selecciona el ZIP de un proyecto Spring Boot y revisa el diagnóstico. Para ejecutar sin instalar el paquete:

```bash
set PYTHONPATH=src
python -m devsecops_initializer.web --port 8080
```

## Uso por consola

```bash
python -m devsecops_initializer.cli inspect ruta/al/proyecto
python -m devsecops_initializer.cli generate ruta/al/proyecto salida.zip
```

## Arquitectura ampliable

Cada perfil implementa cuatro operaciones: `detect`, `inspect`, `plan` y `learning_content`. Para incorporar otro framework se añade una clase en `profiles/` y se registra en `registry.py`; el importador, la interfaz y el generador no cambian.

El ZIP generado incorpora su propio workflow y el núcleo mínimo necesario en `.devsecops/engine`. El repositorio del alumno no depende del repositorio del inicializador para ejecutar GitHub Actions.

La versión del paquete queda registrada en `.devsecops/manifest.json`. Cuando se vuelve a importar un proyecto, el asistente indica si ya está actualizado o si puede generar una copia con una versión más reciente.

## Pruebas

```bash
python -m unittest discover -s tests -v
```

Este repositorio forma parte de un TFM y prioriza la trazabilidad pedagógica: explica qué se incorpora, por qué se incorpora y cómo comprobarlo.

## Despliegue con Docker y Dokploy

El servicio puede desplegarse desde el `Dockerfile` como una aplicación única, sin base de datos ni volúmenes persistentes. Expone el puerto `8080` y el endpoint de salud `/health`.

En Dokploy se configura el repositorio, el puerto interno `8080`, un dominio HTTPS y el `Dockerfile` de la raíz. Como los alumnos envían código fuente, el acceso debe limitarse al grupo autorizado, por ejemplo mediante Cloudflare Access.

Los proyectos se conservan temporalmente durante un máximo de 30 minutos. Después de generar el ZIP de salida se eliminan del servidor. El proyecto original nunca se modifica.
## Selección de capacidades

La base DevSecOps se incorpora siempre. Desde la interfaz se puede añadir de forma opcional el panel local con remediación asistida por IA. Esta opción genera `compose.security.yml`, una configuración de ejemplo y una guía, pero no copia los Compose específicos de la aplicación ni modifica su infraestructura.
