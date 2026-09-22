# Arquitectura del asistente

El proyecto separa tres decisiones que no deben evolucionar al mismo ritmo:

1. El núcleo importa el proyecto, aplica límites de seguridad al ZIP, construye un diagnóstico, presenta el plan y genera una copia.
2. Los perfiles conocen la estructura de un framework. Spring Boot es el primer perfil; su lógica no se reparte por la interfaz ni por el importador.
3. El workflow autónomo y los adaptadores ejecutan herramientas concretas y transforman sus informes al modelo común.

## Organización del código

- `web.py` recibe las peticiones y devuelve el diagnóstico o el ZIP generado.
- `sessions.py` guarda las sesiones de carga, limita su número y elimina los proyectos caducados. El bloqueo protege el acceso desde peticiones simultáneas.
- `importer.py` valida y extrae el ZIP. `safe_extract_zip` devuelve un `ExtractedProject` con `root` (el proyecto) y `workspace` (la carpeta temporal completa que debe limpiarse). No se deduce la carpeta temporal a partir del nombre del proyecto.
- `service.py` coordina el análisis y genera una copia. La carpeta de salida utiliza `TemporaryDirectory` para limpiarse también si la generación falla.
- `updates.py` limpia las dos carpetas propias del paquete en la copia temporal. El catálogo `template_files/legacy_files.json` identifica por SHA-256 los archivos del prototipo anterior, normalizando los saltos de línea. No se eliminan archivos personalizados por coincidir solo en el nombre. Si una integración todavía referencia un archivo que se retiraría, se pide adaptarla antes de generar la copia.
- `templates.py` prepara los valores variables y los documentos JSON. Los textos largos y las configuraciones se guardan en `template_files/`, incluida en el paquete instalable.

Las plantillas `config.yml` y `student_guide.md` utilizan campos entre llaves que completa `templates.py`. En esas dos plantillas, una llave literal debe escribirse duplicada. Las demás se cargan sin sustituciones.

## Contrato de un perfil

Un perfil implementa:

- `detect(root)`: devuelve una confianza entre 0 y 100 y nunca modifica el proyecto.
- `inspect(root, confidence)`: obtiene hechos normalizados.
- `plan(facts)`: añade decisiones específicas y explica los casos no aplicables.
- `learning_content(facts)`: adapta la ayuda al contexto encontrado.

El registro elige el perfil con mayor confianza y rechaza el proyecto si ninguno alcanza el umbral mínimo. Cuando aparezcan varios proyectos compatibles no se debe elegir uno de forma silenciosa: una siguiente versión debe mostrar los candidatos al usuario.

## Modelo de cambios

El plan utiliza cuatro estados:

- `add`: el fichero no existía.
- `modify`: el archivo o carpeta ya existe y se sustituye por completo; la vista explica el alcance, sin presentar un resumen como una diferencia línea a línea.
- `delete`: se elimina un archivo antiguo reconocido de la copia.
- `not_applicable`: el control no corresponde al proyecto. No equivale a un análisis limpio.

La primera versión siempre devuelve otro ZIP. La escritura directa, la creación de ramas o una pull request quedan fuera del MVP porque requieren una autorización distinta y una revisión explícita.

## Paquete autónomo y versionado

Cada proyecto recibe su propio `.github/workflows/devsecops.yml` y el núcleo mínimo en `.devsecops/engine`. De esta forma, GitHub Actions no depende de permisos sobre el repositorio del inicializador y el alumno puede revisar los controles incorporados.

`.devsecops/manifest.json` registra la versión del paquete. Al importar de nuevo el proyecto, el asistente compara esa versión con la actual y avisa antes de generar una copia actualizada. El inicializador no sustituye una versión más reciente por otra anterior.

## Incorporar otro framework

Para añadir un perfil nuevo se crea una implementación de `FrameworkProfile`, se registra y se añaden fixtures propios. El núcleo, la API web y el formato público de `AnalysisPlan` deben permanecer sin cambios. La ampliación solo se considera validada cuando existe una prueba completa con un proyecto real del nuevo framework.

## Separación entre tecnología y herramienta

El estudiante aprende tres tecnologías de análisis: SAST, SCA y contenedores. Semgrep y Trivy son las herramientas elegidas en este prototipo. Si se sustituyen, el adaptador debe conservar la categoría y producir el mismo modelo normalizado; la política y la explicación educativa no deberían depender del nombre del proveedor.
