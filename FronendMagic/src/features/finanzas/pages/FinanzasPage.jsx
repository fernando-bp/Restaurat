import { useMemo, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import { createCompra, createGasto, getCompras, getEstadosFacturaOrdenes, getGastos, getReporteFinanciero } from '../services/finanzasService'
import { formatCOP } from '../../../shared/utils/currency'

const tabs = ['Dashboard', 'Ventas', 'Rankings', 'Categorias', 'Rentabilidad', 'Estado de Resultados', 'Gastos', 'Compras', 'Conciliacion', 'Comparativo']

const today = new Date()
const firstDay = new Date(today.getFullYear(), today.getMonth(), 1).toISOString().slice(0, 10)
const todayText = today.toISOString().slice(0, 10)

const money = formatCOP

function pct(value) {
  const numberValue = Number(value || 0)
  return `${numberValue > 0 ? '+' : ''}${numberValue.toFixed(1)}%`
}

function statusClass(value = '') {
  const normalized = value.toLowerCase()
  if (normalized.includes('pag')) return 'finance-status finance-status--paid'
  if (normalized.includes('cancel')) return 'finance-status finance-status--cancel'
  return 'finance-status finance-status--partial'
}

function invoiceStatusLabel(status = '') {
  const normalized = status.toLowerCase()
  if (['validated', 'validada', 'aceptada'].includes(normalized)) return 'Emitida'
  if (['rejected', 'rechazada'].includes(normalized)) return 'Rechazada'
  if (normalized === 'error') return 'Error'
  return 'Pendiente'
}

function invoiceStatusClass(status = '') {
  const normalized = status.toLowerCase()
  if (['validated', 'validada', 'aceptada'].includes(normalized)) return 'finance-invoice-status finance-invoice-status--ok'
  if (['rejected', 'rechazada', 'error'].includes(normalized)) return 'finance-invoice-status finance-invoice-status--error'
  return 'finance-invoice-status finance-invoice-status--pending'
}

function MetricCard({ icon, label, value, change }) {
  return (
    <article className="finance-metric-card">
      <div className="finance-metric-card__top">
        <span className="finance-metric-icon">{icon}</span>
        <span className={`finance-change ${Number(change || 0) >= 0 ? 'is-up' : 'is-down'}`}>{pct(change)}</span>
      </div>
      <small>{label}</small>
      <strong>{value}</strong>
    </article>
  )
}

function BarChart({ rows = [] }) {
  const max = Math.max(...rows.map((row) => Number(row.ventas || 0)), 1)
  return (
    <div className="finance-bar-chart">
      {rows.map((row) => (
        <div key={row.fecha} className="finance-bar-item">
          <div className="finance-bar-track">
            <span style={{ height: `${Math.max((Number(row.ventas || 0) / max) * 100, 4)}%` }} />
          </div>
          <small>{String(row.fecha).slice(-2)}</small>
        </div>
      ))}
    </div>
  )
}

function LineChart({ rows = [] }) {
  const max = Math.max(...rows.map((row) => Number(row.ventas || 0)), 1)
  const points = rows.map((row, index) => {
    const x = rows.length === 1 ? 0 : (index / (rows.length - 1)) * 100
    const y = 100 - (Number(row.ventas || 0) / max) * 92
    return `${x},${Math.max(y, 8)}`
  }).join(' ')
  return (
    <svg className="finance-line-chart" viewBox="0 0 100 100" preserveAspectRatio="none">
      <polyline points={points} fill="none" stroke="#c9a227" strokeWidth="1.8" />
    </svg>
  )
}

function Progress({ value, tone = 'green' }) {
  return (
    <span className="finance-progress">
      <span className={`finance-progress__bar finance-progress__bar--${tone}`} style={{ width: `${Math.min(Number(value || 0), 100)}%` }} />
    </span>
  )
}

export default function FinanzasPage() {
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const [activeTab, setActiveTab] = useState('Dashboard')
  const [showFilters, setShowFilters] = useState(false)
  const [filters, setFilters] = useState({
    fecha_inicio: firstDay,
    fecha_fin: todayText,
    mesero_id: '',
    cajero_id: '',
    forma_pago: '',
    estado: '',
    zona: '',
    categoria_menu: '',
    numero_orden: '',
  })

  const reporteQuery = useQuery({
    queryKey: ['reportes-financieros', filters],
    queryFn: () => getReporteFinanciero(filters),
    retry: 1,
  })

  const data = reporteQuery.data
  const maxPayment = useMemo(() => Math.max(...(data?.metodos_pago || []).map((item) => item.total), 1), [data])
  const ventaOrdenIds = useMemo(
    () => Array.from(new Set((data?.ventas || []).map((venta) => venta.orden).filter(Boolean))),
    [data?.ventas],
  )

  const facturasQuery = useQuery({
    queryKey: ['facturas-ventas', ventaOrdenIds],
    queryFn: () => getEstadosFacturaOrdenes(ventaOrdenIds),
    enabled: activeTab === 'Ventas' && ventaOrdenIds.length > 0,
    retry: 1,
  })

  const facturasPorOrden = facturasQuery.data || {}
  const gastosQuery = useQuery({ queryKey: ['gastos-operativos', filters.fecha_inicio, filters.fecha_fin], queryFn: () => getGastos({ fecha_inicio: filters.fecha_inicio, fecha_fin: filters.fecha_fin }), enabled: activeTab === 'Gastos' })
  const comprasQuery = useQuery({ queryKey: ['compras-proveedores'], queryFn: getCompras, enabled: activeTab === 'Compras' })
  const gastoMutation = useMutation({ mutationFn: createGasto, onSuccess: () => { queryClient.invalidateQueries({ queryKey: ['gastos-operativos'] }); queryClient.invalidateQueries({ queryKey: ['reportes-financieros'] }) } })
  const compraMutation = useMutation({ mutationFn: createCompra, onSuccess: () => queryClient.invalidateQueries({ queryKey: ['compras-proveedores'] }) })

  const updateFilter = (key, value) => setFilters((current) => ({ ...current, [key]: value }))
  const clearFilters = () => setFilters({
    fecha_inicio: firstDay,
    fecha_fin: todayText,
    mesero_id: '',
    cajero_id: '',
    forma_pago: '',
    estado: '',
    zona: '',
    categoria_menu: '',
    numero_orden: '',
  })

  return (
    <div className="finance-page">
      <header className="finance-header">
        <div className="finance-brand">
          <button type="button" onClick={() => navigate('/mesas')} aria-label="Volver">‹</button>
          <span className="finance-brand__mark">▥</span>
          <div>
            <strong>Magic Village POS</strong>
            <small>Modulo de Reportes Financieros</small>
          </div>
        </div>
        <div className="finance-actions">
          <button type="button" onClick={() => reporteQuery.refetch()}>Actualizar</button>
          <button type="button">Generar</button>
          <button type="button" onClick={() => window.print()}>PDF</button>
          <button type="button">Excel</button>
          <button type="button">Correo</button>
          <button type="button" onClick={() => window.print()}>Imprimir</button>
          <span>{data?.periodo?.inicio || filters.fecha_inicio} / {data?.periodo?.fin || filters.fecha_fin}</span>
        </div>
      </header>

      <nav className="finance-tabs">
        {tabs.map((tab) => (
          <button key={tab} type="button" className={activeTab === tab ? 'is-active' : ''} onClick={() => setActiveTab(tab)}>
            {tab}
          </button>
        ))}
        <button type="button" className="finance-filter-button" onClick={() => setShowFilters((value) => !value)}>
          Filtros
        </button>
      </nav>

      {showFilters ? (
        <section className="finance-filters">
          <label><span>Fecha Inicio</span><input type="date" value={filters.fecha_inicio} onChange={(event) => updateFilter('fecha_inicio', event.target.value)} /></label>
          <label><span>Fecha Fin</span><input type="date" value={filters.fecha_fin} onChange={(event) => updateFilter('fecha_fin', event.target.value)} /></label>
          <label><span>Forma de Pago</span><select value={filters.forma_pago} onChange={(event) => updateFilter('forma_pago', event.target.value)}><option value="">Todas</option><option value="efectivo">Efectivo</option><option value="tarjeta_debito">Tarjeta Debito</option><option value="tarjeta_credito">Tarjeta Credito</option><option value="nequi">Nequi</option><option value="daviplata">Daviplata</option><option value="pse">PSE</option><option value="cortesia">Cortesias</option></select></label>
          <label><span>Estado de Orden</span><select value={filters.estado} onChange={(event) => updateFilter('estado', event.target.value)}><option value="">Todos</option><option value="pagada">Pagada</option><option value="cancelada">Cancelada</option><option value="abierta">Abierta</option><option value="en_preparacion">En preparacion</option></select></label>
          <label><span>Categoria del Menu</span><select value={filters.categoria_menu} onChange={(event) => updateFilter('categoria_menu', event.target.value)}><option value="">Todas</option><option value="desayuno">Desayuno</option><option value="entrada">Entrada</option><option value="fuerte">Fuerte</option><option value="pizza">Pizza</option><option value="pasta">Pasta</option><option value="hamburguesa">Hamburguesa</option><option value="al_horno">Al horno</option><option value="bebida">Bebida</option><option value="licor">Licor</option><option value="postre">Postre</option><option value="otro">Otro</option></select></label>
          <label><span>Numero de Orden</span><input value={filters.numero_orden} onChange={(event) => updateFilter('numero_orden', event.target.value)} placeholder="Numero de Orden" /></label>
          <button type="button" onClick={() => reporteQuery.refetch()}>Buscar</button>
          <button type="button" onClick={clearFilters}>Limpiar</button>
        </section>
      ) : null}

      {reporteQuery.isLoading ? <div className="finance-state">Cargando reportes financieros...</div> : null}
      {reporteQuery.isError ? <div className="finance-state finance-state--error">{reporteQuery.error?.response?.data?.detail || 'No se pudo cargar el reporte.'}</div> : null}

      {data && activeTab === 'Dashboard' ? (
        <main className="finance-dashboard">
          <section className="finance-metrics">
            <MetricCard icon="$" label="Ventas Totales del Dia" value={money(data.metricas.ventas_dia, true)} change={data.metricas.variacion_ventas} />
            <MetricCard icon="↗" label="Ventas del Periodo" value={money(data.metricas.ventas_periodo, true)} change={data.metricas.variacion_ventas} />
            <MetricCard icon="▣" label="Ticket Promedio" value={money(data.metricas.ticket_promedio)} change={data.comparativo.variacion_ticket} />
            <MetricCard icon="▤" label="Numero de Ordenes" value={data.metricas.numero_ordenes} change={data.metricas.variacion_ordenes} />
          </section>
          {data.alertas_costeo?.length ? <div className="finance-integrity-alert"><b>Alerta de costeo:</b> {data.alertas_costeo.length} receta(s) supera(n) 100% de Food Cost. Revise unidades y costo unitario antes de tomar decisiones.</div> : null}

          <section className="finance-panel finance-chart-panel">
            <div className="finance-panel__title"><strong>Ventas por Dia</strong><span>Total vendido y cantidad de ordenes</span></div>
            <BarChart rows={data.ventas_por_dia} />
          </section>

          <section className="finance-panel">
            <div className="finance-panel__title"><strong>Evolucion de ventas</strong><span>Tendencia diaria del periodo</span></div>
            <LineChart rows={data.ventas_por_dia} />
          </section>

          <section className="finance-panel">
            <div className="finance-panel__title"><strong>Metodos de pago</strong><span>Distribucion del periodo</span></div>
            <div className="finance-payment-list">
              {data.metodos_pago.map((item) => (
                <div key={item.metodo}>
                  <span>{item.metodo}</span>
                  <Progress value={(item.total / maxPayment) * 100} />
                  <b>{item.porcentaje}%</b>
                </div>
              ))}
            </div>
          </section>

          <aside className="finance-summary">
            <strong>Resumen Financiero</strong>
            {Object.entries({
              'Ventas Brutas': data.resumen.ventas_brutas,
              'Total Descuentos': -data.resumen.total_descuentos,
              ...(Number(data.resumen.iva_recaudado) ? { 'IVA Recaudado': data.resumen.iva_recaudado } : {}),
              'Ventas Netas': data.resumen.ventas_netas,
              'Prom. por Mesa': data.resumen.promedio_mesa,
            }).map(([label, value]) => (
              <div key={label}><span>{label}</span><b className={Number(value) < 0 ? 'is-red' : ''}>{money(value, true)}</b></div>
            ))}
          </aside>
        </main>
      ) : null}

      {data && activeTab === 'Ventas' ? (
        <main className="finance-section">
          <div className="finance-section__top">
            <div>
              <h2>Tabla de Ventas</h2>
              <p>{data.ventas.length} registros encontrados{facturasQuery.isFetching ? ' · consultando facturas...' : ''}</p>
            </div>
          </div>
          <div className="finance-table-card">
            <table className="finance-table">
              <thead><tr><th>Orden</th><th>Fecha</th><th>Hora</th><th>Mesa</th><th>Mesero</th><th>Cajero</th><th>Subtotal</th><th>Descuento</th><th>IVA</th><th>Total</th><th>Pago</th><th>Estado</th><th>Factura</th></tr></thead>
              <tbody>
                {data.ventas.map((venta) => {
                  const factura = facturasPorOrden[venta.orden]
                  const pdfUrl = factura?.pdf_url
                  const numeroDocumento = factura?.numero_documento
                  return (
                    <tr key={venta.orden}>
                      <td>#{venta.orden}</td><td>{venta.fecha}</td><td>{venta.hora}</td><td>{venta.mesa}</td><td>{venta.mesero}</td><td>{venta.cajero}</td><td>{money(venta.subtotal)}</td><td className="is-red">{venta.descuento ? `-${money(venta.descuento)}` : '-'}</td><td>{money(venta.iva)}</td><td><b>{money(venta.total)}</b></td><td>{venta.pago}</td><td><span className={statusClass(venta.estado)}>{venta.estado}</span></td>
                      <td>
                        <div className="finance-invoice-cell">
                          <span className={invoiceStatusClass(factura?.estado)}>
                            {factura ? invoiceStatusLabel(factura.estado) : '...'}
                          </span>
                          {numeroDocumento ? <small>{numeroDocumento}</small> : null}
                          {pdfUrl ? (
                            <span className="finance-invoice-actions">
                              <a href={pdfUrl} target="_blank" rel="noreferrer">Ver PDF</a>
                              <a href={pdfUrl} target="_blank" rel="noreferrer" download={`factura-${numeroDocumento || venta.orden}.pdf`}>Descargar</a>
                            </span>
                          ) : null}
                        </div>
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        </main>
      ) : null}

      {data && activeTab === 'Rankings' ? (
        <main className="finance-section">
          <div className="finance-table-card">
            <h2>Ranking de Platos</h2>
            <table className="finance-table"><thead><tr><th>#</th><th>Plato</th><th>Vendidos</th><th>Ingresos</th><th>Costo</th><th>Food Cost %</th><th>Margen</th><th>Utilidad</th></tr></thead><tbody>{data.rankings.platos.map((item, index) => <tr key={item.receta_id}><td><span className="finance-rank">{index + 1}</span></td><td><b>{item.plato}</b></td><td>{item.vendidos}</td><td><b>{money(item.ingresos)}</b></td><td>{money(item.costo)}</td><td>{item.food_cost_pct}%</td><td>{item.margen_pct}%</td><td><b>{money(item.utilidad)}</b></td></tr>)}</tbody></table>
          </div>
          <div className="finance-split">
            <div className="finance-table-card"><h2>Ranking de Meseros</h2><table className="finance-table"><thead><tr><th>#</th><th>Nombre</th><th>Ordenes</th><th>Ventas</th><th>Ticket</th><th>Comision</th></tr></thead><tbody>{data.rankings.meseros.map((item, index) => <tr key={item.nombre}><td>{index + 1}</td><td><b>{item.nombre}</b></td><td>{item.ordenes}</td><td>{money(item.ventas, true)}</td><td>{money(item.ticket)}</td><td>{money(item.comision, true)}</td></tr>)}</tbody></table></div>
            <div className="finance-table-card"><h2>Ranking de Cajeros</h2><table className="finance-table"><thead><tr><th>#</th><th>Nombre</th><th>Pagos</th><th>Total Recaudado</th><th>Diferencia</th></tr></thead><tbody>{data.rankings.cajeros.map((item, index) => <tr key={item.nombre}><td>{index + 1}</td><td><b>{item.nombre}</b></td><td>{item.pagos}</td><td>{money(item.total, true)}</td><td>Cuadrado</td></tr>)}</tbody></table></div>
          </div>
        </main>
      ) : null}

      {data && activeTab === 'Categorias' ? (
        <main className="finance-category-grid">
          {data.categorias.map((item) => (
            <article key={item.categoria} className="finance-category-card">
              <div><strong>{item.categoria}</strong><span>{item.porcentaje}%</span></div>
              <b>{money(item.ventas, true)}</b>
              <small>{item.unidades} unidades vendidas</small>
              <Progress value={item.porcentaje} tone={item.food_cost_pct > 35 ? 'gold' : 'green'} />
            </article>
          ))}
          <section className="finance-table-card finance-category-table">
            <h2>Reporte de Metodos de Pago</h2>
            <table className="finance-table"><thead><tr><th>Metodo</th><th>Cantidad Pagos</th><th>Valor Total</th><th>Porcentaje</th><th>Distribucion</th></tr></thead><tbody>{data.metodos_pago.map((item) => <tr key={item.metodo}><td><b>{item.metodo}</b></td><td>{item.cantidad}</td><td><b>{money(item.total)}</b></td><td>{item.porcentaje}%</td><td><Progress value={item.porcentaje} /></td></tr>)}</tbody></table>
          </section>
        </main>
      ) : null}

      {data && activeTab === 'Rentabilidad' ? (
        <main className="finance-section">
          <section className="finance-profit-grid">
            <MetricCard icon="◉" label="Food Cost Prom." value={`${data.rentabilidad.food_cost_promedio}%`} change={-data.rentabilidad.food_cost_promedio} />
            <MetricCard icon="▧" label="Margen Bruto" value={`${data.rentabilidad.margen_bruto}%`} change={data.rentabilidad.margen_bruto} />
            <MetricCard icon="$" label="Utilidad Est." value={money(data.rentabilidad.utilidad_estimada, true)} change={data.rentabilidad.rentabilidad_pct} />
            <MetricCard icon="▥" label="Costo Ingredientes" value={money(data.rentabilidad.costo_ingredientes, true)} change={-data.rentabilidad.food_cost_promedio} />
            <MetricCard icon="▣" label="Ventas Netas" value={money(data.rentabilidad.ventas_netas, true)} change={data.metricas.variacion_ventas} />
          </section>
          <div className="finance-split">
            <section className="finance-panel"><div className="finance-panel__title"><strong>Food Cost por Categoria</strong><span>Costo estimado por BOM</span></div>{data.rentabilidad.por_categoria.map((item) => <div key={item.categoria} className="finance-profit-row"><span>{item.categoria}</span><Progress value={item.food_cost_pct} tone={item.food_cost_pct > 35 ? 'gold' : 'green'} /><b>{item.food_cost_pct}%</b></div>)}</section>
            <section className="finance-panel"><div className="finance-panel__title"><strong>Tendencia de Rentabilidad</strong><span>Margen del periodo</span></div><LineChart rows={data.ventas_por_dia} /></section>
          </div>
        </main>
      ) : null}

      {data && activeTab === 'Estado de Resultados' ? (
        <main className="finance-section"><section className="finance-table-card finance-pl-card"><h2>Estado de Resultados</h2><p>Resultado contable del período seleccionado.</p>{[
          ['Ventas Brutas', data.estado_resultados.ventas_brutas], ['(-) Descuentos', -data.estado_resultados.descuentos], ['Ventas Netas', data.estado_resultados.ventas_netas, 'total'], ['(-) Costo de Ventas (COGS)', -data.estado_resultados.costo_ventas], ['Utilidad Bruta', data.estado_resultados.utilidad_bruta, 'total'], ['(-) Gastos Operativos', -data.estado_resultados.gastos_operativos], ['Utilidad Neta', data.estado_resultados.utilidad_neta, 'net'],
        ].map(([label, value, type]) => <div key={label} className={`finance-pl-row ${type || ''}`}><span>{label}</span><b className={Number(value) < 0 ? 'is-red' : ''}>{money(value, true)}</b></div>)}<footer>Margen bruto: <b>{data.estado_resultados.margen_bruto}%</b> · Margen neto: <b>{data.estado_resultados.margen_neto}%</b></footer></section></main>
      ) : null}

      {activeTab === 'Gastos' ? (
        <main className="finance-section finance-entry-layout"><section className="finance-table-card"><h2>Gastos operativos</h2><form className="finance-entry-form" onSubmit={(event) => { event.preventDefault(); const f = new FormData(event.currentTarget); gastoMutation.mutate({ fecha: f.get('fecha'), categoria: f.get('categoria'), monto: Number(f.get('monto')), descripcion: f.get('descripcion'), es_recurrente: f.get('es_recurrente') === 'on', frecuencia: f.get('frecuencia') || null }); event.currentTarget.reset() }}><input name="fecha" type="date" defaultValue={todayText} required /><select name="categoria" defaultValue="Otros"><option>Arriendo</option><option>Servicios públicos</option><option>Nómina</option><option>Insumos de aseo</option><option>Mantenimiento</option><option>Marketing</option><option>Otros</option></select><input name="monto" type="number" min="1" placeholder="Monto" required /><input name="descripcion" placeholder="Descripción" /><label><input name="es_recurrente" type="checkbox" /> Recurrente</label><select name="frecuencia" defaultValue=""><option value="">Frecuencia</option><option value="mensual">Mensual</option><option value="semanal">Semanal</option></select><button disabled={gastoMutation.isPending}>Registrar gasto</button></form></section><section className="finance-table-card"><table className="finance-table"><thead><tr><th>Fecha</th><th>Categoría</th><th>Descripción</th><th>Tipo</th><th>Monto</th></tr></thead><tbody>{(gastosQuery.data || []).map((item) => <tr key={item.id}><td>{item.fecha}</td><td>{item.categoria}</td><td>{item.descripcion || '-'}</td><td>{item.es_recurrente ? `Recurrente ${item.frecuencia || ''}` : 'Puntual'}</td><td><b>{money(item.monto)}</b></td></tr>)}</tbody></table></section></main>
      ) : null}

      {activeTab === 'Compras' ? (
        <main className="finance-section finance-entry-layout"><section className="finance-table-card"><h2>Compras a proveedores</h2><form className="finance-entry-form" onSubmit={(event) => { event.preventDefault(); const f = new FormData(event.currentTarget); compraMutation.mutate({ fecha: f.get('fecha'), proveedor: f.get('proveedor'), descripcion: f.get('descripcion'), cantidad: Number(f.get('cantidad')), unidad: f.get('unidad'), costo_total: Number(f.get('costo_total')) }); event.currentTarget.reset() }}><input name="fecha" type="date" defaultValue={todayText} required /><input name="proveedor" placeholder="Proveedor" required /><input name="descripcion" placeholder="Insumo comprado" required /><input name="cantidad" type="number" min="0.001" step="any" placeholder="Cantidad" required /><select name="unidad"><option>unidad</option><option>g</option><option>kg</option><option>ml</option><option>l</option></select><input name="costo_total" type="number" min="1" placeholder="Costo real pagado" required /><button disabled={compraMutation.isPending}>Registrar compra</button></form></section><section className="finance-table-card"><table className="finance-table"><thead><tr><th>Fecha</th><th>Proveedor</th><th>Insumo</th><th>Cantidad</th><th>Costo real</th><th>Unitario</th></tr></thead><tbody>{(comprasQuery.data || []).map((item) => <tr key={item.id}><td>{item.fecha}</td><td>{item.proveedor}</td><td>{item.descripcion}</td><td>{item.cantidad} {item.unidad}</td><td><b>{money(item.costo_total)}</b></td><td>{money(item.costo_unitario)}</td></tr>)}</tbody></table></section></main>
      ) : null}

      {data && activeTab === 'Conciliacion' ? (
        <main className="finance-section"><section className="finance-table-card finance-reconciliation"><h2>Conciliación con caja</h2><p>Comparación acumulada entre las ventas del sistema y los cierres de caja registrados.</p><div><span>Ventas registradas</span><b>{money(data.conciliacion_caja.ventas_sistema, true)}</b></div><div><span>Total contado en cierres</span><b>{money(data.conciliacion_caja.total_contado, true)}</b></div><div className="total"><span>Diferencia acumulada</span><b className={Number(data.conciliacion_caja.diferencia) ? 'is-red' : ''}>{money(data.conciliacion_caja.diferencia, true)}</b></div></section></main>
      ) : null}

      {data && activeTab === 'Comparativo' ? (
        <main className="finance-section">
          <section className="finance-comparison-grid">
            <article><strong>Periodo Actual vs Anterior</strong><div><span>Actual<br /><b>{money(data.comparativo.actual.ventas_netas, true)}</b></span><span>Anterior<br /><b>{money(data.comparativo.anterior.ventas_netas, true)}</b></span></div><em>{pct(data.comparativo.variacion_ventas)}</em></article>
            <article><strong>Ordenes</strong><div><span>Actual<br /><b>{data.comparativo.actual.ordenes}</b></span><span>Anterior<br /><b>{data.comparativo.anterior.ordenes}</b></span></div><em>{pct(data.comparativo.variacion_ordenes)}</em></article>
            <article><strong>Ticket Promedio</strong><div><span>Actual<br /><b>{money(data.metricas.ticket_promedio)}</b></span><span>Anterior<br /><b>{money(data.comparativo.anterior.ventas_netas / Math.max(data.comparativo.anterior.ordenes, 1))}</b></span></div><em>{pct(data.comparativo.variacion_ticket)}</em></article>
          </section>
          <div className="finance-table-card">
            <h2>Comparativo Detallado</h2>
            <table className="finance-table"><thead><tr><th>Indicador</th><th>Actual</th><th>Anterior</th><th>Variacion</th></tr></thead><tbody><tr><td>Ventas Totales</td><td>{money(data.comparativo.actual.ventas_netas)}</td><td>{money(data.comparativo.anterior.ventas_netas)}</td><td>{pct(data.comparativo.variacion_ventas)}</td></tr><tr><td>N Ordenes</td><td>{data.comparativo.actual.ordenes}</td><td>{data.comparativo.anterior.ordenes}</td><td>{pct(data.comparativo.variacion_ordenes)}</td></tr><tr><td>Ticket Promedio</td><td>{money(data.metricas.ticket_promedio)}</td><td>{money(data.comparativo.anterior.ventas_netas / Math.max(data.comparativo.anterior.ordenes, 1))}</td><td>{pct(data.comparativo.variacion_ticket)}</td></tr><tr><td>Food Cost</td><td>{data.rentabilidad.food_cost_promedio}%</td><td>-</td><td>-</td></tr></tbody></table>
          </div>
        </main>
      ) : null}
    </div>
  )
}
