from __future__ import annotations

import mimetypes
import re
import unicodedata
from pathlib import Path
from urllib.parse import urlparse

import mysql.connector

IMAGE_DIR = Path(__file__).resolve().parents[2] / "FronendMagic" / "src" / "features" / "cocina" / "recetas"
ENV_PATH = Path(__file__).resolve().parents[1] / ".env"
IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".webp"}


def normalize_text(value: str) -> str:
    value = unicodedata.normalize("NFKD", value)
    value = "".join(ch for ch in value if not unicodedata.combining(ch))
    value = value.lower()
    value = re.sub(r"[\s_]+", " ", value)
    value = re.sub(r"[^a-z0-9 ]", "", value)
    return value.strip()


def load_env(env_path: Path) -> dict[str, str]:
    if not env_path.exists():
        raise FileNotFoundError(f"Env file not found: {env_path}")

    env_data: dict[str, str] = {}
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        env_data[key.strip()] = value.strip().strip('"').strip("'")
    return env_data


def parse_database_url(database_url: str) -> dict[str, str]:
    parsed = urlparse(database_url)
    scheme = parsed.scheme.split("+")[0]
    if scheme not in {"mysql", "mysql+aiomysql"}:
        raise ValueError(f"Unsupported database URL scheme: {parsed.scheme}")

    return {
        "host": parsed.hostname or "localhost",
        "port": parsed.port or 3306,
        "user": parsed.username or "root",
        "password": parsed.password or "",
        "database": parsed.path.lstrip("/") or "",
    }


def build_image_map(image_dir: Path) -> dict[str, Path]:
    if not image_dir.exists():
        raise FileNotFoundError(f"Image folder not found: {image_dir}")

    image_map: dict[str, Path] = {}
    for path in sorted(image_dir.iterdir()):
        if path.is_file() and path.suffix.lower() in IMAGE_EXTENSIONS:
            key = normalize_text(path.stem)
            if key in image_map:
                print(f"Warning: duplicate image name after normalization: {key} -> {path.name} (existing {image_map[key].name})")
            image_map[key] = path
    return image_map


def ensure_columns(cursor: mysql.connector.cursor.MySQLCursor) -> None:
    for column_name, column_definition in [
        ("imagen", "LONGBLOB"),
        ("imagen_tipo", "VARCHAR(100)"),
    ]:
        cursor.execute(
            "SELECT COUNT(*) FROM information_schema.COLUMNS "
            "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'recetas' "
            "AND COLUMN_NAME = %s",
            (column_name,),
        )
        exists = cursor.fetchone()[0] > 0
        if not exists:
            print(f"Creating missing column: {column_name}")
            cursor.execute(f"ALTER TABLE recetas ADD COLUMN {column_name} {column_definition} NULL")


def main() -> None:
    env = load_env(ENV_PATH)
    if "DATABASE_URL" not in env:
        raise KeyError("DATABASE_URL not found in .env")

    connection_data = parse_database_url(env["DATABASE_URL"])
    print("Connecting to database:", connection_data["database"])

    image_map = build_image_map(IMAGE_DIR)
    print(f"Found {len(image_map)} image files in {IMAGE_DIR}")

    connection = mysql.connector.connect(
        host=connection_data["host"],
        port=connection_data["port"],
        user=connection_data["user"],
        password=connection_data["password"],
        database=connection_data["database"],
    )

    try:
        cursor = connection.cursor()
        ensure_columns(cursor)

        cursor.execute("SELECT id, nombre FROM recetas ORDER BY id")
        recetas = cursor.fetchall()
        print(f"Loaded {len(recetas)} recipes from the database")

        updated = 0
        missing = []

        for receta_id, nombre in recetas:
            key = normalize_text(str(nombre))
            image_path = image_map.get(key)
            if image_path is None:
                missing.append(nombre)
                continue

            with open(image_path, "rb") as f:
                image_blob = f.read()

            mime_type = mimetypes.guess_type(image_path.name)[0] or "application/octet-stream"
            cursor.execute(
                "UPDATE recetas SET imagen = %s, imagen_tipo = %s WHERE id = %s",
                (image_blob, mime_type, receta_id),
            )
            updated += 1
            print(f"Updated recipe {receta_id}: {nombre} <- {image_path.name} ({mime_type})")

        connection.commit()
        print(f"\nFinished. Updated {updated} recipes.")
        if missing:
            print(f"Recipes without matching image: {len(missing)}")
            for nombre in missing:
                print(" -", nombre)

        unmatched = sorted(name for name in image_map if name not in {normalize_text(str(nombre)) for _, nombre in recetas})
        if unmatched:
            print(f"\nImage files not matched to any recipe: {len(unmatched)}")
            for name in unmatched:
                print(" -", name)

    finally:
        connection.close()


if __name__ == "__main__":
    main()
