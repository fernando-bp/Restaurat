from __future__ import annotations

from sqlalchemy.orm import declarative_base

Base = declarative_base()

# Import all models so metadata is populated for Alembic and SQLAlchemy.
from app.infrastructure.database.models.usuario import UsuarioORM  # noqa: F401
from app.infrastructure.database.models.rol import RolORM  # noqa: F401
from app.infrastructure.database.models.empleado import EmpleadoORM  # noqa: F401
from app.infrastructure.database.models.mesa import MesaORM, OrdenORM  # noqa: F401
from app.infrastructure.database.models.receta import RecetaORM  # noqa: F401
from app.infrastructure.database.models.orden_item import OrdenItemORM  # noqa: F401
from app.infrastructure.database.models.ingrediente import IngredienteORM  # noqa: F401
from app.infrastructure.database.models.inventario import InventarioORM  # noqa: F401
from app.infrastructure.database.models.unidades_medida import UnidadMedidaORM  # noqa: F401
from app.infrastructure.database.models.receta_detalle import RecetaDetalleORM  # noqa: F401
from app.infrastructure.database.models.receta_sub import RecetaSubORM  # noqa: F401
from app.infrastructure.database.models.movimientos_inventario import MovimientosInventarioORM  # noqa: F401
from app.infrastructure.database.models.pago import PagoORM  # noqa: F401
from app.infrastructure.database.models.pago_dividido import PagoDivididoORM, PersonaPagoDivididoORM  # noqa: F401
from app.integrations.bold_qr.models import BoldPaymentIntentORM  # noqa: F401
