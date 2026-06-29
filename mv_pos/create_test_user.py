import asyncio
import sys
from sqlalchemy import select
from app.infrastructure.database.connection import async_session
from app.infrastructure.database.models.usuario import UsuarioORM
from app.infrastructure.database.models.rol import RolORM
from app.infrastructure.security.password import hash_password
from datetime import datetime


async def create_test_user():
    """Crea un usuario de prueba con contraseña hasheada correctamente."""
    
    async with async_session() as session:
        # Obtener el rol de administrador o el primer rol disponible
        result = await session.execute(select(RolORM).limit(1))
        rol = result.scalar_one_or_none()
        
        if not rol:
            print("❌ No hay roles en la BD. Crea al menos un rol primero.")
            sys.exit(1)
        
        # Datos del usuario de prueba
        username = "admin"
        password = "admin123"  # Cambiar en producción
        nombre_completo = "Administrador Sistema"
        
        # Generar hash correcto con bcrypt 4.0.1 compatible con passlib
        password_hash = hash_password(password)
        
        # Verificar si el usuario ya existe
        result = await session.execute(
            select(UsuarioORM).where(UsuarioORM.username == username)
        )
        existing_user = result.scalar_one_or_none()
        
        if existing_user:
            print(f"⚠️  Usuario '{username}' ya existe. Actualizando...")
            existing_user.password_hash = password_hash
            existing_user.updated_at = datetime.utcnow()
            await session.merge(existing_user)
        else:
            # Crear nuevo usuario
            nuevo_usuario = UsuarioORM(
                nombre_completo=nombre_completo,
                username=username,
                password_hash=password_hash,
                rol_id=rol.id,
                activo=True,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            )
            session.add(nuevo_usuario)
        
        await session.commit()
        print(f"✅ Usuario '{username}' creado/actualizado correctamente")
        print(f"   Contraseña: {password}")
        print(f"   Rol: {rol.nombre}")
        print(f"   Hash: {password_hash[:20]}...")


if __name__ == "__main__":
    asyncio.run(create_test_user())
