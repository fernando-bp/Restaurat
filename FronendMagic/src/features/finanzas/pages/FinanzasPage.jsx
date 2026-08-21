import { useMemo, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import {
  createCompra,
  createGasto,
  getCompras,
  getEstadosFacturaOrdenes,
  getGastos,
  getReporteFinanciero,
} from '../services/finanzasService'

const TABS = ['Resumen', 'P&G', 'IVA', 'Libro de Ventas', 'Costos', 'Gastos', 'Compras', 'Conciliación', 'Comparativo']

const today = new Date()
const firstDay = new Date(today.getFullYear(), today.getMonth(), 1).toISOString().slice(0, 10)
const todayText = today.toISOString().slice(0, 10)

// ── Formato contable colombiano ──────────────────────────────────────────────
function fmtAcc(value) {
  const num = Number(value || 0)
  const abs = Math.abs(num).toLocaleString('es-CO')
  if (num < 0) return `($ ${abs})`
  return `$ ${abs}`
}
function fmtDebit(value) {
  const num = Math.abs(Number(value || 0))
  return `($ ${num.toLocaleString('es-CO')})`
}
function fmtPct(value) {
  return `${Number(value || 0).toFixed(1)}%`
}
function varColor(v) {
  return Number(v) >= 0 ? '#16a34a' : '#dc2626'
}

// ── Componentes contables ────────────────────────────────────────────────────
function AccRow({ label, value, indent = false, subtotal = false, total = false, header = false, debit = false, pct, note }) {
  let cls = 'acct-row'
  if (header) cls += ' acct-row--header'
  else if (total) cls += ' acct-row--total'
  else if (subtotal) cls += ' acct-row--subtotal'
  else if (indent) cls += ' acct-row--indent'

  const displayValue = value !== undefined
    ? (debit ? fmtDebit(value) : fmtAcc(value))
    : null

  return (
    <div className={cls}>
      <span className="acct-label">{label}{note && <small style={{ marginLeft: 8, color: '#94a3b8', fontWeight: 400, fontSize: 11 }}>{note}</small>}</span>
      <span className="acct-num">
        {displayValue}
        {pct !== undefined && <span style={{ marginLeft: 8, color: '#52627a', fontSize: 12 }}>{fmtPct(pct)}</span>}
      </span>
    </div>
  )
}

function SectionTitle({ children }) {
  return (
    <div style={{ padding: '18px 0 6px', borderBottom: '2px solid #c9a227', marginBottom: 4 }}>
      <span style={{ fontSize: 11, fontWeight: 800, letterSpacing: 2, color: '#52627a', textTransform: 'uppercase' }}>
        {children}
      </span>
    </div>
  )
}

function KpiCard({ label, value, sub, color = '#14263d' }) {
  return (
    <div style={{
      background: '#fff',
      border: '1px solid #e5dfc7',
      borderRadius: 12,
      padding: '20px 24px',
      display: 'flex',
      flexDirection: 'column',
      gap: 4,
    }}>
      <span style={{ fontSize: 12, color: '#52627a', fontWeight: 600, textTransform: 'uppercase', letterSpacing: 1 }}>{label}</span>
      <span style={{ fontSize: 22, fontWeight: 900, color, fontVariantNumeric: 'tabular-nums' }}>{value}</span>
      {sub && <span style={{ fontSize: 12, color: '#94a3b8' }}>{sub}</span>}
    </div>
  )
}

function StatusBadge({ estado = '' }) {
  const n = estado.toLowerCase()
  if (n.includes('pag')) return <span style={{ background: '#dcfce7', color: '#166534', padding: '2px 8px', borderRadius: 6, fontSize: 11, fontWeight: 700 }}>Pagada</span>
  if (n.includes('cancel')) return <span style={{ background: '#fee2e2', color: '#991b1b', padding: '2px 8px', borderRadius: 6, fontSize: 11, fontWeight: 700 }}>Cancelada</span>
  return <span style={{ background: '#fef9c3', color: '#854d0e', padding: '2px 8px', borderRadius: 6, fontSize: 11, fontWeight: 700 }}>{estado}</span>
}

function InvoiceCell({ factura }) {
  if (!factura) return <span style={{ color: '#94a3b8', fontSize: 12 }}>—</span>
  const { estado = '', numero_documento, pdf_url } = factura
  const n = estado.toLowerCase()
  const isOk = ['validated', 'validada', 'aceptada'].includes(n)
  const isError = ['rejected', 'rechazada', 'error'].includes(n)
  const color = isOk ? '#16a34a' : isError ? '#dc2626' : '#d97706'
  const label = isOk ? 'Emitida' : isError ? 'Rechazada' : 'Pendiente'
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 3 }}>
      <span style={{ color, fontSize: 11, fontWeight: 700 }}>{label}</span>
      {numero_documento && <span style={{ fontSize: 11, color: '#52627a' }}>{numero_documento}</span>}
      {pdf_url && <a href={pdf_url} target="_blank" rel="noreferrer" style={{ fontSize: 11, color: '#1d4ed8', textDecoration: 'underline' }}>Ver PDF</a>}
    </div>
  )
}

// ── Page ─────────────────────────────────────────────────────────────────────
export default function FinanzasPage() {
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const [activeTab, setActiveTab] = useState('Resumen')
  const [filters, setFilters] = useState({ fecha_inicio: firstDay, fecha_fin: todayText, forma_pago: '', estado: '', categoria_menu: '', numero_orden: '' })
  const [showFilters, setShowFilters] = useState(false)

  const reporteQuery = useQuery({ queryKey: ['reportes-financieros', filters], queryFn: () => getReporteFinanciero(filters), retry: 1 })
  const gastosQuery = useQuery({ queryKey: ['gastos-operativos', filters.fecha_inicio, filters.fecha_fin], queryFn: () => getGastos({ fecha_inicio: filters.fecha_inicio, fecha_fin: filters.fecha_fin }) })
  const comprasQuery = useQuery({ queryKey: ['compras-proveedores'], queryFn: getCompras })

  const gastoMutation = useMutation({
    mutationFn: createGasto,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['gastos-operativos'] })
      queryClient.invalidateQueries({ queryKey: ['reportes-financieros'] })
    },
  })
  const compraMutation = useMutation({
    mutationFn: createCompra,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['compras-proveedores'] }),
  })

  const data = reporteQuery.data
  const gastos = gastosQuery.data || []
  const compras = comprasQuery.data || []

  const ventaOrdenIds = useMemo(
    () => Array.from(new Set((data?.ventas || []).map((v) => v.orden).filter(Boolean))),
    [data?.ventas],
  )
  const facturasQuery = useQuery({
    queryKey: ['facturas-ventas', ventaOrdenIds],
    queryFn: () => getEstadosFacturaOrdenes(ventaOrdenIds),
    enabled: activeTab === 'Libro de Ventas' && ventaOrdenIds.length > 0,
    retry: 1,
  })
  const facturasPorOrden = facturasQuery.data || {}

  // ── Derivados contables ────────────────────────────────────────────────────
  const er = data?.estado_resultados || {}
  const resumen = data?.resumen || {}
  const metricas = data?.metricas || {}
  const comparativo = data?.comparativo || {}
  const conciliacion = data?.conciliacion_caja || {}

  const ingresosNetosOp = (resumen.ventas_brutas || 0) - (resumen.total_descuentos || 0)
  const utilidadOperacional = ingresosNetosOp - (er.costo_ventas || 0) - (er.gastos_operativos || 0)
  const margenOperacional = ingresosNetosOp > 0 ? (utilidadOperacional / ingresosNetosOp * 100) : 0

  // Gastos agrupados por categoría
  const gastosPorCategoria = useMemo(() => {
    const map = {}
    gastos.forEach((g) => {
      const cat = g.categoria || 'Otros'
      map[cat] = (map[cat] || 0) + Number(g.monto || 0)
    })
    return Object.entries(map).sort((a, b) => b[1] - a[1])
  }, [gastos])

  // IVA descontable estimado en compras (19% IVA general, aproximación)
  const totalComprasPeriodo = useMemo(() => {
    return compras
      .filter((c) => c.fecha >= filters.fecha_inicio && c.fecha <= filters.fecha_fin)
      .reduce((s, c) => s + Number(c.costo_total || 0), 0)
  }, [compras, filters.fecha_inicio, filters.fecha_fin])
  const ivaDescontableEstimado = totalComprasPeriodo * 0.08
  const ivaNetoCargo = (resumen.iva_recaudado || 0) - ivaDescontableEstimado

  function printPG() {
    const win = window.open('', '_blank', 'width=800,height=900')
    const periodo = `${filters.fecha_inicio} al ${filters.fecha_fin}`
    const fmt = (v) => {
      const n = Number(v || 0)
      const a = Math.abs(n).toLocaleString('es-CO')
      return n < 0 ? `($ ${a})` : `$ ${a}`
    }
    const row = (label, val, indent = false) =>
      `<tr><td style="padding:8px ${indent ? '24px' : '4px'};color:#1f2d3d">${label}</td><td style="padding:8px 4px;text-align:right;font-variant-numeric:tabular-nums;font-family:monospace">${fmt(val)}</td></tr>`
    const sep = (double = false) =>
      `<tr><td colspan="2" style="border-top:${double ? '3px double' : '2px solid'} #c9a227;padding:0"></td></tr>`
    win.document.write(`
      <html><head><title>P&G</title>
      <style>body{font-family:Georgia,serif;padding:40px;color:#14263d}h2{margin-bottom:4px}p{color:#52627a;margin-top:0}table{width:100%;border-collapse:collapse}thead th{font-size:10px;letter-spacing:2px;text-transform:uppercase;color:#52627a;padding:6px 4px;border-bottom:2px solid #c9a227}</style>
      </head><body>
      <h2>ESTADO DE PÉRDIDAS Y GANANCIAS</h2>
      <p>Magic Village · Período: ${periodo}</p>
      <table><tbody>
        <tr><td colspan="2" style="padding:12px 4px 4px;font-weight:800;font-size:11px;letter-spacing:2px;color:#52627a">INGRESOS OPERACIONALES</td></tr>
        ${row('Ventas brutas (excluye IVA)', resumen.ventas_brutas, true)}
        ${row('(-) Descuentos y cortesías', -(resumen.total_descuentos || 0), true)}
        ${sep()}
        ${row('INGRESOS NETOS OPERACIONALES', ingresosNetosOp)}
        ${sep()}
        <tr><td colspan="2" style="padding:12px 4px 4px;font-weight:800;font-size:11px;letter-spacing:2px;color:#52627a">COSTO DE VENTAS (CMV)</td></tr>
        ${row('(-) Costo de ingredientes consumidos', -(er.costo_ventas || 0), true)}
        ${sep()}
        ${row('UTILIDAD BRUTA', er.utilidad_bruta)}
        <tr><td colspan="2" style="padding:4px;font-size:11px;color:#52627a">Margen bruto: ${fmtPct(er.margen_bruto)}</td></tr>
        ${sep()}
        <tr><td colspan="2" style="padding:12px 4px 4px;font-weight:800;font-size:11px;letter-spacing:2px;color:#52627a">GASTOS OPERACIONALES</td></tr>
        ${gastosPorCategoria.map(([cat, monto]) => row(cat, -monto, true)).join('')}
        ${sep()}
        ${row('TOTAL GASTOS OPERACIONALES', -(er.gastos_operativos || 0))}
        ${sep()}
        ${row('UTILIDAD OPERACIONAL (EBIT)', utilidadOperacional)}
        <tr><td colspan="2" style="padding:4px;font-size:11px;color:#52627a">Margen operacional: ${fmtPct(margenOperacional)}</td></tr>
        ${sep(true)}
        ${row('UTILIDAD NETA DEL PERÍODO', er.utilidad_neta)}
        <tr><td colspan="2" style="padding:4px;font-size:11px;color:#52627a">Margen neto: ${fmtPct(er.margen_neto)}</td></tr>
        ${sep(true)}
      </tbody></table>
      <p style="margin-top:32px;font-size:11px;color:#94a3b8">Generado el ${new Date().toLocaleDateString('es-CO')} · Magic Village POS</p>
      </body></html>
    `)
    win.document.close()
    win.print()
  }

  function updateFilter(key, value) {
    setFilters((prev) => ({ ...prev, [key]: value }))
  }

  return (
    <div className="acct-page">
      {/* Header */}
      <header className="finance-header">
        <div className="finance-brand">
          <button type="button" onClick={() => navigate('/mesas')} aria-label="Volver">‹</button>
          <span className="finance-brand__mark">▥</span>
          <div>
            <strong>Magic Village POS</strong>
            <small>Módulo Financiero · {filters.fecha_inicio} / {filters.fecha_fin}</small>
          </div>
        </div>
        <div className="finance-actions">
          <button type="button" onClick={() => reporteQuery.refetch()}>↻ Actualizar</button>
          <button type="button" onClick={() => setShowFilters((v) => !v)}>Filtros</button>
          <button type="button" onClick={window.print}>Imprimir</button>
        </div>
      </header>

      {/* Filters */}
      {showFilters && (
        <section className="finance-filters">
          <label><span>Fecha Inicio</span><input type="date" value={filters.fecha_inicio} onChange={(e) => updateFilter('fecha_inicio', e.target.value)} /></label>
          <label><span>Fecha Fin</span><input type="date" value={filters.fecha_fin} onChange={(e) => updateFilter('fecha_fin', e.target.value)} /></label>
          <label><span>Forma de Pago</span>
            <select value={filters.forma_pago} onChange={(e) => updateFilter('forma_pago', e.target.value)}>
              <option value="">Todas</option><option value="efectivo">Efectivo</option><option value="tarjeta_debito">Tarjeta Débito</option><option value="tarjeta_credito">Tarjeta Crédito</option><option value="nequi">Nequi</option><option value="daviplata">Daviplata</option><option value="pse">PSE</option><option value="cortesia">Cortesía</option>
            </select>
          </label>
          <label><span>Estado Orden</span>
            <select value={filters.estado} onChange={(e) => updateFilter('estado', e.target.value)}>
              <option value="">Todos</option><option value="pagada">Pagada</option><option value="cancelada">Cancelada</option><option value="abierta">Abierta</option>
            </select>
          </label>
          <label><span>Categoría</span>
            <select value={filters.categoria_menu} onChange={(e) => updateFilter('categoria_menu', e.target.value)}>
              <option value="">Todas</option><option value="desayuno">Desayuno</option><option value="entrada">Entrada</option><option value="fuerte">Fuerte</option><option value="pizza">Pizza</option><option value="pasta">Pasta</option><option value="hamburguesa">Hamburguesa</option><option value="bebida">Bebida</option><option value="postre">Postre</option>
            </select>
          </label>
          <label><span>Nº Orden</span><input value={filters.numero_orden} onChange={(e) => updateFilter('numero_orden', e.target.value)} placeholder="Ej: 45" /></label>
          <button type="button" onClick={() => reporteQuery.refetch()}>Buscar</button>
          <button type="button" onClick={() => setFilters({ fecha_inicio: firstDay, fecha_fin: todayText, forma_pago: '', estado: '', categoria_menu: '', numero_orden: '' })}>Limpiar</button>
        </section>
      )}

      {/* Tabs */}
      <nav className="finance-tabs">
        {TABS.map((tab) => (
          <button key={tab} type="button" className={activeTab === tab ? 'is-active' : ''} onClick={() => setActiveTab(tab)}>
            {tab}
          </button>
        ))}
      </nav>

      {reporteQuery.isLoading && <div className="finance-state">Cargando información financiera…</div>}
      {reporteQuery.isError && <div className="finance-state finance-state--error">{reporteQuery.error?.response?.data?.detail || 'No se pudo cargar el reporte.'}</div>}

      <main className="acct-main">

        {/* ── RESUMEN ──────────────────────────────────────────────────────── */}
        {data && activeTab === 'Resumen' && (
          <div>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))', gap: 16, marginBottom: 32 }}>
              <KpiCard label="Ventas del día" value={fmtAcc(metricas.ventas_dia)} sub="Neto incluyendo IVA" />
              <KpiCard label="Ventas del período" value={fmtAcc(metricas.ventas_periodo)} sub={`${metricas.numero_ordenes} órdenes`} />
              <KpiCard label="Ticket promedio" value={fmtAcc(metricas.ticket_promedio)} />
              <KpiCard label="IVA recaudado" value={fmtAcc(resumen.iva_recaudado)} sub="8% sobre base gravable" color="#b45309" />
              <KpiCard label="Utilidad bruta est." value={fmtAcc(er.utilidad_bruta)} sub={`Margen: ${fmtPct(er.margen_bruto)}`} color={Number(er.utilidad_bruta) >= 0 ? '#16a34a' : '#dc2626'} />
              <KpiCard label="Utilidad neta est." value={fmtAcc(er.utilidad_neta)} sub={`Margen: ${fmtPct(er.margen_neto)}`} color={Number(er.utilidad_neta) >= 0 ? '#16a34a' : '#dc2626'} />
            </div>

            {data.alertas_costeo?.length > 0 && (
              <div className="finance-integrity-alert" style={{ marginBottom: 24 }}>
                ⚠️ <b>Alerta de costeo:</b> {data.alertas_costeo.length} receta(s) con Food Cost &gt; 100%. Revise costos de ingredientes.
              </div>
            )}

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 24 }}>
              <div className="acct-card">
                <SectionTitle>Resumen ejecutivo del período</SectionTitle>
                <AccRow label="Ventas brutas (sin IVA)" value={resumen.ventas_brutas} />
                <AccRow label="(-) Descuentos concedidos" value={resumen.total_descuentos} debit indent />
                <AccRow label="Ingresos netos operacionales" value={ingresosNetosOp} subtotal />
                <AccRow label="(-) Costo de ventas (CMV)" value={er.costo_ventas} debit indent />
                <AccRow label="Utilidad bruta" value={er.utilidad_bruta} subtotal />
                <AccRow label="(-) Gastos operativos" value={er.gastos_operativos} debit indent />
                <AccRow label="Utilidad neta del período" value={er.utilidad_neta} total />
              </div>
              <div className="acct-card">
                <SectionTitle>Recaudo por método de pago</SectionTitle>
                {(data.metodos_pago || []).map((item) => (
                  <div key={item.metodo} style={{ display: 'flex', justifyContent: 'space-between', padding: '10px 4px', borderBottom: '1px solid #eee7d9' }}>
                    <span style={{ color: '#1f2d3d', fontSize: 14 }}>{item.metodo}</span>
                    <span style={{ display: 'flex', gap: 12, alignItems: 'center' }}>
                      <span style={{ color: '#52627a', fontSize: 12 }}>{item.porcentaje}%</span>
                      <b style={{ fontVariantNumeric: 'tabular-nums', minWidth: 120, textAlign: 'right' }}>{fmtAcc(item.total)}</b>
                    </span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}

        {/* ── P&G ──────────────────────────────────────────────────────────── */}
        {data && activeTab === 'P&G' && (
          <div>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20 }}>
              <div>
                <h2 style={{ margin: 0, color: '#14263d', fontSize: 18, fontWeight: 800 }}>Estado de Pérdidas y Ganancias</h2>
                <p style={{ margin: '4px 0 0', color: '#52627a', fontSize: 13 }}>Período: {filters.fecha_inicio} al {filters.fecha_fin}</p>
              </div>
              <button type="button" onClick={printPG} style={{ background: '#14263d', color: '#f8e6a3', border: 'none', borderRadius: 8, padding: '8px 18px', fontWeight: 700, cursor: 'pointer', fontSize: 13 }}>
                🖨 Imprimir P&G
              </button>
            </div>

            <div className="acct-card" style={{ maxWidth: 720 }}>
              <AccRow label="INGRESOS OPERACIONALES" header />
              <AccRow label="Ventas brutas (excluye IVA)" value={resumen.ventas_brutas} indent />
              <AccRow label="(-) Descuentos y cortesías" value={resumen.total_descuentos} debit indent />
              <AccRow label="INGRESOS NETOS OPERACIONALES" value={ingresosNetosOp} subtotal />

              <AccRow label="COSTO DE VENTAS (CMV)" header />
              <AccRow label="Costo de ingredientes consumidos" value={er.costo_ventas} debit indent />
              <AccRow label="UTILIDAD BRUTA" value={er.utilidad_bruta} subtotal pct={er.margen_bruto} />

              <AccRow label="GASTOS OPERACIONALES DE ADMINISTRACIÓN" header />
              {gastosPorCategoria.length === 0 && (
                <AccRow label="Sin gastos registrados en el período" indent />
              )}
              {gastosPorCategoria.map(([cat, monto]) => (
                <AccRow key={cat} label={cat} value={monto} debit indent />
              ))}
              <AccRow label="TOTAL GASTOS OPERACIONALES" value={er.gastos_operativos} debit subtotal />

              <AccRow label="UTILIDAD OPERACIONAL (EBIT)" value={utilidadOperacional} subtotal pct={margenOperacional} />

              <div style={{ padding: '4px 0 12px', borderTop: '1px solid #eee7d9' }} />
              <AccRow label="UTILIDAD NETA DEL PERÍODO" value={er.utilidad_neta} total pct={er.margen_neto} />

              <div style={{ padding: '16px 4px 4px', color: '#52627a', fontSize: 12 }}>
                IVA recaudado (no es ingreso, es pasivo ante la DIAN): <b>{fmtAcc(resumen.iva_recaudado)}</b>
              </div>
            </div>
          </div>
        )}

        {/* ── IVA ──────────────────────────────────────────────────────────── */}
        {data && activeTab === 'IVA' && (
          <div>
            <h2 style={{ margin: '0 0 4px', color: '#14263d', fontSize: 18, fontWeight: 800 }}>Declaración de IVA</h2>
            <p style={{ margin: '0 0 24px', color: '#52627a', fontSize: 13 }}>Período: {filters.fecha_inicio} al {filters.fecha_fin} · Tarifa 8% (Restaurantes - Art. 468-1 E.T.)</p>

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 24 }}>
              <div className="acct-card">
                <SectionTitle>IVA Generado (Ventas)</SectionTitle>
                <AccRow label="Ingresos netos operacionales (base gravable)" value={ingresosNetosOp} />
                <AccRow label="Tarifa IVA aplicable" />
                <div className="acct-row acct-row--indent">
                  <span className="acct-label">Tarifa aplicable</span>
                  <span className="acct-num" style={{ color: '#b45309' }}>8%</span>
                </div>
                <AccRow label="IVA GENERADO EN VENTAS" value={resumen.iva_recaudado} subtotal />

                <div style={{ height: 20 }} />
                <SectionTitle>IVA Descontable (Compras)</SectionTitle>
                <AccRow label="Total compras a proveedores en período" value={totalComprasPeriodo} />
                <AccRow label="IVA estimado en compras (8%)" value={ivaDescontableEstimado} note="*aproximación" indent />
                <div style={{ padding: '8px 4px', fontSize: 11, color: '#94a3b8', borderTop: '1px solid #eee7d9' }}>
                  * El IVA descontable exacto depende de las facturas físicas de sus proveedores. Valide con su contador.
                </div>

                <div style={{ height: 20 }} />
                <AccRow label="IVA NETO A CARGO (estimado)" value={ivaNetoCargo} total />
                <div style={{ padding: '4px 4px', fontSize: 12, color: Number(ivaNetoCargo) >= 0 ? '#dc2626' : '#16a34a' }}>
                  {Number(ivaNetoCargo) >= 0 ? '⚠ Saldo a pagar a la DIAN' : '✓ Saldo a favor'}
                </div>
              </div>

              <div className="acct-card">
                <SectionTitle>Detalle diario de IVA generado</SectionTitle>
                <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
                  <thead>
                    <tr>
                      <th style={{ textAlign: 'left', padding: '8px 4px', color: '#52627a', fontSize: 11, fontWeight: 700, borderBottom: '2px solid #c9a227' }}>Fecha</th>
                      <th style={{ textAlign: 'right', padding: '8px 4px', color: '#52627a', fontSize: 11, fontWeight: 700, borderBottom: '2px solid #c9a227' }}>Ventas (sin IVA)</th>
                      <th style={{ textAlign: 'right', padding: '8px 4px', color: '#52627a', fontSize: 11, fontWeight: 700, borderBottom: '2px solid #c9a227' }}>IVA 8%</th>
                    </tr>
                  </thead>
                  <tbody>
                    {(data.ventas_por_dia || []).map((row) => {
                      const ventasDia = Number(row.ventas || 0)
                      const baseDia = ventasDia / 1.08
                      const ivaDia = ventasDia - baseDia
                      return (
                        <tr key={row.fecha} style={{ borderBottom: '1px solid #eee7d9' }}>
                          <td style={{ padding: '8px 4px', color: '#1f2d3d' }}>{row.fecha}</td>
                          <td style={{ padding: '8px 4px', textAlign: 'right', fontVariantNumeric: 'tabular-nums' }}>{fmtAcc(baseDia)}</td>
                          <td style={{ padding: '8px 4px', textAlign: 'right', fontVariantNumeric: 'tabular-nums', color: '#b45309' }}>{fmtAcc(ivaDia)}</td>
                        </tr>
                      )
                    })}
                  </tbody>
                  <tfoot>
                    <tr style={{ borderTop: '2px solid #c9a227', fontWeight: 900 }}>
                      <td style={{ padding: '10px 4px' }}>TOTAL</td>
                      <td style={{ padding: '10px 4px', textAlign: 'right', fontVariantNumeric: 'tabular-nums' }}>{fmtAcc(ingresosNetosOp)}</td>
                      <td style={{ padding: '10px 4px', textAlign: 'right', fontVariantNumeric: 'tabular-nums', color: '#b45309' }}>{fmtAcc(resumen.iva_recaudado)}</td>
                    </tr>
                  </tfoot>
                </table>
              </div>
            </div>
          </div>
        )}

        {/* ── LIBRO DE VENTAS ───────────────────────────────────────────────── */}
        {data && activeTab === 'Libro de Ventas' && (
          <div>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
              <div>
                <h2 style={{ margin: 0, color: '#14263d', fontSize: 18, fontWeight: 800 }}>Libro de Ventas</h2>
                <p style={{ margin: '4px 0 0', color: '#52627a', fontSize: 13 }}>{data.ventas.length} registros{facturasQuery.isFetching ? ' · consultando facturas…' : ''}</p>
              </div>
            </div>
            <div style={{ overflowX: 'auto' }}>
              <table className="finance-table" style={{ fontSize: 13 }}>
                <thead>
                  <tr>
                    <th>Orden</th><th>Fecha</th><th>Hora</th><th>Mesa</th><th>Mesero</th><th>Cajero</th>
                    <th style={{ textAlign: 'right' }}>Base (sin IVA)</th>
                    <th style={{ textAlign: 'right' }}>Descuento</th>
                    <th style={{ textAlign: 'right' }}>IVA 8%</th>
                    <th style={{ textAlign: 'right' }}>Total</th>
                    <th>Pago</th><th>Estado</th><th>Factura DIAN</th>
                  </tr>
                </thead>
                <tbody>
                  {data.ventas.map((venta) => (
                    <tr key={venta.orden}>
                      <td>#{venta.orden}</td>
                      <td>{venta.fecha}</td>
                      <td style={{ color: '#52627a' }}>{String(venta.hora).slice(0, 5)}</td>
                      <td>{venta.mesa}</td>
                      <td>{venta.mesero}</td>
                      <td style={{ color: '#52627a' }}>{venta.cajero}</td>
                      <td style={{ textAlign: 'right', fontVariantNumeric: 'tabular-nums' }}>{fmtAcc(venta.subtotal)}</td>
                      <td style={{ textAlign: 'right', color: '#dc2626', fontVariantNumeric: 'tabular-nums' }}>{venta.descuento ? fmtDebit(venta.descuento) : '—'}</td>
                      <td style={{ textAlign: 'right', color: '#b45309', fontVariantNumeric: 'tabular-nums' }}>{fmtAcc(venta.iva)}</td>
                      <td style={{ textAlign: 'right', fontWeight: 700, fontVariantNumeric: 'tabular-nums' }}>{fmtAcc(venta.total)}</td>
                      <td style={{ color: '#52627a', fontSize: 12 }}>{venta.pago}</td>
                      <td><StatusBadge estado={venta.estado} /></td>
                      <td><InvoiceCell factura={facturasPorOrden[venta.orden]} /></td>
                    </tr>
                  ))}
                </tbody>
                <tfoot>
                  <tr style={{ borderTop: '2px solid #c9a227', fontWeight: 900 }}>
                    <td colSpan={6} style={{ padding: '10px 8px' }}>TOTALES</td>
                    <td style={{ textAlign: 'right', padding: '10px 8px', fontVariantNumeric: 'tabular-nums' }}>{fmtAcc(resumen.ventas_brutas)}</td>
                    <td style={{ textAlign: 'right', padding: '10px 8px', color: '#dc2626', fontVariantNumeric: 'tabular-nums' }}>{fmtDebit(resumen.total_descuentos)}</td>
                    <td style={{ textAlign: 'right', padding: '10px 8px', color: '#b45309', fontVariantNumeric: 'tabular-nums' }}>{fmtAcc(resumen.iva_recaudado)}</td>
                    <td style={{ textAlign: 'right', padding: '10px 8px', fontVariantNumeric: 'tabular-nums' }}>{fmtAcc(resumen.ventas_netas)}</td>
                    <td colSpan={3} />
                  </tr>
                </tfoot>
              </table>
            </div>
          </div>
        )}

        {/* ── COSTOS ───────────────────────────────────────────────────────── */}
        {data && activeTab === 'Costos' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 28 }}>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))', gap: 16 }}>
              <KpiCard label="Food Cost Promedio" value={fmtPct(data.rentabilidad.food_cost_promedio)} sub="Costo / Ventas netas" color="#b45309" />
              <KpiCard label="Margen Bruto" value={fmtPct(data.rentabilidad.margen_bruto)} color="#16a34a" />
              <KpiCard label="Costo de Ingredientes" value={fmtAcc(data.rentabilidad.costo_ingredientes)} sub="Estimado BOM" />
              <KpiCard label="Utilidad Estimada" value={fmtAcc(data.rentabilidad.utilidad_estimada)} color={Number(data.rentabilidad.utilidad_estimada) >= 0 ? '#16a34a' : '#dc2626'} />
            </div>

            <div className="acct-card">
              <SectionTitle>Food Cost por Categoría</SectionTitle>
              <table className="finance-table" style={{ fontSize: 13 }}>
                <thead><tr><th>Categoría</th><th style={{ textAlign: 'right' }}>Ventas</th><th style={{ textAlign: 'right' }}>Costo</th><th style={{ textAlign: 'right' }}>Food Cost %</th><th style={{ textAlign: 'right' }}>Utilidad</th></tr></thead>
                <tbody>
                  {data.categorias.map((item) => (
                    <tr key={item.categoria} style={{ borderBottom: '1px solid #eee7d9' }}>
                      <td style={{ padding: '10px 8px' }}><b>{item.categoria}</b></td>
                      <td style={{ textAlign: 'right', padding: '10px 8px', fontVariantNumeric: 'tabular-nums' }}>{fmtAcc(item.ventas)}</td>
                      <td style={{ textAlign: 'right', padding: '10px 8px', color: '#dc2626', fontVariantNumeric: 'tabular-nums' }}>{fmtDebit(item.costo)}</td>
                      <td style={{ textAlign: 'right', padding: '10px 8px', color: item.food_cost_pct > 35 ? '#dc2626' : '#16a34a', fontWeight: 700 }}>{fmtPct(item.food_cost_pct)}</td>
                      <td style={{ textAlign: 'right', padding: '10px 8px', fontVariantNumeric: 'tabular-nums', fontWeight: 700 }}>{fmtAcc(item.ventas - item.costo)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            <div className="acct-card">
              <SectionTitle>Ranking de Platos — Top 15</SectionTitle>
              <table className="finance-table" style={{ fontSize: 13 }}>
                <thead><tr><th>#</th><th>Plato</th><th>Categoría</th><th style={{ textAlign: 'right' }}>Vendidos</th><th style={{ textAlign: 'right' }}>Ingresos</th><th style={{ textAlign: 'right' }}>Costo</th><th style={{ textAlign: 'right' }}>Food Cost %</th><th style={{ textAlign: 'right' }}>Utilidad</th></tr></thead>
                <tbody>
                  {data.rankings.platos.map((item, i) => (
                    <tr key={item.receta_id} style={{ borderBottom: '1px solid #eee7d9' }}>
                      <td style={{ padding: '10px 8px', color: '#52627a' }}>{i + 1}</td>
                      <td style={{ padding: '10px 8px' }}><b>{item.plato}</b></td>
                      <td style={{ padding: '10px 8px', color: '#52627a', fontSize: 12 }}>{item.categoria}</td>
                      <td style={{ textAlign: 'right', padding: '10px 8px' }}>{item.vendidos}</td>
                      <td style={{ textAlign: 'right', padding: '10px 8px', fontVariantNumeric: 'tabular-nums' }}>{fmtAcc(item.ingresos)}</td>
                      <td style={{ textAlign: 'right', padding: '10px 8px', color: '#dc2626', fontVariantNumeric: 'tabular-nums' }}>{fmtDebit(item.costo)}</td>
                      <td style={{ textAlign: 'right', padding: '10px 8px', color: item.food_cost_pct > 35 ? '#dc2626' : '#16a34a', fontWeight: 700 }}>{fmtPct(item.food_cost_pct)}</td>
                      <td style={{ textAlign: 'right', padding: '10px 8px', fontVariantNumeric: 'tabular-nums', fontWeight: 700 }}>{fmtAcc(item.utilidad)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* ── GASTOS ───────────────────────────────────────────────────────── */}
        {activeTab === 'Gastos' && (
          <div style={{ display: 'grid', gridTemplateColumns: 'minmax(280px, 0.85fr) minmax(0, 1.8fr)', gap: 24, alignItems: 'start' }}>
            <div className="acct-card">
              <h3 style={{ margin: '0 0 16px', color: '#14263d', fontSize: 15, fontWeight: 800 }}>Registrar Gasto Operativo</h3>
              <form className="finance-entry-form" onSubmit={(e) => {
                e.preventDefault()
                const f = new FormData(e.currentTarget)
                gastoMutation.mutate({ fecha: f.get('fecha'), categoria: f.get('categoria'), monto: Number(f.get('monto')), descripcion: f.get('descripcion'), es_recurrente: f.get('es_recurrente') === 'on', frecuencia: f.get('frecuencia') || null })
                e.currentTarget.reset()
              }}>
                <input name="fecha" type="date" defaultValue={todayText} required />
                <select name="categoria" defaultValue="Otros">
                  <option>Arriendo</option><option>Servicios públicos</option><option>Nómina</option><option>Insumos de aseo</option><option>Mantenimiento</option><option>Marketing</option><option>Otros</option>
                </select>
                <input name="monto" type="number" min="1" placeholder="Monto ($)" required />
                <input name="descripcion" placeholder="Descripción" />
                <label style={{ display: 'flex', alignItems: 'center', gap: 8 }}><input name="es_recurrente" type="checkbox" /> Gasto recurrente</label>
                <select name="frecuencia" defaultValue=""><option value="">Frecuencia (si es recurrente)</option><option value="mensual">Mensual</option><option value="semanal">Semanal</option></select>
                <button disabled={gastoMutation.isPending}>{gastoMutation.isPending ? 'Registrando…' : 'Registrar gasto'}</button>
              </form>
            </div>
            <div className="acct-card">
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
                <h3 style={{ margin: 0, color: '#14263d', fontSize: 15, fontWeight: 800 }}>Gastos Operativos del Período</h3>
                <b style={{ fontVariantNumeric: 'tabular-nums' }}>{fmtDebit(gastos.reduce((s, g) => s + Number(g.monto || 0), 0))}</b>
              </div>
              <table className="finance-table" style={{ fontSize: 13 }}>
                <thead><tr><th>Fecha</th><th>Categoría</th><th>Descripción</th><th>Tipo</th><th style={{ textAlign: 'right' }}>Monto</th></tr></thead>
                <tbody>
                  {gastos.map((item) => (
                    <tr key={item.id} style={{ borderBottom: '1px solid #eee7d9' }}>
                      <td style={{ padding: '10px 8px' }}>{item.fecha}</td>
                      <td style={{ padding: '10px 8px' }}><b>{item.categoria}</b></td>
                      <td style={{ padding: '10px 8px', color: '#52627a' }}>{item.descripcion || '—'}</td>
                      <td style={{ padding: '10px 8px', fontSize: 11 }}>{item.es_recurrente ? `Recurrente ${item.frecuencia || ''}` : 'Puntual'}</td>
                      <td style={{ textAlign: 'right', padding: '10px 8px', fontVariantNumeric: 'tabular-nums', color: '#dc2626', fontWeight: 700 }}>{fmtDebit(item.monto)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* ── COMPRAS ──────────────────────────────────────────────────────── */}
        {activeTab === 'Compras' && (
          <div style={{ display: 'grid', gridTemplateColumns: 'minmax(280px, 0.85fr) minmax(0, 1.8fr)', gap: 24, alignItems: 'start' }}>
            <div className="acct-card">
              <h3 style={{ margin: '0 0 16px', color: '#14263d', fontSize: 15, fontWeight: 800 }}>Registrar Compra a Proveedor</h3>
              <form className="finance-entry-form" onSubmit={(e) => {
                e.preventDefault()
                const f = new FormData(e.currentTarget)
                compraMutation.mutate({ fecha: f.get('fecha'), proveedor: f.get('proveedor'), descripcion: f.get('descripcion'), cantidad: Number(f.get('cantidad')), unidad: f.get('unidad'), costo_total: Number(f.get('costo_total')) })
                e.currentTarget.reset()
              }}>
                <input name="fecha" type="date" defaultValue={todayText} required />
                <input name="proveedor" placeholder="Proveedor" required />
                <input name="descripcion" placeholder="Insumo comprado" required />
                <input name="cantidad" type="number" min="0.001" step="any" placeholder="Cantidad" required />
                <select name="unidad"><option>unidad</option><option>g</option><option>kg</option><option>ml</option><option>l</option></select>
                <input name="costo_total" type="number" min="1" placeholder="Costo total pagado ($)" required />
                <button disabled={compraMutation.isPending}>{compraMutation.isPending ? 'Registrando…' : 'Registrar compra'}</button>
              </form>
            </div>
            <div className="acct-card">
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
                <h3 style={{ margin: 0, color: '#14263d', fontSize: 15, fontWeight: 800 }}>Compras a Proveedores</h3>
                <b style={{ fontVariantNumeric: 'tabular-nums' }}>{fmtDebit(compras.reduce((s, c) => s + Number(c.costo_total || 0), 0))}</b>
              </div>
              <table className="finance-table" style={{ fontSize: 13 }}>
                <thead><tr><th>Fecha</th><th>Proveedor</th><th>Insumo</th><th style={{ textAlign: 'right' }}>Cantidad</th><th style={{ textAlign: 'right' }}>Costo Total</th><th style={{ textAlign: 'right' }}>Costo Unitario</th></tr></thead>
                <tbody>
                  {compras.map((item) => (
                    <tr key={item.id} style={{ borderBottom: '1px solid #eee7d9' }}>
                      <td style={{ padding: '10px 8px' }}>{item.fecha}</td>
                      <td style={{ padding: '10px 8px' }}><b>{item.proveedor}</b></td>
                      <td style={{ padding: '10px 8px', color: '#52627a' }}>{item.descripcion}</td>
                      <td style={{ textAlign: 'right', padding: '10px 8px' }}>{item.cantidad} {item.unidad}</td>
                      <td style={{ textAlign: 'right', padding: '10px 8px', fontVariantNumeric: 'tabular-nums', color: '#dc2626', fontWeight: 700 }}>{fmtDebit(item.costo_total)}</td>
                      <td style={{ textAlign: 'right', padding: '10px 8px', fontVariantNumeric: 'tabular-nums', color: '#52627a' }}>{fmtAcc(item.costo_unitario)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* ── CONCILIACIÓN ─────────────────────────────────────────────────── */}
        {data && activeTab === 'Conciliación' && (
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 24 }}>
            <div className="acct-card">
              <h2 style={{ margin: '0 0 4px', color: '#14263d', fontSize: 16, fontWeight: 800 }}>Conciliación de Caja</h2>
              <p style={{ margin: '0 0 20px', color: '#52627a', fontSize: 13 }}>Comparativo sistema vs cierres registrados</p>

              <AccRow label="VENTAS REGISTRADAS EN SISTEMA" header />
              <AccRow label="Total facturado al cliente (inc. IVA)" value={resumen.ventas_netas} indent />
              <AccRow label="(-) IVA incluido en ventas" value={resumen.iva_recaudado} debit indent />
              <AccRow label="(-) Descuentos concedidos" value={resumen.total_descuentos} debit indent />
              <AccRow label="Ingresos netos operacionales" value={ingresosNetosOp} subtotal />

              <div style={{ height: 16 }} />
              <AccRow label="RECAUDO POR MÉTODO DE PAGO" header />
              {(data.metodos_pago || []).map((item) => (
                <AccRow key={item.metodo} label={item.metodo} value={item.total} indent />
              ))}
              <AccRow label="TOTAL RECAUDADO" value={data.metodos_pago.reduce((s, m) => s + m.total, 0)} subtotal />

              <div style={{ height: 16 }} />
              <AccRow label="CONCILIACIÓN CON CIERRES DE CAJA" header />
              <AccRow label="Ventas registradas en cierres" value={conciliacion.ventas_cierres} indent />
              <AccRow label="Total contado en cierres" value={conciliacion.total_contado} indent />
              <AccRow label="Diferencia (sistema − cierres)" value={conciliacion.diferencia} total />
              {Number(conciliacion.diferencia) !== 0 && (
                <div style={{ padding: '8px 4px', fontSize: 12, color: '#dc2626', fontWeight: 600 }}>
                  ⚠ Diferencia detectada. Verifique cierres de caja del período.
                </div>
              )}
              {Number(conciliacion.diferencia) === 0 && conciliacion.ventas_cierres > 0 && (
                <div style={{ padding: '8px 4px', fontSize: 12, color: '#16a34a', fontWeight: 600 }}>
                  ✓ Caja cuadrada
                </div>
              )}
            </div>

            <div className="acct-card">
              <SectionTitle>Distribución de recaudo</SectionTitle>
              {(data.metodos_pago || []).map((item) => {
                const totalRec = data.metodos_pago.reduce((s, m) => s + m.total, 0) || 1
                return (
                  <div key={item.metodo} style={{ padding: '12px 4px', borderBottom: '1px solid #eee7d9' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 6 }}>
                      <span style={{ fontSize: 14, color: '#1f2d3d', fontWeight: 600 }}>{item.metodo}</span>
                      <span style={{ fontVariantNumeric: 'tabular-nums', fontWeight: 700 }}>{fmtAcc(item.total)}</span>
                    </div>
                    <div style={{ height: 6, background: '#eee7d9', borderRadius: 3 }}>
                      <div style={{ height: 6, background: '#c9a227', borderRadius: 3, width: `${(item.total / totalRec) * 100}%` }} />
                    </div>
                    <div style={{ fontSize: 11, color: '#52627a', marginTop: 3 }}>{item.porcentaje}% del total · {item.cantidad} transacciones</div>
                  </div>
                )
              })}
            </div>
          </div>
        )}

        {/* ── COMPARATIVO ──────────────────────────────────────────────────── */}
        {data && activeTab === 'Comparativo' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 24 }}>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 16 }}>
              {[
                { label: 'Ventas Netas', actual: comparativo.actual?.ventas_netas, anterior: comparativo.anterior?.ventas_netas, var: comparativo.variacion_ventas },
                { label: 'Nº Órdenes', actual: comparativo.actual?.ordenes, anterior: comparativo.anterior?.ordenes, var: comparativo.variacion_ordenes, raw: true },
                { label: 'Ticket Promedio', actual: metricas.ticket_promedio, anterior: comparativo.anterior?.ventas_netas / Math.max(comparativo.anterior?.ordenes || 1, 1), var: comparativo.variacion_ticket },
              ].map((item) => (
                <div key={item.label} className="acct-card" style={{ textAlign: 'center' }}>
                  <div style={{ fontSize: 12, color: '#52627a', fontWeight: 700, textTransform: 'uppercase', letterSpacing: 1, marginBottom: 8 }}>{item.label}</div>
                  <div style={{ display: 'flex', justifyContent: 'center', gap: 32, marginBottom: 12 }}>
                    <div><div style={{ fontSize: 11, color: '#52627a' }}>Actual</div><div style={{ fontWeight: 900, fontSize: 18, color: '#14263d' }}>{item.raw ? item.actual : fmtAcc(item.actual)}</div></div>
                    <div><div style={{ fontSize: 11, color: '#52627a' }}>Anterior</div><div style={{ fontWeight: 700, fontSize: 18, color: '#94a3b8' }}>{item.raw ? item.anterior : fmtAcc(item.anterior)}</div></div>
                  </div>
                  <div style={{ fontSize: 20, fontWeight: 900, color: varColor(item.var) }}>
                    {Number(item.var) > 0 ? '+' : ''}{Number(item.var).toFixed(1)}%
                  </div>
                </div>
              ))}
            </div>

            <div className="acct-card">
              <SectionTitle>Comparativo Detallado — Período Actual vs Período Anterior</SectionTitle>
              <table className="finance-table" style={{ fontSize: 13 }}>
                <thead>
                  <tr>
                    <th>Indicador</th>
                    <th style={{ textAlign: 'right' }}>Período Actual</th>
                    <th style={{ textAlign: 'right' }}>Período Anterior</th>
                    <th style={{ textAlign: 'right' }}>Variación %</th>
                    <th style={{ textAlign: 'right' }}>Variación $</th>
                  </tr>
                </thead>
                <tbody>
                  {[
                    ['Ventas netas', comparativo.actual?.ventas_netas, comparativo.anterior?.ventas_netas, comparativo.variacion_ventas],
                    ['Nº órdenes', comparativo.actual?.ordenes, comparativo.anterior?.ordenes, comparativo.variacion_ordenes, true],
                    ['Ticket promedio', metricas.ticket_promedio, comparativo.anterior?.ventas_netas / Math.max(comparativo.anterior?.ordenes || 1, 1), comparativo.variacion_ticket],
                    ['Food Cost %', data.rentabilidad.food_cost_promedio, null, null, true],
                  ].map(([label, actual, anterior, varPct, raw]) => (
                    <tr key={label} style={{ borderBottom: '1px solid #eee7d9' }}>
                      <td style={{ padding: '10px 8px' }}><b>{label}</b></td>
                      <td style={{ textAlign: 'right', padding: '10px 8px', fontVariantNumeric: 'tabular-nums' }}>{raw ? actual : fmtAcc(actual)}</td>
                      <td style={{ textAlign: 'right', padding: '10px 8px', fontVariantNumeric: 'tabular-nums', color: '#94a3b8' }}>{anterior != null ? (raw ? anterior : fmtAcc(anterior)) : '—'}</td>
                      <td style={{ textAlign: 'right', padding: '10px 8px', fontWeight: 700, color: varPct != null ? varColor(varPct) : '#94a3b8' }}>
                        {varPct != null ? `${Number(varPct) > 0 ? '+' : ''}${Number(varPct).toFixed(1)}%` : '—'}
                      </td>
                      <td style={{ textAlign: 'right', padding: '10px 8px', fontVariantNumeric: 'tabular-nums', color: '#52627a' }}>
                        {actual != null && anterior != null && !raw ? fmtAcc(Number(actual) - Number(anterior)) : '—'}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

      </main>
    </div>
  )
}
