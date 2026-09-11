# Publicar cambios en GitHub

Desde esta carpeta, en PowerShell:

```powershell
git status
git add .
git commit -m "Describe tus cambios"
git push
```

La rama `main` corresponde al repositorio
https://github.com/sebastian123431/vector5010-2026.

## Archivos que se conservan solamente en tu computador

El archivo `.gitignore` excluye los modelos `*.gguf`, los pesos `*.weights`,
los ejecutables y DLL descargados de `bin/`, las bases de datos SQLite,
fotos, conversaciones, memoria generada, proyectos adjuntos de
`vectorapp/workspace/`, registros, respaldos y archivos temporales de Python.
Excluirlos de Git no los elimina del disco. GitHub no es un respaldo de estos
archivos: conserva una copia por separado si la necesitas.

GitHub bloquea los archivos mayores de 100 MiB en Git normal:
https://docs.github.com/en/repositories/working-with-files/managing-large-files/about-large-files-on-github

Al clonar en otro computador, instala las dependencias de `requirements.txt`,
coloca las bibliotecas y ejecutables de inferencia en `bin/`, los modelos
indicados en `models/Modelfile.chat` y `models/Modelfile.embed` en `models/`,
y los pesos YOLO en `yolo/yolov3.weights`. Ejecuta `python manage.py migrate`
para crear una base de datos nueva. Consulta `README.md` para ejecutar el proyecto.

La clave de Django se obtiene de `DJANGO_SECRET_KEY` o del archivo local
`.django-secret-key`, excluido de Git. En un clon nuevo debes configurar uno
de los dos antes de iniciar la aplicación. Por ejemplo, para una sesión local:

```powershell
$env:DJANGO_SECRET_KEY = python -c "import secrets; print(secrets.token_urlsafe(50))"
python manage.py migrate
```

El commit original anterior a la limpieza se conserva en la rama local
`backup/antes-publicar`. Esa rama contiene los archivos excluidos y no se debe
publicar. Para subir el código usa `git push`, sin `--all` ni `--mirror`.
