# Arquitectura del asistente

El proyecto separa tres decisiones que no deben evolucionar al mismo ritmo:

1. El núcleo importa el proyecto, aplica límites de seguridad al ZIP, construye un diagnóstico, presenta el plan y genera una copia.
2. Los perfiles conocen la estructura de un framework. Spring Boot es el primer perfil; su lógica no se reparte por la interfaz ni por el importador.
3. El workflow autónomo y los adaptadores ejecutan herramientas concretas y transforman sus informes al modelo común.

## Contrato de un perfil

Un perfil implementa:

- `detect(root)`: devuelve una confianza entre 0 y 100 y nunca modifica el proyecto.
- `inspect(root, confidence)`: obtiene hechos normalizados.
- `plan(facts)`: añade decisiones específicas y explica los casos no aplicables.
- `learning_content(facts)`: adapta la ayuda al contexto encontrado.

El registro elige el perfil con mayor confianza y rechaza el proyecto si ninguno alcanza el umbral mínimo. Cuando aparezcan varios proyectos compatibles no se debe elegir uno de forma silenciosa: una siguiente versión debe mostrar los candidatos al usuario.

## Modelo de cambios

El plan utiliza tres estados:

- `add`: el fichero no existía.
- `modify`: el fichero ya existe; la vista debe enseñar línea, contenido eliminado y contenido añadido.
- `not_applicable`: el control no corresponde al proyecto. No equivale a un análisis limpio.

La primera versión siempre devuelve otro ZIP. La escritura directa, la creación de ramas o una pull request quedan fuera del MVP porque requieren una autorización distinta y una revisión explícita.

## Paquete autónomo y versionado

Cada proyecto recibe su propio `.github/workflows/devsecops.yml` y el núcleo mínimo en `.devsecops/engine`. De esta forma, GitHub Actions no depende de permisos sobre el repositorio del inicializador y el alumno puede revisar los controles incorporados.

`.devsecops/manifest.json` registra la versión del paquete. Al importar de nuevo el proyecto, el asistente compara esa versión con la actual y avisa antes de generar una copia actualizada. El inicializador no sustituye una versión más reciente por otra anterior.

## Incorporar otro framework

Para añadir un perfil nuevo se crea una implementación de `FrameworkProfile`, se registra y se añaden fixtures propios. El núcleo, la API web y el formato público de `AnalysisPlan` deben permanecer sin cambios. La ampliación solo se considera validada cuando existe una prueba completa con un proyecto real del nuevo framework.

## Separación entre tecnología y herramienta

El estudiante aprende tres tecnologías de análisis: SAST, SCA y contenedores. Semgrep y Trivy son las herramientas elegidas en este prototipo. Si se sustituyen, el adaptador debe conservar la categoría y producir el mismo modelo normalizado; la política y la explicación educativa no deberían depender del nombre del proveedor.
