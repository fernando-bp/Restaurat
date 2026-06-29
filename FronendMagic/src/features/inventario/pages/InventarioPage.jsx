import { useInventario } from '../hooks/useInventario'

export default function InventarioPage() {
  const { data: inventario = [], isLoading, isError, error, refetch } = useInventario()

  return (
    <div style={{ padding: 24 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-end', gap: 16 }}>
        <div>
          <h1>Inventario</h1>
          <p>Lista de ingredientes y niveles de stock.</p>
        </div>
        <button
          type="button"
          onClick={() => refetch()}
          style={{ padding: '10px 16px', cursor: 'pointer' }}
        >
          Actualizar
        </button>
      </div>

      {isLoading && <p>Cargando inventario...</p>}
      {isError && (
        <p style={{ color: '#c62828' }}>
          Error al cargar inventario: {error?.message ?? 'Revise la conexión y vuelva a intentar.'}
        </p>
      )}

      {!isLoading && !isError && (
        <div style={{ overflowX: 'auto', marginTop: 24 }}>
          <table style={{ width: '100%', borderCollapse: 'collapse', minWidth: 760 }}>
            <thead>
              <tr>
                <th style={{ textAlign: 'left', padding: '12px 10px', borderBottom: '2px solid #ddd' }}>Ingrediente</th>
                <th style={{ textAlign: 'right', padding: '12px 10px', borderBottom: '2px solid #ddd' }}>Stock actual</th>
                <th style={{ textAlign: 'right', padding: '12px 10px', borderBottom: '2px solid #ddd' }}>Stock mínimo</th>
                <th style={{ textAlign: 'right', padding: '12px 10px', borderBottom: '2px solid #ddd' }}>Stock máximo</th>
                <th style={{ textAlign: 'left', padding: '12px 10px', borderBottom: '2px solid #ddd' }}>Ubicación</th>
                <th style={{ textAlign: 'center', padding: '12px 10px', borderBottom: '2px solid #ddd' }}>Alerta</th>
              </tr>
            </thead>
            <tbody>
              {inventario.map((item) => {
                const isLowStock = item.esta_en_alerta
                return (
                  <tr key={item.id} style={{ background: isLowStock ? '#fff6f6' : 'transparent' }}>
                    <td style={{ padding: '12px 10px', borderBottom: '1px solid #eee' }}>{item.nombre_ingrediente}</td>
                    <td style={{ padding: '12px 10px', borderBottom: '1px solid #eee', textAlign: 'right' }}>{item.stock_actual.toFixed(2)}</td>
                    <td style={{ padding: '12px 10px', borderBottom: '1px solid #eee', textAlign: 'right' }}>{item.stock_minimo.toFixed(2)}</td>
                    <td style={{ padding: '12px 10px', borderBottom: '1px solid #eee', textAlign: 'right' }}>{item.stock_maximo != null ? item.stock_maximo.toFixed(2) : '-'}</td>
                    <td style={{ padding: '12px 10px', borderBottom: '1px solid #eee' }}>{item.ubicacion || '-'}</td>
                    <td style={{ padding: '12px 10px', borderBottom: '1px solid #eee', textAlign: 'center' }}>
                      {isLowStock ? (
                        <span style={{ color: '#b71c1c', fontWeight: 600 }}>Bajo stock</span>
                      ) : (
                        <span style={{ color: '#2e7d32', fontWeight: 600 }}>OK</span>
                      )}
                    </td>
                  </tr>
                )
              })}
              {inventario.length === 0 && (
                <tr>
                  <td colSpan={6} style={{ padding: '16px 10px', textAlign: 'center' }}>
                    No se encontraron registros de inventario.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
