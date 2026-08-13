# DevSecOps Learning Initializer

Prototipo educativo que incorpora una base DevSecOps en proyectos existentes sin obligar a adaptar manualmente cada repositorio. Spring Boot es el primer perfil implementado, pero el núcleo no depende de un framework concreto.

El asistente:

- importa un ZIP o analiza una carpeta local;
- detecta el framework, el gestor de construcción y la presencia de contenedores;
- presenta un plan antes de escribir, distinguiendo archivos añadidos, modificados y no aplicables;
- genera un ZIP nuevo y conserva intacto el original;
- añade un flujo de seguridad y una guía breve para el estudiante;
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

El flujo generado llama al workflow reutilizable incluido en este repositorio. Antes de utilizarlo desde otros repositorios hay que publicar este proyecto y ajustar `workflowRepository` en `.devsecops/config.yml` o indicar el repositorio desde la interfaz.

## Pruebas

```bash
python -m unittest discover -s tests -v
```

Este repositorio forma parte de un TFM y prioriza la trazabilidad pedagógica: explica qué se incorpora, por qué se incorpora y cómo comprobarlo.

