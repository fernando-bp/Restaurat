import React, { useState, useEffect } from 'react';
import './CierreCaja.css';

interface BilleteMoneda {
  denominacion: number;
  cantidad: number;
}

interface ConteoEfectivo {
  billetes: BilleteMoneda[];
  monedas: BilleteMoneda[];
}

interface ResumenCaja {
  fecha: string;
  total_ventas: number;
  total_efectivo_sistema: number;
  total_tarjeta_debito: number;
  total_tarjeta_credito: number;
  total_transferencia: number;
  por_forma_pago: Array<{ forma_pago: string; total: number; cantidad_transacciones: number }>;
}

interface ResultadoCierre {
  id: number;
  fecha: string;
  total_efectivo_sistema: number;
  total_efectivo_contado: number;
  diferencia_efectivo: number;
  diferencia_porcentaje: number | null;
  cuadra: boolean;
  total_tarjeta_debito: number;
  total_tarjeta_credito: number;
  total_transferencia: number;
  total_descuentos: number;
  observaciones?: string;
}

const BILLETES_DEFAULT = [
  { denominacion: 100000, cantidad: 0 },
  { denominacion: 50000, cantidad: 0 },
  { denominacion: 20000, cantidad: 0 },
  { denominacion: 10000, cantidad: 0 },
  { denominacion: 5000, cantidad: 0 },
  { denominacion: 2000, cantidad: 0 },
  { denominacion: 1000, cantidad: 0 },
];

const MONEDAS_DEFAULT = [
  { denominacion: 1000, cantidad: 0 },
  { denominacion: 500, cantidad: 0 },
  { denominacion: 200, cantidad: 0 },
  { denominacion: 100, cantidad: 0 },
  { denominacion: 50, cantidad: 0 },
];

export const CierreCaja: React.FC = () => {
  const [paso, setPaso] = useState<'resumen' | 'conteo' | 'resultado'>('resumen');
  const [resumen, setResumen] = useState<ResumenCaja | null>(null);
  const [billetes, setBilletes] = useState<BilleteMoneda[]>(BILLETES_DEFAULT);
  const [monedas, setMonedas] = useState<BilleteMoneda[]>(MONEDAS_DEFAULT);
  const [observaciones, setObservaciones] = useState('');
  const [resultado, setResultado] = useState<ResultadoCierre | null>(null);
  const [cargando, setCargando] = useState(false);
  const [error, setError] = useState('');

  // Obtener resumen al cargar
  useEffect(() => {
    obtenerResumen();
  }, []);

  const obtenerResumen = async () => {
    try {
      setCargando(true);
      const response = await fetch('/api/v1/cierre-caja/resumen', {
        headers: {
          Authorization: `Bearer ${localStorage.getItem('access_token')}`,
        },
      });

      if (!response.ok) throw new Error('Error obteniendo resumen');
      const data = await response.json();
      setResumen(data);
      setPaso('resumen');
    } catch (err) {
      setError('Error al obtener resumen de caja');
      console.error(err);
    } finally {
      setCargando(false);
    }
  };

  const calcularTotalEfectivo = (): number => {
    const totalBilletes = billetes.reduce((sum, b) => sum + b.denominacion * b.cantidad, 0);
    const totalMonedas = monedas.reduce((sum, m) => sum + m.denominacion * m.cantidad, 0);
    return totalBilletes + totalMonedas;
  };

  const manejarCambioBillete = (index: number, cantidad: number) => {
    const nuevosBilletes = [...billetes];
    nuevosBilletes[index].cantidad = cantidad;
    setBilletes(nuevosBilletes);
  };

  const manejarCambioMoneda = (index: number, cantidad: number) => {
    const nuevasMonedas = [...monedas];
    nuevasMonedas[index].cantidad = cantidad;
    setMonedas(nuevasMonedas);
  };

  const ejecutarCierre = async () => {
    try {
      setCargando(true);
      
      // Primero validar que todas las mesas estén cerradas
      const validationResponse = await fetch('/api/v1/cierre-caja/validar-mesas', {
        headers: {
          Authorization: `Bearer ${localStorage.getItem('access_token')}`,
        },
      });
      
      if (!validationResponse.ok) throw new Error('Error validando mesas');
      const validationData = await validationResponse.json();
      
      if (!validationData.todas_cerradas) {
        setError(
          `❌ No se puede cerrar caja. Hay ${validationData.cantidad_mesas_abiertas} mesa(s) aún abiertas: ${validationData.mesas_abiertas.join(', ')}. Ciérrales primero.`
        );
        setCargando(false);
        return;
      }
      
      const payload = {
        efectivo_contado: { billetes, monedas },
        observaciones,
      };

      const response = await fetch('/api/v1/cierre-caja/ejecutar', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${localStorage.getItem('access_token')}`,
        },
        body: JSON.stringify(payload),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Error ejecutando cierre');
      }
      
      const data = await response.json();
      setResultado(data);
      setPaso('resultado');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Error al ejecutar cierre de caja');
      console.error(err);
    } finally {
      setCargando(false);
    }
  };

  const imprimirReporte = () => {
    if (!resultado) return;

    const contenido = `
      ================================
      CIERRE DE CAJA DIARIO
      ================================
      Fecha: ${resultado.fecha}
      
      RESUMEN POR FORMA DE PAGO
      --------------------------------
      Efectivo (Sistema):     $${resultado.total_efectivo_sistema.toFixed(0)}
      Tarjeta Débito:        $${resultado.total_tarjeta_debito.toFixed(0)}
      Tarjeta Crédito:       $${resultado.total_tarjeta_credito.toFixed(0)}
      Transferencia:         $${resultado.total_transferencia.toFixed(0)}
      Total Ventas:          $${(resultado.total_efectivo_sistema + resultado.total_tarjeta_debito + resultado.total_tarjeta_credito + resultado.total_transferencia).toFixed(0)}
      
      CUADRE DE EFECTIVO
      --------------------------------
      Total Sistema:         $${resultado.total_efectivo_sistema.toFixed(0)}
      Total Contado:         $${resultado.total_efectivo_contado.toFixed(0)}
      Diferencia:            $${resultado.diferencia_efectivo.toFixed(0)}
      Porcentaje:            ${resultado.diferencia_porcentaje?.toFixed(2)}%
      
      ESTADO: ${resultado.cuadra ? '✓ CUADRADO' : '✗ DIFERENCIA'}
      ${resultado.observaciones ? `Observaciones: ${resultado.observaciones}` : ''}
      ================================
    `;

    const ventana = window.open('', '', 'height=600,width=800');
    if (ventana) {
      ventana.document.write('<pre>' + contenido + '</pre>');
      ventana.document.close();
      ventana.print();
    }
  };

  if (cargando && !resumen) {
    return <div className="cierre-caja-container">Cargando...</div>;
  }

  return (
    <div className="cierre-caja-container">
      {error && <div className="cierre-caja-error">{error}</div>}

      {paso === 'resumen' && resumen && (
        <div className="cierre-caja-panel">
          <h2>Resumen de Caja - {resumen.fecha}</h2>

          <div className="cierre-caja-resumen-grid">
            <div className="cierre-caja-resumen-card">
              <span className="cierre-caja-label">Total Ventas</span>
              <strong className="cierre-caja-monto">${resumen.total_ventas.toFixed(0)}</strong>
            </div>
            <div className="cierre-caja-resumen-card">
              <span className="cierre-caja-label">Efectivo</span>
              <strong className="cierre-caja-monto">${resumen.total_efectivo_sistema.toFixed(0)}</strong>
            </div>
            <div className="cierre-caja-resumen-card">
              <span className="cierre-caja-label">Tarjeta Débito</span>
              <strong className="cierre-caja-monto">${resumen.total_tarjeta_debito.toFixed(0)}</strong>
            </div>
            <div className="cierre-caja-resumen-card">
              <span className="cierre-caja-label">Tarjeta Crédito</span>
              <strong className="cierre-caja-monto">${resumen.total_tarjeta_credito.toFixed(0)}</strong>
            </div>
            <div className="cierre-caja-resumen-card">
              <span className="cierre-caja-label">Transferencia</span>
              <strong className="cierre-caja-monto">${resumen.total_transferencia.toFixed(0)}</strong>
            </div>
          </div>

          <button
            className="cierre-caja-btn-primary"
            onClick={() => {
              setBilletes(BILLETES_DEFAULT);
              setMonedas(MONEDAS_DEFAULT);
              setPaso('conteo');
            }}
          >
            Continuar con Conteo de Efectivo
          </button>
        </div>
      )}

      {paso === 'conteo' && (
        <div className="cierre-caja-panel">
          <h2>Conteo de Efectivo</h2>

          <div className="cierre-caja-conteo">
            <div className="cierre-caja-seccion">
              <h3>Billetes</h3>
              {billetes.map((billete, idx) => (
                <div key={idx} className="cierre-caja-fila">
                  <label>${billete.denominacion.toLocaleString()}</label>
                  <div className="cierre-caja-input-group">
                    <input
                      type="number"
                      min="0"
                      value={billete.cantidad}
                      onChange={(e) => manejarCambioBillete(idx, parseInt(e.target.value) || 0)}
                      className="cierre-caja-input"
                    />
                    <span className="cierre-caja-subtotal">
                      = ${(billete.denominacion * billete.cantidad).toLocaleString()}
                    </span>
                  </div>
                </div>
              ))}
            </div>

            <div className="cierre-caja-seccion">
              <h3>Monedas</h3>
              {monedas.map((moneda, idx) => (
                <div key={idx} className="cierre-caja-fila">
                  <label>${moneda.denominacion.toLocaleString()}</label>
                  <div className="cierre-caja-input-group">
                    <input
                      type="number"
                      min="0"
                      value={moneda.cantidad}
                      onChange={(e) => manejarCambioMoneda(idx, parseInt(e.target.value) || 0)}
                      className="cierre-caja-input"
                    />
                    <span className="cierre-caja-subtotal">
                      = ${(moneda.denominacion * moneda.cantidad).toLocaleString()}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          </div>

          <div className="cierre-caja-total">
            <span>Total Contado:</span>
            <strong>${calcularTotalEfectivo().toLocaleString()}</strong>
          </div>

          <div className="cierre-caja-observaciones">
            <label>Observaciones (opcional)</label>
            <textarea
              value={observaciones}
              onChange={(e) => setObservaciones(e.target.value)}
              placeholder="Ej: Diferencia por cliente con dinero falso"
              maxLength={500}
            />
          </div>

          <div className="cierre-caja-botones">
            <button className="cierre-caja-btn-secondary" onClick={() => setPaso('resumen')}>
              Atrás
            </button>
            <button className="cierre-caja-btn-primary" onClick={ejecutarCierre} disabled={cargando}>
              {cargando ? 'Procesando...' : 'Finalizar Cierre'}
            </button>
          </div>
        </div>
      )}

      {paso === 'resultado' && resultado && (
        <div className="cierre-caja-panel">
          <h2>Resultado del Cierre</h2>

          <div className={`cierre-caja-resultado ${resultado.cuadra ? 'cuadrado' : 'diferencia'}`}>
            <h3>{resultado.cuadra ? '✓ CAJA CUADRADA' : '✗ DIFERENCIA DETECTADA'}</h3>

            <div className="cierre-caja-resultado-detalle">
              <div className="cierre-caja-fila-resultado">
                <span>Total Sistema:</span>
                <strong>${resultado.total_efectivo_sistema.toLocaleString()}</strong>
              </div>
              <div className="cierre-caja-fila-resultado">
                <span>Total Contado:</span>
                <strong>${resultado.total_efectivo_contado.toLocaleString()}</strong>
              </div>
              <div className="cierre-caja-fila-resultado diferencia">
                <span>Diferencia:</span>
                <strong className={resultado.diferencia_efectivo >= 0 ? 'positiva' : 'negativa'}>
                  {resultado.diferencia_efectivo >= 0 ? '+' : ''}${resultado.diferencia_efectivo.toLocaleString()}
                  {resultado.diferencia_porcentaje !== null && (
                    <span> ({resultado.diferencia_porcentaje.toFixed(2)}%)</span>
                  )}
                </strong>
              </div>
            </div>

            <div className="cierre-caja-resumen-final">
              <div className="cierre-caja-item">
                <span>Tarjeta Débito:</span>
                <strong>${resultado.total_tarjeta_debito.toLocaleString()}</strong>
              </div>
              <div className="cierre-caja-item">
                <span>Tarjeta Crédito:</span>
                <strong>${resultado.total_tarjeta_credito.toLocaleString()}</strong>
              </div>
              <div className="cierre-caja-item">
                <span>Transferencia:</span>
                <strong>${resultado.total_transferencia.toLocaleString()}</strong>
              </div>
            </div>

            {resultado.observaciones && (
              <div className="cierre-caja-observaciones-resultado">
                <strong>Observaciones:</strong>
                <p>{resultado.observaciones}</p>
              </div>
            )}
          </div>

          <div className="cierre-caja-botones">
            <button className="cierre-caja-btn-secondary" onClick={imprimirReporte}>
              🖨️ Imprimir Reporte
            </button>
            <button className="cierre-caja-btn-primary" onClick={obtenerResumen}>
              Nuevo Cierre
            </button>
          </div>
        </div>
      )}
    </div>
  );
};

export default CierreCaja;
