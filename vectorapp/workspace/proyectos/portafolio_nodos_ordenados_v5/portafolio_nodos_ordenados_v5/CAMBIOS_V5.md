# Portafolio V5 — grafo → explorador ordenado

Esta versión reforma la navegación sin eliminar la identidad original del portafolio.

## Flujo principal

1. El inicio conserva un mapa de nodos con Perfil, Proyectos, Habilidades, Experiencia, Estudios, Contacto e Idiomas.
2. Durante el scroll de escritorio, los nodos abandonan progresivamente su distribución radial y se ordenan en columna.
3. En el explorador, esa columna se convierte en navegación sticky a la izquierda.
4. Cada módulo es un acordeón independiente: se pueden dejar abiertos uno, varios o todos.
5. En móvil la columna se convierte en una rail horizontal sticky para no ocupar ancho útil.

## Contenido conservado

- Perfil y acceso a Sobre mí / retrato digital.
- ControlBins como caso principal, arquitectura, problema, rol, solución, resultado y flujo de sincronización.
- Habilidades técnicas por Backend, Mobile, Datos, Herramientas e Infraestructura.
- Experiencia laboral.
- Estudios, título y certificaciones con evidencia visual.
- Visor de evidencia con zoom y arrastre.
- Ruta a INACAP solicitando geolocalización únicamente al pulsar el botón de ruta.
- Contacto protegido mediante el endpoint existente `/api/reveal-contact/`.
- Idiomas.

## Archivos principales de la reforma

- `templates/templatesapp/index.html`
- `static/portafoliosapp/css/portfolio-v5.css`
- `static/portafoliosapp/js/portfolio-v5.js`

Los antiguos `style.css` y `main.js` se conservaron para no destruir trabajo previo y como referencia, pero la página principal usa los archivos V5.

## Validación

La suite contiene 23 pruebas y todas pasan en la revisión V5. Se añadieron pruebas específicas para la nueva estructura, acordeones independientes, scroll morph, contacto/evidencias/ruta y navegación responsive.
