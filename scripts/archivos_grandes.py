"""Comprime, verifica y restaura los archivos grandes con Python estandar."""

import argparse
import gzip
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ARCHIVE = ROOT / "archivos_grandes"
MANIFEST = ARCHIVE / "manifest.json"
CHUNK_SIZE = 48 * 1024 * 1024
SOURCES = (
    "bin/cublas64_12.dll",
    "bin/cublasLt64_12.dll",
    "bin/ggml-cuda.dll",
    "models/gemma-3-1b-it-Q4_K_M.gguf",
    "models/nomic-embed-text-v1.5.Q4_K_M.gguf",
    "yolo/yolov3.weights",
)


def digest_file(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def inside(base, relative):
    target = (base / relative).resolve()
    if target == base.resolve() or not target.is_relative_to(base.resolve()):
        raise ValueError(f"Ruta fuera del proyecto: {relative}")
    return target


def pack():
    if ARCHIVE.exists():
        raise FileExistsError("archivos_grandes ya existe; usa verify o restore.")
    for relative in SOURCES:
        if not (ROOT / relative).is_file():
            raise FileNotFoundError(relative)
    ARCHIVE.mkdir()
    manifest = {"version": 1, "format": "independent-gzip-parts", "files": []}
    for relative in SOURCES:
        source = ROOT / relative
        digest = hashlib.sha256()
        entry = {"path": relative, "size": 0, "parts": []}
        directory = ARCHIVE / relative
        directory.mkdir(parents=True)
        print(f"Comprimiendo {relative}...", flush=True)
        with source.open("rb") as stream:
            for number, block in enumerate(iter(lambda: stream.read(CHUNK_SIZE), b""), 1):
                digest.update(block)
                entry["size"] += len(block)
                compressed = gzip.compress(block, compresslevel=6, mtime=0)
                if len(compressed) >= 50 * 1024 * 1024:
                    raise ValueError("Una parte supera el limite previsto de 50 MiB")
                part = directory / f"parte-{number:04d}.gz"
                with part.open("xb") as output:
                    output.write(compressed)
                entry["parts"].append({
                    "path": part.relative_to(ARCHIVE).as_posix(),
                    "size": len(compressed),
                    "sha256": hashlib.sha256(compressed).hexdigest(),
                })
        entry["sha256"] = digest.hexdigest()
        manifest["files"].append(entry)
        print(f"  {len(entry['parts'])} partes guardadas", flush=True)
    MANIFEST.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print("Compresion terminada. Ejecuta verify antes de publicar.")


def process(restore):
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    if manifest["version"] != 1 or manifest["format"] != "independent-gzip-parts":
        raise ValueError("Formato de archivo no compatible")
    for entry in manifest["files"]:
        target = inside(ROOT, entry["path"])
        if restore and target.exists():
            if target.stat().st_size == entry["size"] and digest_file(target) == entry["sha256"]:
                print(f"Ya existe y coincide: {entry['path']}", flush=True)
                continue
            raise FileExistsError(f"No se sobrescribe un archivo distinto: {target}")
        temporary = target.with_name(target.name + ".restaurando")
        output = None
        created = False
        digest = hashlib.sha256()
        size = 0
        try:
            if restore:
                target.parent.mkdir(parents=True, exist_ok=True)
                output = temporary.open("xb")
                created = True
            for part in entry["parts"]:
                path = inside(ARCHIVE, part["path"])
                if path.stat().st_size != part["size"] or digest_file(path) != part["sha256"]:
                    raise ValueError(f"Parte incompleta o alterada: {part['path']}")
                with gzip.open(path, "rb") as stream:
                    for block in iter(lambda: stream.read(1024 * 1024), b""):
                        size += len(block)
                        if size > entry["size"]:
                            raise ValueError(f"Tamano descomprimido inesperado: {entry['path']}")
                        digest.update(block)
                        if output is not None:
                            output.write(block)
            if size != entry["size"] or digest.hexdigest() != entry["sha256"]:
                raise ValueError(f"El archivo reconstruido no coincide: {entry['path']}")
            if output is not None:
                output.close()
                output = None
                # Never overwrite a file created by another process during restoration.
                if target.exists():
                    raise FileExistsError(target)
                temporary.rename(target)
                created = False
            print(f"{'Restaurado' if restore else 'Verificado'}: {entry['path']}", flush=True)
        finally:
            if output is not None:
                output.close()
            if created:
                temporary.unlink(missing_ok=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("pack", "verify", "restore"))
    args = parser.parse_args()
    if args.action == "pack":
        pack()
    else:
        process(restore=args.action == "restore")


if __name__ == "__main__":
    main()
