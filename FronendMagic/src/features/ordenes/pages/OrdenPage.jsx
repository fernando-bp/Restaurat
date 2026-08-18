import { useEffect, useMemo, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import apiClient from '../../../shared/api/apiClient'
import { getMesa } from '../../mesas/services/mesasService'
import { getOrden, getRecetas, crearOrden, confirmarOrden, actualizarItem, eliminarItem } from '../services/ordenesService'
import { formatCOP } from '../../../shared/utils/currency'

const normalizeDbName = (value = '') =>
  value
    .trim()
    .toLowerCase()
    .normalize('NFD')
    .replace(/[-]/g, (c) => c)
    .replace(/[\u0300-\u036f]/g, '')
    .replace(/[^\w\s]/g, ' ')
    .replace(/\s+/g, ' ')
    .trim()

const formatTitle = (dbName) =>
  dbName
    .replace(/\.[^/.]+$/, '')
    .replace(/[_-]+/g, ' ')
    .replace(/\s+/g, ' ')
    .trim()
    .split(' ')
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1).toLowerCase())
    .join(' ')

const displayNameOverrides = {
  'des amer': 'Desayuno Americano',
  'des cont': 'Desayuno Continental',
  'des boya': 'Desayuno Boyacense',
  'ham doble carne mayo cilantro': 'Hamburguesa doble carne con mayo de cilantro',
}

const getDisplayTitle = (dbName) => displayNameOverrides[normalizeDbName(dbName)] || formatTitle(dbName)

const getCategory = (dbName) => {
  const normalized = normalizeDbName(dbName)
  if (/desayuno|americano|continental|croissant|pancake/.test(normalized)) return 'Desayunos'
  if (/entrada|bruschetta|envolto|dip|tost|parfait/.test(normalized)) return 'Entradas'
  if (/sopa|caldo|trucha/.test(normalized)) return 'Sopas'
  if (/carne|costillas|pollo|hamburguesa|longanizas|tomahawk|molcajete|chorrillana|lasagna|pizza|salmon|rissoto/.test(normalized)) return 'Platos Fuertes'
  if (/costilla|cerdo|chorizo|pollo|hamburguesa|steak|toma/.test(normalized)) return 'Carnes'
  return 'Platos Fuertes'
}

const categoryLabels = {
  desayuno: 'Desayuno',
  entrada: 'Entrada',
  fuerte: 'Fuerte',
  pizza: 'Pizza',
  pasta: 'Pasta',
  hamburguesa: 'Hamburguesa',
  al_horno: 'Al horno',
  bebida: 'Bebida',
  licor: 'Licor',
  postre: 'Postre',
  otro: 'Otro',
}

const getRecipeCategory = (receta) =>
  categoryLabels[receta?.categoria_menu] || getCategory(receta?.nombre || '')

const priceFromName = (dbName) => {
  const score = normalizeDbName(dbName).split('').reduce((sum, char) => sum + char.charCodeAt(0), 0)
  const raw = 10 + (score % 16) + ((score % 4) * 0.5)
  return Number(raw.toFixed(2))
}

const getApiErrorMessage = (err, fallback = 'Ocurrió un error inesperado.') => {
  const detail = err?.response?.data?.detail
  if (!detail) return err?.message || fallback
  if (typeof detail === 'string') return detail
  return detail.mensaje || detail.message || fallback
}

const isStockErrorResponse = (err) => {
  const detail = err?.response?.data?.detail
  if (typeof detail === 'object' && detail?.error === 'STOCK_INSUFICIENTE') return true
  const message = typeof detail === 'string' ? detail : detail?.mensaje
  return /stock insuficiente|Inventario para ingrediente|detalle.*stock/i.test(message || '')
}

const getStockDetails = (err) => {
  const detail = err?.response?.data?.detail
  if (typeof detail === 'object' && detail?.error === 'STOCK_INSUFICIENTE') {
    if (Array.isArray(detail.detalles) && detail.detalles.length > 0) {
      return detail.detalles
    }
    return [{
      ingrediente_id: detail.ingrediente_id,
      ingrediente_nombre: detail.ingrediente_nombre || `Ingrediente #${detail.ingrediente_id}`,
      disponible: detail.disponible,
      requerido: detail.requerido,
      faltante: Number(detail.requerido || 0) - Number(detail.disponible || 0),
      unidad: detail.unidad || '',
      productos: detail.productos || [],
    }]
  }
  return []
}

const formatStockQty = (value, unit = '') => {
  const numeric = Number(value || 0)
  const formatted = numeric >= 100 ? numeric.toFixed(0) : numeric.toFixed(2)
  return `${formatted}${unit ? ` ${unit}` : ''}`
}

const formatStockMessage = (err) => {
  const detalles = getStockDetails(err)
  if (detalles.length > 0) {
    const first = detalles[0]
    const producto = first.productos?.length ? ` para ${first.productos.join(', ')}` : ''
    return `Falta ${first.ingrediente_nombre || 'un ingrediente'}${producto}: faltan ${formatStockQty(first.faltante, first.unidad)}.`
  }
  return 'Stock insuficiente para preparar este producto.'
}

const categoryOrder = ['Todas', 'Desayuno', 'Entrada', 'Fuerte', 'Pizza', 'Pasta', 'Hamburguesa', 'Al horno', 'Bebida', 'Licor', 'Postre', 'Otro']

const recetasModules = import.meta.glob('../../cocina/recetas/*.{jpg,jpeg,png,webp,avif}', { eager: true, import: 'default' })

const localRecipeImages = Object.entries(recetasModules).reduce((acc, [path, module]) => {
  const fileName = path.split('/').pop().replace(/\.[^/.]+$/, '')
  const image = typeof module === 'string' ? module : module?.default
  if (image) acc[normalizeDbName(fileName)] = image
  return acc
}, {})

// Algunos PNG heredados contienen un fondo negro incrustado. Usamos la foto
// equivalente del catálogo mientras esos archivos se reemplazan en origen.
const imageFallbacks = {
  'des cont': localRecipeImages['des amer'],
  'lasagna pollo y champinones': localRecipeImages['lasagna bolognesa'],
}

if (Object.keys(localRecipeImages).length === 0) {
  console.warn('OrdenPage: no se cargaron imágenes de recetas. Revisa la ruta de importación o que el directorio exista en src/features/cocina/recetas.')
}

export default function OrdenPage() {
  const { id: mesaId } = useParams()
  const parsedMesaId = Number(mesaId)
  const isValidMesaId = Number.isInteger(parsedMesaId) && parsedMesaId > 0
  const navigate = useNavigate()
  const [mesaState, setMesaState] = useState(null)
  const [ordenState, setOrdenState] = useState(null)
  const [orderItemsState, setOrderItemsState] = useState([])
  const [recetas, setRecetas] = useState([])
  const [activeCategory, setActiveCategory] = useState('Todas')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [successMessage, setSuccessMessage] = useState('')
  const [errorMessage, setErrorMessage] = useState('')
  const [stockWarning, setStockWarning] = useState('')
  const [stockDetails, setStockDetails] = useState([])
  const [showStockInline, setShowStockInline] = useState(false)
  const [isOrderDrawerOpen, setIsOrderDrawerOpen] = useState(false)

  useEffect(() => {
    const loadMesaAndOrden = async () => {
      setLoading(true)
      setError('')
      setSuccessMessage('')
      setErrorMessage('')
      setMesaState(null)
      setOrdenState(null)
      setOrderItemsState([])

      try {
        const mesa = await getMesa(parsedMesaId)
        setMesaState(mesa)

        if (mesa?.orden_id) {
          try {
            const orden = await getOrden(mesa.orden_id)
            setOrdenState(orden)
            setOrderItemsState(
              orden.items.map((item) => ({
                itemId: item.id,
                recipeId: item.receta_id,
                id: item.receta_id,
                title: item.title || `Producto #${item.receta_id}`,
                price: Number(item.precio_unitario),
                quantity: Number(item.cantidad),
                estado: item.estado || 'pendiente',
              })),
            )
          } catch (err) {
            if (err?.response?.status === 404) {
              setMesaState((prev) => (prev ? { ...prev, orden_id: null } : prev))
              setErrorMessage('La orden asociada a esta mesa ya no existe. Vuelve a mesas y abre la mesa nuevamente.')
            } else {
              throw err
            }
          }
        }
      } catch (err) {
        setError(err?.response?.data?.detail || err.message || 'No se pudo cargar la mesa')
      } finally {
        setLoading(false)
      }
    }

    const loadRecetas = async () => {
      try {
        const recetasData = await getRecetas()
        setRecetas(recetasData)
      } catch (err) {
        console.warn('No se pudieron cargar las recetas desde el backend:', err)
      }
    }

    if (!isValidMesaId) {
      setLoading(false)
      setError('La mesa seleccionada no es válida. Regresa al mapa e inténtalo nuevamente.')
    } else {
      loadMesaAndOrden()
      loadRecetas()
    }
  }, [mesaId, isValidMesaId, parsedMesaId])

  const menuItemsWithRecipeId = useMemo(() => {
    return recetas.map((receta) => {
      const normalizedName = normalizeDbName(receta.nombre)
      return {
        id: receta.id,
        recetaId: receta.id,
        title: getDisplayTitle(receta.nombre),
        image: receta.imagen_base64 || imageFallbacks[normalizedName] || localRecipeImages[normalizedName],
        category: getRecipeCategory(receta),
        price: Number(receta.precio_venta || priceFromName(receta.nombre)),
      }
    })
  }, [recetas])

  const filteredMenuItems = useMemo(() => {
    if (activeCategory === 'Todas') return menuItemsWithRecipeId
    return menuItemsWithRecipeId.filter((item) => item.category === activeCategory)
  }, [activeCategory, menuItemsWithRecipeId])

  const findMenuItem = (recipeId, title) =>
    menuItemsWithRecipeId.find((menuItem) =>
      menuItem.recetaId === recipeId || menuItem.id === recipeId || menuItem.title === title,
    )

  const cardQuantities = useMemo(
    () =>
      orderItemsState.reduce((acc, item) => {
        if (item.recipeId) acc[item.recipeId] = item.quantity
        return acc
      }, {}),
    [orderItemsState],
  )

  const orderItemsDisplay = useMemo(
    () =>
      orderItemsState.map((item) => {
        const menuItem = findMenuItem(item.recipeId, item.title)
        return {
          ...item,
          image: item.image || menuItem?.image,
        }
      }),
    [orderItemsState],
  )

  const displaySubtotal = useMemo(
    () => orderItemsDisplay.reduce((sum, item) => sum + item.price * item.quantity, 0),
    [orderItemsDisplay],
  )
  const totalBruto = Number(ordenState?.total_bruto ?? displaySubtotal)
  const totalNeto = Number(ordenState?.total_neto ?? totalBruto)
  const orderStatus = ordenState?.estado?.toLowerCase() || ''
  const mesaStatus = mesaState?.estado?.toLowerCase() || ''
  const isOrdenPagada = ['pagada', 'cerrada'].includes(orderStatus) || ['pagada', 'cerrada'].includes(mesaStatus)
  const isMesaLibre = mesaState?.estado?.toLowerCase().includes('libre')
  const hasOrden = Boolean(mesaState?.orden_id)
  const orderItemCount = orderItemsDisplay.reduce((sum, item) => sum + item.quantity, 0)
  const savedQuantitiesByRecipe = useMemo(
    () => (ordenState?.items || []).reduce((acc, item) => {
      acc[item.receta_id] = (acc[item.receta_id] || 0) + Number(item.cantidad)
      return acc
    }, {}),
    [ordenState],
  )
  const localQuantitiesByRecipe = useMemo(
    () => orderItemsState.reduce((acc, item) => {
      const recetaId = item.recipeId || item.id
      acc[recetaId] = (acc[recetaId] || 0) + Number(item.quantity)
      return acc
    }, {}),
    [orderItemsState],
  )
  const hasBackendPendingItems = (ordenState?.items || []).some((item) => (item.estado || 'pendiente') === 'pendiente')
  const canConfirmOrder = orderItemCount > 0 && !isOrdenPagada
  const filterPillStyles = (category) => ({
    padding: '10px 18px',
    borderRadius: 9999,
    border: '1px solid #e2e8f0',
    background: activeCategory === category ? '#0f172a' : '#fff',
    color: activeCategory === category ? '#fff' : '#0f172a',
    cursor: 'pointer',
    fontWeight: 700,
  })

  const handleAddToOrder = (product) => {
    if (!product.recetaId) {
      setErrorMessage('El producto seleccionado no está disponible para enviar al backend.')
      return
    }

    setOrderItemsState((prev) => {
      const exists = prev.find((item) => item.recipeId === product.recetaId || item.id === product.id)
      if (exists) {
        return prev.map((item) =>
          item.recipeId === product.recetaId || item.id === product.id
            ? { ...item, quantity: item.quantity + 1 }
            : item,
        )
      }
      return [
        ...prev,
        {
          recipeId: product.recetaId,
          id: product.id,
          title: product.title,
          price: product.price,
          quantity: 1,
          image: product.image,
        },
      ]
    })
  }

  const reloadOrden = async (ordenId) => {
    const orden = await getOrden(ordenId)
    setOrdenState(orden)
    setOrderItemsState(
      orden.items.map((item) => ({
        itemId: item.id,
        recipeId: item.receta_id,
        id: item.receta_id,
        title: item.title || `Producto #${item.receta_id}`,
        price: Number(item.precio_unitario),
        quantity: Number(item.cantidad),
        estado: item.estado || 'pendiente',
      })),
    )
  }

  const handleQuantityChange = (targetItem, delta) => {
    const currentItem = orderItemsState.find((item) =>
      targetItem.itemId ? item.itemId === targetItem.itemId : item.recipeId === targetItem.recipeId && !item.itemId,
    )
    if (!currentItem) return

    if (currentItem.itemId && currentItem.estado !== 'pendiente') {
      setErrorMessage('Este producto ya fue enviado a cocina y no puede modificarse desde la orden.')
      return
    }

    const nextQuantity = Math.max(1, currentItem.quantity + delta)
    setOrderItemsState((prev) =>
      prev.map((item) =>
        targetItem.itemId ? item.itemId === targetItem.itemId ? { ...item, quantity: nextQuantity } : item : item.recipeId === targetItem.recipeId && !item.itemId ? { ...item, quantity: nextQuantity } : item,
      ),
    )
    // All changes are batched and synced to backend on "Confirmar"
  }

  const sidebarMessage = orderItemsDisplay.length === 0
    ? 'Agrega un plato desde el menú para iniciar la orden.'
    : 'Ajusta cantidades o elimina productos antes de confirmar.'

  const handleRemoveFromOrder = (targetItem) => {
    setSuccessMessage('')
    setErrorMessage('')
    setOrderItemsState((prev) => prev.filter((item) =>
      targetItem.itemId ? item.itemId !== targetItem.itemId : !(item.recipeId === targetItem.recipeId && !item.itemId),
    ))
    // Saved items (itemId present) are deleted from backend on "Confirmar"
  }

  const handleConfirmarOrden = async () => {
    setSuccessMessage('')
    setErrorMessage('')
    setStockWarning('')
    setStockDetails([])

    try {
      const existingOrdenId = ordenState?.orden_id || mesaState?.orden_id

      // 1. Sync local changes to saved items (deletions + quantity decreases)
      if (existingOrdenId) {
        const savedItems = ordenState?.items || []

        const toDelete = savedItems
          .filter((si) => (si.estado || 'pendiente') === 'pendiente')
          .filter((si) => !orderItemsState.find((local) => local.itemId === si.id))

        const toUpdate = orderItemsState.filter((local) => {
          if (!local.itemId) return false
          const saved = savedItems.find((si) => si.id === local.itemId)
          return saved && Number(saved.cantidad) !== local.quantity && (saved.estado || 'pendiente') === 'pendiente'
        })

        if (toDelete.length > 0 || toUpdate.length > 0) {
          await Promise.all([
            ...toDelete.map((si) => eliminarItem(existingOrdenId, si.id)),
            ...toUpdate.map((local) => actualizarItem(existingOrdenId, local.itemId, { cantidad: local.quantity })),
          ])
        }
      }

      // 2. Add new / increased items
      const itemsToSave = Object.entries(localQuantitiesByRecipe)
        .map(([recetaId, quantity]) => ({
          receta_id: Number(recetaId),
          cantidad: quantity - (hasOrden ? savedQuantitiesByRecipe[recetaId] || 0 : 0),
        }))
        .filter((item) => item.cantidad > 0)

      if (itemsToSave.length === 0 && orderItemCount === 0 && !existingOrdenId) {
        setErrorMessage('Selecciona al menos un producto para crear la orden.')
        return
      }

      const payload = {
        mesa_id: Number(mesaId),
        num_comensales: mesaState?.num_comensales || 1,
        items: itemsToSave,
      }

      let ordenId = existingOrdenId

      if (itemsToSave.length > 0) {
        const created = await crearOrden(payload)
        ordenId = created.orden_id
        setMesaState((prev) => (prev ? { ...prev, estado: 'ocupada', orden_id: ordenId } : prev))
      }

      if (!ordenId) {
        setErrorMessage('No se pudo identificar la orden activa para confirmar.')
        return
      }

      // Determine if there are still pending items to send to kitchen
      const deletedIds = new Set((ordenState?.items || [])
        .filter((si) => (si.estado || 'pendiente') === 'pendiente')
        .filter((si) => !orderItemsState.find((local) => local.itemId === si.id))
        .map((si) => si.id))
      const remainingPending = (ordenState?.items || []).some(
        (si) => (si.estado || 'pendiente') === 'pendiente' && !deletedIds.has(si.id),
      )

      if (itemsToSave.length === 0 && !remainingPending) {
        await reloadOrden(ordenId)
        setSuccessMessage('Orden actualizada correctamente.')
        return
      }

      await confirmarOrden(ordenId)
      await reloadOrden(ordenId)
      setSuccessMessage('Orden confirmada exitosamente. Enviada a cocina.')
      return
    } catch (err) {
      if (isStockErrorResponse(err)) {
        const detalles = getStockDetails(err)
        setStockWarning(formatStockMessage(err))
        setStockDetails(detalles)
        // Enrich details with ingredient names when backend returns only ids
        (async function fillNames() {
          try {
            const placeholderRegex = /^Ingrediente #\d+$/i
            const missing = detalles.filter((d) => ( !d.ingrediente_nombre || placeholderRegex.test(String(d.ingrediente_nombre)) ) && d.ingrediente_id)
            if (missing.length === 0) return
            const promises = missing.map((d) => apiClient.get(`/ingredientes/${d.ingrediente_id}`).then((r) => ({ id: d.ingrediente_id, nombre: r.data.nombre })).catch(() => null))
            const results = await Promise.all(promises)
            const namesMap = {}
            results.forEach((r) => { if (r && r.id) namesMap[r.id] = r.nombre })
            const enriched = detalles.map((d) => ({ ...d, ingrediente_nombre: namesMap[d.ingrediente_id] || d.ingrediente_nombre }))
            setStockDetails(enriched)
            // Update stock warning text to include first name if available
            if (enriched.length > 0) {
              const first = enriched[0]
              if (first && first.ingrediente_nombre) {
                setStockWarning(`Falta ${first.ingrediente_nombre}: faltan ${formatStockQty(first.faltante, first.unidad)}.`)
              }
            }
          } catch (e) {
            // ignore enrichment errors
          }
        })()
      } else {
        setErrorMessage(getApiErrorMessage(err, 'Error al confirmar la orden.'))
      }
    }
  }

  const handleCancelar = async () => {
    // Validar cierre de orden si existe
    if (ordenState?.orden_id) {
      try {
        const response = await apiClient.post(`/ordenes/${ordenState.orden_id}/validar-cierre`)
        console.log('Validación de cierre:', response.data)
      } catch (error) {
        console.warn('No se pudo validar cierre:', error)
      }
    }
    
    setOrderItemsState([])
    navigate('/mesas')
  }

  return (
    <div className="pos-wrapper orden-page">
      {stockWarning ? (
        <div className="stock-modal-overlay" role="dialog" aria-modal="true" aria-labelledby="stock-modal-title">
          <div className="stock-modal-panel">
            <div className="stock-modal-icon">!</div>
            <div className="stock-modal-content">
              <h2 id="stock-modal-title">Stock insuficiente</h2>
              <p>{stockWarning}</p>
              {stockDetails.length > 0 ? (
                <div className="stock-modal-list">
                  {stockDetails.map((detail) => (
                    <div key={detail.ingrediente_id || detail.ingrediente_nombre} className="stock-modal-item">
                      <strong>{detail.ingrediente_nombre || `Ingrediente #${detail.ingrediente_id}`}</strong>
                      {detail.productos?.length ? (
                        <span>Producto: {detail.productos.join(', ')}</span>
                      ) : null}
                      <small>
                        Disponible: {formatStockQty(detail.disponible, detail.unidad)} · Requerido: {formatStockQty(detail.requerido, detail.unidad)} · Faltante: {formatStockQty(detail.faltante, detail.unidad)}
                      </small>
                    </div>
                  ))}
                </div>
              ) : null}
              <button type="button" onClick={() => { setStockWarning(''); setStockDetails([]) }}>
                Entendido
              </button>
            </div>
          </div>
        </div>
      ) : null}

      <div className="orden-header" style={{ marginBottom: 24 }}>
        <div className="orden-header__left">
          <button type="button" onClick={() => navigate('/mesas')} className="orden-back-button">
            ← Volver a Mesas
          </button>
          <div className="orden-header__title">
            <span className="orden-header__mesa-label">Mesa {mesaState?.numero ?? mesaId}</span>
            <h1>Orden Actual</h1>
            <span className="orden-header__mesa-meta">Capacidad: {mesaState?.capacidad ?? '—'} personas</span>
          </div>
          {hasOrden ? (
            <button
              type="button"
              onClick={() => navigate(`/caja/${mesaId}`)}
              className="orden-cash-button"
            >
              Ir a caja
            </button>
          ) : null}
        </div>
        <div className="orden-header__summary">
          <span className="orden-header__summary-pill">{orderItemCount} ítems</span>
          <span className="orden-header__summary-total">{formatCOP(displaySubtotal)}</span>
        </div>
      </div>

      {loading ? (
        <div style={{ padding: 24, background: '#fff', borderRadius: 20, boxShadow: '0 18px 40px rgba(2,6,23,0.07)' }}>
          Cargando orden...
        </div>
      ) : error ? (
        <div style={{ padding: 24, background: '#fee2e2', borderRadius: 20, color: '#b91c1c' }}>{error}</div>
      ) : (
        <div className="orden-content">
          <section className="orden-catalog">
            <div className="orden-catalog__top">
              <div>
                <h2>Menú</h2>
                <p>{filteredMenuItems.length} productos</p>
              </div>
              <div className="orden-categories">
                {categoryOrder.map((category) => (
                  <button
                    key={category}
                    type="button"
                    onClick={() => setActiveCategory(category)}
                    className={`orden-category-pill ${activeCategory === category ? 'active' : ''}`}
                  >
                    {category}
                  </button>
                ))}
              </div>
            </div>

            <div className="orden-grid">
              {filteredMenuItems.map((product) => (
                <article key={product.id} className={`orden-card ${cardQuantities[product.recetaId] > 0 ? 'selected' : ''}`}>
                  <div className="orden-card__image-wrapper">
                    {product.image ? (
                      <img src={product.image} alt={product.title} className="orden-card__image" />
                    ) : (
                      <div className="orden-card__image orden-card__image-placeholder">
                        <span>{product.title.slice(0, 2).toUpperCase()}</span>
                      </div>
                    )}
                    {cardQuantities[product.recetaId] > 0 ? (
                      <span className="orden-card__badge">{cardQuantities[product.recetaId]}</span>
                    ) : null}
                  </div>
                  <div className="orden-card__body">
                    <div>
                      <h3 title={product.title}>{product.title}</h3>
                      <p className="orden-card__category">{product.category}</p>
                    </div>
                    <div className="orden-card__footer">
                      <p className="orden-card__price">{formatCOP(product.price)}</p>
                      <button
                        type="button"
                        onClick={() => handleAddToOrder(product)}
                        disabled={!product.recetaId}
                        className="orden-card__button"
                        style={{ opacity: product.recetaId ? 1 : 0.5, cursor: product.recetaId ? 'pointer' : 'not-allowed' }}
                      >
                        {product.recetaId ? '+ Agregar' : 'No disponible'}
                      </button>
                    </div>
                  </div>
                </article>
              ))}
            </div>
          </section>

          <aside className={`orden-sidebar ${isOrderDrawerOpen ? 'is-drawer-open' : ''}`}>
            <div className="orden-sidebar__panel">
              <button type="button" className="orden-drawer-close" onClick={() => setIsOrderDrawerOpen(false)} aria-label="Cerrar orden">×</button>
              <div className="orden-sidebar__title">
                <div>
                  <p className="orden-sidebar__label">Orden Actual</p>
                  <h2>Mesa {mesaState?.numero ?? mesaId}</h2>
                  <p className="orden-sidebar__description">{filteredMenuItems.length} productos disponibles</p>
                </div>
                <span className="orden-sidebar__badge">{orderItemCount} ítems</span>
              </div>

              <div className="orden-sidebar__body">
                {orderItemsDisplay.length === 0 ? (
                  <div className="orden-empty-state">{sidebarMessage}</div>
                ) : null}

                {orderItemsDisplay.length > 0 ? (
                  <div className="orden-items-list">
                    {orderItemsDisplay.map((item) => (
                      <div key={item.itemId ?? `local-${item.recipeId}`} className="orden-item-card">
                        {item.image ? (
                          <img src={item.image} alt={item.title} className="orden-item-card__image" />
                        ) : (
                          <div className="orden-item-card__image" />
                        )}
                        <div className="orden-item-card__content">
                          <div className="orden-item-card__header">
                            <h3>{item.title}</h3>
                            <button
                              type="button"
                              onClick={() => handleRemoveFromOrder(item)}
                              className="orden-item-card__remove"
                              aria-label={`Eliminar ${item.title}`}
                              title={`Eliminar ${item.title}`}
                            >
                              ×
                            </button>
                          </div>
                          <p className="orden-item-card__price">{formatCOP(item.price)} c/u</p>

                          <div className="orden-item-card__line-actions">
                            <div className="orden-item-card__controls">
                              <button type="button" onClick={() => handleQuantityChange(item, -1)} disabled={Boolean(item.itemId && item.estado !== 'pendiente')}>−</button>
                              <span>{item.quantity}</span>
                              <button type="button" onClick={() => handleQuantityChange(item, 1)} disabled={Boolean(item.itemId && item.estado !== 'pendiente')}>+</button>
                            </div>
                            <div style={{ fontWeight: 700 }}>{formatCOP(item.price * item.quantity)}</div>
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                ) : null}
              </div>

              <div className="orden-sidebar__footer">
                <div style={{ display: 'grid', gap: 16, color: '#475569' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <span>Subtotal</span>
                    <strong>{formatCOP(displaySubtotal)}</strong>
                  </div>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontSize: 18, fontWeight: 700, color: '#0f172a' }}>
                    <span>Total</span>
                    <strong>{formatCOP(displaySubtotal)}</strong>
                  </div>
                </div>

                {successMessage ? (
                  <div style={{ padding: 14, borderRadius: 18, background: '#dcfce7', color: '#166534' }}>{successMessage}</div>
                ) : null}

                {errorMessage ? (
                  <div style={{ padding: 14, borderRadius: 18, background: '#fee2e2', color: '#991b1b' }}>{errorMessage}</div>
                ) : null}

                {stockWarning ? (
                  <div className="stock-inline">
                    <div className="stock-inline-message">Stock insuficiente para confirmar la orden.</div>
                    {stockDetails.length > 0 ? (
                      <div className="stock-inline-list">
                        {stockDetails.slice(0, showStockInline ? stockDetails.length : 3).map((d) => (
                          <div key={d.ingrediente_id || d.ingrediente_nombre} className="stock-inline-item">
                            <strong>{d.ingrediente_nombre || `Ingrediente #${d.ingrediente_id}`}</strong>
                            <span> · Faltan {formatStockQty(d.faltante, d.unidad)}</span>
                          </div>
                        ))}
                        {stockDetails.length > 3 && !showStockInline ? <div className="stock-inline-more">y {stockDetails.length - 3} más...</div> : null}
                      </div>
                    ) : null}
                    <div style={{ display: 'flex', gap: 8, marginTop: 8 }}>
                      <button type="button" onClick={() => setShowStockInline((s) => !s)} className="orden-cancel-button" style={{ padding: '8px 12px' }}>
                        {showStockInline ? 'Ocultar' : 'Mostrar detalles'}
                      </button>
                      <button type="button" onClick={() => { setStockWarning(''); setStockDetails([]) }} className="orden-cancel-button" style={{ padding: '8px 12px' }}>
                        Cerrar alerta
                      </button>
                    </div>
                  </div>
                ) : null}

                <button
                  type="button"
                  onClick={handleConfirmarOrden}
                  disabled={!canConfirmOrder}
                  className="orden-confirm-button"
                  aria-disabled={!canConfirmOrder}
                >
                  Confirmar Orden
                </button>

                <button type="button" onClick={handleCancelar} className="orden-cancel-button">
                  Cancelar
                </button>
              </div>
            </div>
          </aside>
          <button type="button" className="orden-drawer-trigger" onClick={() => setIsOrderDrawerOpen(true)}>
            <span>{orderItemCount} ítems</span>
            <strong>{formatCOP(displaySubtotal)}</strong>
          </button>
        </div>
      )}
    </div>
  )
}
