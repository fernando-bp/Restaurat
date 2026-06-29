from __future__ import annotations

import mimetypes
import os
import re
import unicodedata
from pathlib import Path

from sqlalchemy import select, text

from app.infrastructure.database.connection import engine
from app.infrastructure.database.models.receta import RecetaORM

IMAGE_DIR = Path(__file__).resolve().parents[2] / 'FronendMagic' / 'src' / 'features' / 'cocina' / 'recetas'
IMAGE_EXTENSIONS = {'.png', '.jpg', '.jpeg', '.gif', '.webp'}


def normalize_text(value: str) -> str:
    value = unicodedata.normalize('NFKD', value)
    value = ''.join(ch for ch in value if not unicodedata.combining(ch))
    value = value.upper()
    value = re.sub(r'[\s_]+', ' ', value)
    value = re.sub(r'[^A-Z0-9 .]', '', value)
    return value.strip()


def build_image_map(image_dir: Path) -> dict[str, Path]:
    image_map: dict[str, Path] = {}
    if not image_dir.exists():
        raise FileNotFoundError(f'Image directory not found: {image_dir}')

    for path in sorted(image_dir.iterdir()):
        if path.is_file() and path.suffix.lower() in IMAGE_EXTENSIONS:
            name = normalize_text(path.stem)
            if name in image_map:
                print(f'Warning: duplicate normalized name {name} for {path} and {image_map[name]}')
            image_map[name] = path
    return image_map


def guess_mime_type(path: Path) -> str:
    mime, _ = mimetypes.guess_type(path.name)
    return mime or 'application/octet-stream'


async def add_image_columns() -> None:
    async with engine.begin() as conn:
        await conn.execute(text(
            'ALTER TABLE recetas '
            'ADD COLUMN IF NOT EXISTS imagen LONGBLOB NULL, '
            'ADD COLUMN IF NOT EXISTS imagen_tipo VARCHAR(100) NULL'
        ))


async def load_recipes() -> list[tuple[int, str]]:
    async with engine.connect() as conn:
        result = await conn.execute(select(RecetaORM.id, RecetaORM.nombre).order_by(RecetaORM.id))
        return [(row.id, row.nombre) for row in result.all()]


async def update_recipe_image(recipe_id: int, image_path: Path, mime_type: str) -> None:
    data = image_path.read_bytes()
    async with engine.begin() as conn:
        await conn.execute(
            text('UPDATE recetas SET imagen = :imagen, imagen_tipo = :imagen_tipo WHERE id = :id'),
            {'imagen': data, 'imagen_tipo': mime_type, 'id': recipe_id},
        )


async def main() -> None:
    print('Scanning recipe image folder:', IMAGE_DIR)
    image_map = build_image_map(IMAGE_DIR)
    print('Found', len(image_map), 'image files')

    await add_image_columns()
    recipes = await load_recipes()
    print('Loaded', len(recipes), 'recipes from database')

    updated = []
    missing = []

    for recipe_id, recipe_name in recipes:
        normalized_name = normalize_text(recipe_name)
        image_path = image_map.get(normalized_name)
        if image_path is None:
            missing.append(recipe_name)
            continue

        mime_type = guess_mime_type(image_path)
        await update_recipe_image(recipe_id, image_path, mime_type)
        updated.append((recipe_name, image_path.name, mime_type))

    print('\nSummary:')
    print('Updated recipe images:', len(updated))
    for recipe_name, filename, mime in updated:
        print(f'  - {recipe_name} <= {filename} ({mime})')

    if missing:
        print('\nRecipes without matching image file:', len(missing))
        for recipe_name in missing:
            print('  -', recipe_name)

    unmatched_files = [name for name in image_map.keys() if name not in {normalize_text(rn) for _, rn in recipes}]
    if unmatched_files:
        print('\nImage files not matched to any recipe name:', len(unmatched_files))
        for name in unmatched_files:
            print('  -', name)


if __name__ == '__main__':
    import asyncio

    asyncio.run(main())
