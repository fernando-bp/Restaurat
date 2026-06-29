from enum import Enum


class FormaPagoEnum(str, Enum):
    """Formas de pago soportadas (RF-27 a RF-34)"""
    EFECTIVO = "efectivo"
    TARJETA_DEBITO = "tarjeta_debito"
    TARJETA_CREDITO = "tarjeta_credito"
    NEQUI = "nequi"
    DAVIPLATA = "daviplata"
    PSE = "pse"
    QR_BREB = "qr_breb"
    CORTESIA = "cortesia"

    def __str__(self):
        return self.value


class TipoMovimientoPagoEnum(str, Enum):
    """Tipos de movimiento de pago para auditoría"""
    PAGO_PROCESADO = "pago_procesado"
    PAGO_CANCELADO = "pago_cancelado"
    CAMBIO_ENTREGADO = "cambio_entregado"
    DESCUENTO_APLICADO = "descuento_aplicado"
