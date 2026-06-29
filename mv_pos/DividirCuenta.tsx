import React, { useState, useEffect } from 'react';
import './DividirCuenta.css';

interface Producto {
  id: number;
  nombre: string;
  cantidad: number;
  precio_unitario: number;
  foto_url?: string;
}

interface PersonaPago {
  numero_persona: number;
  monto: number;
  pagado: boolean;
  forma_pago?: string;
  monto_recibido?: number;
  cambio_entregado?: number;
  pagado_at?: string;
}

interface ResumenDivision {
  id: number;
  orden_id: number;
  numero_personas: number;
  monto_total: number;
  monto_por_persona: number;
  personas_pagadas: number;
  completado: boolean;
  personas: PersonaPago[];
}

interface DividirCuentaProps {
  orden_id: number;
  monto_total: number;
  productos?: Producto[];
  onComplete?: () => void;
  onCancel?: () => void;
}

export const DividirCuenta: React.FC<DividirCuentaProps> = ({
  orden_id,
  monto_total,
  productos = [],
  onComplete,
  onCancel,
}) => {
  const [paso, setPaso] = useState<'seleccionar' | 'pagos'>('seleccionar');
  const [numeroPersonas, setNumeroPersonas] = useState(2);
  const [division, setDivision] = useState<ResumenDivision | null>(null);
  const [cargando, setCargando] = useState(false);
  const [error, setError] = useState('');
  const [pagosRegistrados, setPagosRegistrados] = useState<Map<number, PersonaPago>>(new Map());
  const [personasExpandidas, setPersonasExpandidas] = useState<Set<number>>(new Set([1]));

  const FORMAS_PAGO = [
    { id: 'efectivo', label: 'Efectivo', icon: '💵' },
    { id: 'tarjeta_debito', label: 'Tarjeta', icon: '💳' },
    { id: 'transferencia', label: 'Transferencia', icon: '📋' },
    { id: 'otro', label: 'Otro', icon: '⭕' },
  ];

  const crearDivision = async () => {
    setCargando(true);
    setError('');
    try {
      const response = await fetch('/api/v1/pagos-divididos/crear', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.getItem('access_token')}`,
        },
        body: JSON.stringify({
          orden_id,
          numero_personas: numeroPersonas,
          monto_total,
        }),
      });

      if (!response.ok) {
        const data = await response.json();
        throw new Error(data.detail || 'Error al crear división');
      }

      const data = await response.json();
      setDivision(data);
      setPaso('pagos');
    } catch (err: any) {
      setError(err.message || 'Error al crear división');
    } finally {
      setCargando(false);
    }
  };

  const registrarPago = async (
    persona: PersonaPago,
    formaPago: string,
    montoRecibido?: number,
    referencia?: string,
    comprobante?: string
  ) => {
    setCargando(true);
    setError('');
    try {
      const payload: any = {
        pago_dividido_id: division!.id,
        numero_persona: persona.numero_persona,
        forma_pago: formaPago,
      };

      if (formaPago === 'efectivo') {
        payload.monto_recibido = montoRecibido;
      } else if (formaPago.includes('tarjeta')) {
        payload.referencia_datafono = referencia;
      } else {
        payload.numero_comprobante = comprobante;
      }

      const response = await fetch(`/api/v1/pagos-divididos/${division!.id}/pagar`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.getItem('access_token')}`,
        },
        body: JSON.stringify(payload),
      });

      if (!response.ok) {
        const data = await response.json();
        throw new Error(data.detail || 'Error al registrar pago');
      }

      const resultado = await response.json();
      
      const nuevoPago: PersonaPago = {
        numero_persona: persona.numero_persona,
        monto: persona.monto,
        pagado: true,
        forma_pago: formaPago,
        monto_recibido: montoRecibido,
        cambio_entregado: resultado.cambio_entregado,
        pagado_at: resultado.pagado_at,
      };
      
      const nuevosPagos = new Map(pagosRegistrados);
      nuevosPagos.set(persona.numero_persona, nuevoPago);
      setPagosRegistrados(nuevosPagos);

      if (resultado.completado_division) {
        setTimeout(() => onComplete?.(), 1000);
      }
    } catch (err: any) {
      setError(err.message || 'Error al registrar pago');
    } finally {
      setCargando(false);
    }
  };

  const togglePersona = (numero: number) => {
    const nuevas = new Set(personasExpandidas);
    if (nuevas.has(numero)) {
      nuevas.delete(numero);
    } else {
      nuevas.add(numero);
    }
    setPersonasExpandidas(nuevas);
  };

  const renderSeleccionar = () => (
    <div className="dividir-seleccionar">
      <div className="encabezado-division">
        <h3>¿ENTRE CUÁNTAS PERSONAS?</h3>
      </div>

      <div className="selector-personas">
        <button className="btn-menos" onClick={() => setNumeroPersonas(Math.max(2, numeroPersonas - 1))}>−</button>
        <div className="numero-personas-grande">{numeroPersonas}</div>
        <button className="btn-mas" onClick={() => setNumeroPersonas(Math.min(20, numeroPersonas + 1))}>+</button>
      </div>

      <p className="texto-personas">personas</p>

      <div className="opciones-rapidas">
        {[2, 3, 4, 5].map((n) => (
          <button
            key={n}
            className={`btn-opcion ${numeroPersonas === n ? 'activo' : ''}`}
            onClick={() => setNumeroPersonas(n)}
          >
            {n}
          </button>
        ))}
      </div>

      <div className="resumen-precio">
        <span className="label">Cada persona paga</span>
        <span className="precio">${(monto_total / numeroPersonas).toLocaleString('es-CO', {maximumFractionDigits: 2})}</span>
      </div>

      <button
        className="btn-aplicar-division"
        onClick={crearDivision}
        disabled={cargando}
      >
        Aplicar división →
      </button>
    </div>
  );

  const renderPagos = () => {
    const pagosRestantes = division!.numero_personas - division!.personas_pagadas;
    
    return (
      <div className="dividir-pagos">
        {productos.length > 0 && (
          <div className="seccion-productos">
            <h4 className="titulo-productos">PRODUCTO</h4>
            <div className="lista-productos">
              {productos.map((prod) => (
                <div key={prod.id} className="item-producto">
                  {prod.foto_url && (
                    <img src={prod.foto_url} alt={prod.nombre} className="foto-producto" />
                  )}
                  <div className="info-producto">
                    <span className="nombre-producto">{prod.nombre}</span>
                    <span className="cant-producto">×{prod.cantidad}</span>
                  </div>
                  <div className="precio-producto">
                    <span className="precio-unitario">${prod.precio_unitario.toLocaleString('es-CO', {maximumFractionDigits: 0})}</span>
                    <span className="subtotal">${(prod.cantidad * prod.precio_unitario).toLocaleString('es-CO', {maximumFractionDigits: 0})}</span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        <div className="encabezado-pagos">
          <span className="contador-pagos">{division!.personas_pagadas} de {division!.numero_personas} pagaron</span>
          <span className="editar-link">Editar</span>
        </div>

        <div className="barra-progreso-pagos">
          <div className="relleno" style={{ width: `${(division!.personas_pagadas / division!.numero_personas) * 100}%` }} />
        </div>

        <div className="monto-progreso">
          <span>${(division!.personas_pagadas * division!.monto_por_persona).toLocaleString('es-CO', {maximumFractionDigits: 0})} / ${monto_total.toLocaleString('es-CO', {maximumFractionDigits: 0})}</span>
        </div>

        <div className="lista-personas">
          {division!.personas.map((persona, index) => {
            const pagado = pagosRegistrados.get(persona.numero_persona) || persona;
            const expandida = personasExpandidas.has(persona.numero_persona);
            
            return (
              <div key={persona.numero_persona} className="persona-card">
                <div 
                  className={`persona-header ${pagado.pagado ? 'pagado' : ''}`}
                  onClick={() => !pagado.pagado && togglePersona(persona.numero_persona)}
                >
                  <div className="persona-info">
                    <div className="persona-avatar">👤</div>
                    <div>
                      <div className="persona-nombre">Persona {persona.numero_persona}</div>
                      <div className="persona-deuda">Debe ${persona.monto.toLocaleString('es-CO', {maximumFractionDigits: 2})}</div>
                    </div>
                  </div>
                  <div className="persona-monto">
                    <span>${persona.monto.toLocaleString('es-CO', {maximumFractionDigits: 2})}</span>
                    {!pagado.pagado && (
                      <span className="expand-icon">⌄</span>
                    )}
                  </div>
                </div>

                {expandida && !pagado.pagado && (
                  <FormaPagoPersona
                    persona={persona}
                    onPagar={(formaPago, montoRecibido, ref, comp) =>
                      registrarPago(persona, formaPago, montoRecibido, ref, comp)
                    }
                    formasPago={FORMAS_PAGO}
                    cargando={cargando}
                  />
                )}
              </div>
            );
          })}
        </div>

        {pagosRestantes > 0 && (
          <div className="faltan-pagos">
            ⭕ Faltan {pagosRestantes} pagos
          </div>
        )}

        <button className="btn-cancelar-pagos" onClick={onCancel}>
          × Cancelar
        </button>
      </div>
    );
  };

  return (
    <div className="dividir-cuenta-modal">
      <div className="contenido">
        {error && <div className="alerta-error">{error}</div>}

        {paso === 'seleccionar' && renderSeleccionar()}
        {paso === 'pagos' && renderPagos()}
      </div>
    </div>
  );
};

interface FormaPagoPersonaProps {
  persona: PersonaPago;
  onPagar: (formaPago: string, montoRecibido?: number, ref?: string, comp?: string) => void;
  formasPago: any[];
  cargando: boolean;
}

const FormaPagoPersona: React.FC<FormaPagoPersonaProps> = ({
  persona,
  onPagar,
  formasPago,
  cargando,
}) => {
  const [formaPago, setFormaPago] = useState('efectivo');
  const [montoRecibido, setMontoRecibido] = useState(persona.monto);
  const [referencia, setReferencia] = useState('');
  const [comprobante, setComprobante] = useState('');

  return (
    <div className="forma-pago-section">
      <div className="label-forma">MÉTODO DE PAGO</div>

      <div className="opciones-forma">
        {formasPago.map((fp) => (
          <button
            key={fp.id}
            className={`btn-forma-pago ${formaPago === fp.id ? 'activo' : ''}`}
            onClick={() => setFormaPago(fp.id)}
          >
            <span className="icon-forma">{fp.icon}</span>
            <span className="label-forma-pago">{fp.label}</span>
          </button>
        ))}
      </div>

      {formaPago === 'efectivo' && (
        <div className="input-efectivo">
          <label>Monto recibido</label>
          <input
            type="number"
            value={montoRecibido}
            onChange={(e) => setMontoRecibido(Number(e.target.value))}
            min={persona.monto}
          />
          <small>Cambio: ${(montoRecibido - persona.monto).toLocaleString('es-CO', {maximumFractionDigits: 0})}</small>
        </div>
      )}

      <button
        className="btn-cobrar"
        onClick={() => onPagar(formaPago, montoRecibido, referencia, comprobante)}
        disabled={cargando}
      >
        ⭕ Cobrar ${persona.monto.toLocaleString('es-CO', {maximumFractionDigits: 2})}
      </button>
    </div>
  );
};

export default DividirCuenta;
