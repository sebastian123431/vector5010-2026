# Proyecto completo en GitHub

El repositorio incluye el codigo, bases de datos, fotos, memoria, proyectos
adjuntos, registros y respaldos solicitados por su propietario. Los seis
modelos y bibliotecas mayores de 49 MiB se guardan completos, comprimidos
sin perdida y divididos en `archivos_grandes/`. Cada parte es menor de 50 MiB.
Esta version utiliza Git normal; no necesita Git LFS.

## Descargar y reconstruir los archivos grandes

Necesitas Git, Python 3.10 o posterior y espacio para la copia comprimida y
los originales reconstruidos. Desde PowerShell:

```powershell
git clone https://github.com/sebastian123431/vector5010-2026.git
cd vector5010-2026
python scripts/archivos_grandes.py restore
```

El comando restaura automaticamente los modelos en `models/`, las bibliotecas
en `bin/` y los pesos YOLO en `yolo/`. Verifica SHA-256 de cada parte y del
archivo completo antes de finalizar. Si un original ya existe y coincide,
lo conserva; si es distinto, se detiene sin sobrescribirlo.

Para comprobar todas las partes sin escribir los archivos reconstruidos:

```powershell
python scripts/archivos_grandes.py verify
```

No borres partes individuales: todas las partes enumeradas en
`archivos_grandes/manifest.json` son necesarias. Las partes son fragmentos gzip
independientes; usa el comando anterior para unir el contenido descomprimido
en el orden correcto.

Los originales siguen intactos en el computador donde se preparo la subida.
Git los ignora porque su copia completa ya esta en las partes comprimidas.
Para actualizar un modelo, genera un conjunto nuevo de partes y su manifiesto;
`pack` se niega a sobrescribir un archivo comprimido existente.

## Ejecutar la aplicacion

Instala las dependencias de `requirements.txt` y consulta `README.md`.
La clave de Django se obtiene de `DJANGO_SECRET_KEY` o del archivo local
`.django-secret-key`, excluido de Git junto con `.env`. La clave existente
se conserva en el computador original. En otro computador configura una
clave antes de iniciar la aplicacion; por ejemplo, para una sesion local:

```powershell
$env:DJANGO_SECRET_KEY = python -c "import secrets; print(secrets.token_urlsafe(50))"
```

## Publicar futuros cambios

```powershell
git status
git add .
git commit -m "Describe tus cambios"
git push
```

Cierra la aplicacion antes de guardar nuevas versiones de la base de datos.
Los archivos temporales SQLite `-wal` y `-shm` no se publican.

Las ramas `backup/antes-publicar` y `backup/antes-comprimir` son respaldos
locales. No las publiques: contienen archivos grandes sin dividir o referencias
LFS. Usa `git push` para publicar `main`, sin `--all` ni `--mirror`.

GitHub limita el tamano de cada archivo en Git normal:
https://docs.github.com/en/repositories/working-with-files/managing-large-files/about-large-files-on-github
