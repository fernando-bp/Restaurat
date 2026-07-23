import { useState } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { useInventario } from '../hooks/useInventario'
import { actualizarStockInventario } from '../services/inventarioService'

export default function InventarioPage() {
  const { data: inventario = [], isLoading, isError, error, refetch } = useInventario()
  const queryClient = useQueryClient()
  const [editingId, setEditingId] = useState(null)
  const [stockValue, setStockValue] = useState('')
  const actualizarStockMutation = useMutation({
    mutationFn: ({ id, stock }) => actualizarStockInventario(id, stock),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['inventario'] })
      setEditingId(null)
      setStockValue('')
    },
  })
  const errorMessage = error?.response?.status === 401
    ? 'Tu sesion vencio. Vuelve a iniciar sesion para consultar inventario.'
    : error?.response?.data?.detail || error?.message || 'Revise la conexion y vuelva a intentar.'

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
          Error al cargar inventario: {errorMessage}
        </p>
      )}
      {actualizarStockMutation.isError && (
        <p style={{ color: '#c62828' }}>
          No se pudo guardar el stock: {actualizarStockMutation.error?.response?.data?.detail || actualizarStockMutation.error?.message || 'Inténtalo nuevamente.'}
        </p>
      )}

      {!isLoading && !isError && (
        <div style={{ overflowX: 'auto', marginTop: 24 }}>
          <table style={{ width: '100%', borderCollapse: 'collapse', minWidth: 760 }}>
            <thead>
              <tr>
                <th style={{ textAlign: 'left', padding: '12px 10px', borderBottom: '2px solid #ddd' }}>Ingrediente</th>
                <th style={{ textAlign: 'right', padding: '12px 10px', borderBottom: '2px solid #ddd' }}>Stock actual</th>
                <th style={{ textAlign: 'left', padding: '12px 10px', borderBottom: '2px solid #ddd' }}>Unidad</th>
                <th style={{ textAlign: 'right', padding: '12px 10px', borderBottom: '2px solid #ddd' }}>Stock minimo</th>
                <th style={{ textAlign: 'right', padding: '12px 10px', borderBottom: '2px solid #ddd' }}>Stock maximo</th>
                <th style={{ textAlign: 'left', padding: '12px 10px', borderBottom: '2px solid #ddd' }}>Ubicacion</th>
                <th style={{ textAlign: 'center', padding: '12px 10px', borderBottom: '2px solid #ddd' }}>Alerta</th>
                <th style={{ textAlign: 'center', padding: '12px 10px', borderBottom: '2px solid #ddd' }}>Accion</th>
              </tr>
            </thead>
            <tbody>
              {inventario.map((item) => {
                const isLowStock = item.esta_en_alerta
                return (
                  <tr key={item.id} style={{ background: isLowStock ? '#fff6f6' : 'transparent' }}>
                    <td style={{ padding: '12px 10px', borderBottom: '1px solid #eee' }}>{item.nombre_ingrediente}</td>
                    <td style={{ padding: '12px 10px', borderBottom: '1px solid #eee', textAlign: 'right' }}>
                      {editingId === item.id ? (
                        <input
                          aria-label={`Nuevo stock para ${item.nombre_ingrediente}`}
                          type="number"
                          min="0"
                          step="0.01"
                          value={stockValue}
                          onChange={(event) => setStockValue(event.target.value)}
                          style={{ width: 96, padding: 6, textAlign: 'right' }}
                        />
                      ) : item.stock_actual.toFixed(2)}
                    </td>
                    <td style={{ padding: '12px 10px', borderBottom: '1px solid #eee' }}>{item.unidad || '-'}</td>
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
                    <td style={{ padding: '12px 10px', borderBottom: '1px solid #eee', textAlign: 'center', whiteSpace: 'nowrap' }}>
                      {editingId === item.id ? (
                        <>
                          <button
                            type="button"
                            disabled={actualizarStockMutation.isPending || stockValue === '' || Number(stockValue) < 0}
                            onClick={() => actualizarStockMutation.mutate({ id: item.id, stock: Number(stockValue) })}
                            style={{ marginRight: 6, cursor: 'pointer' }}
                          >
                            Guardar
                          </button>
                          <button type="button" onClick={() => { setEditingId(null); setStockValue('') }} style={{ cursor: 'pointer' }}>Cancelar</button>
                        </>
                      ) : (
                        <button
                          type="button"
                          onClick={() => { setEditingId(item.id); setStockValue(String(item.stock_actual)) }}
                          style={{ cursor: 'pointer' }}
                        >
                          Modificar
                        </button>
                      )}
                    </td>
                  </tr>
                )
              })}
              {inventario.length === 0 && (
                <tr>
                  <td colSpan={8} style={{ padding: '16px 10px', textAlign: 'center' }}>
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
