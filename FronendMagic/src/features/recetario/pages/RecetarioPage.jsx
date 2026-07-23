import { useEffect, useMemo, useRef, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import { createReceta, getIngredientesCatalogo, getRecetaDetalle, getRecetas, getSubrecetasCatalogo, updateReceta } from '../services/recetarioService'
import { formatCOP } from '../../../shared/utils/currency'

const categoryOptions = [
  { value: 'desayuno', label: 'Desayuno' },
  { value: 'entrada', label: 'Entrada' },
  { value: 'fuerte', label: 'Fuerte' },
  { value: 'pizza', label: 'Pizza' },
  { value: 'pasta', label: 'Pasta' },
  { value: 'hamburguesa', label: 'Hamburguesa' },
  { value: 'al_horno', label: 'Al horno' },
  { value: 'bebida', label: 'Bebida' },
  { value: 'licor', label: 'Licor' },
  { value: 'postre', label: 'Postre' },
  { value: 'otro', label: 'Otro' },
]

const unitOptions = [
  { id: 1, value: 'g', label: 'Gramo (g)' },
  { id: 2, value: 'kg', label: 'Kilogramo (kg)' },
  { id: 3, value: 'ml', label: 'Mililitro (ml)' },
  { id: 4, value: 'l', label: 'Litro (l)' },
  { id: 5, value: 'und', label: 'Unidad (und)' },
  { id: 6, value: 'tajada', label: 'Tajada' },
  { id: 7, value: 'lamina', label: 'Lamina' },
]

const categoryAliases = {
  'sin categoria': 'otro',
  'sin categoría': 'otro',
  salsas: 'otro',
  'platos fuertes': 'fuerte',
  'plato fuerte': 'fuerte',
  fuertes: 'fuerte',
  'al horno': 'al_horno',
  bebidas: 'bebida',
  licores: 'licor',
  postres: 'postre',
}

const fallbackRecetas = [
  {
    id: 1,
    nombre: 'Salsa BBQ',
    categoria_menu: 'otro',
    precio_venta: 0,
    activa: true,
  },
  {
    id: 2,
    nombre: 'Base de tomate',
    categoria_menu: 'otro',
    precio_venta: 0,
    activa: true,
  },
  {
    id: 3,
    nombre: 'Guarnicion arroz',
    categoria_menu: 'fuerte',
    precio_venta: 0,
    activa: true,
  },
]

const fallbackDetalles = {
  1: {
    id: 1,
    nombre: 'Salsa BBQ',
    tipo: 'final',
    pax: 10,
    tiempo_prep_min: 20,
    categoria_menu: 'otro',
    activa: true,
    ingredientes: [
      { ingrediente_id: 11, nombre: 'Panela', cantidad: 120, unidad_id: 1, unidad: 'g', costo_unitario: 18, costo_total: 2160 },
      { ingrediente_id: 12, nombre: 'Vinagre', cantidad: 90, unidad_id: 3, unidad: 'ml', costo_unitario: 9, costo_total: 810 },
    ],
    sub_recetas: [
      {
        receta_base_id: 2,
        nombre: 'Base de tomate',
        cantidad_g: 300,
        ingredientes: [
          { ingrediente_id: 21, nombre: 'Tomate maduro', cantidad: 500, unidad_id: 1, unidad: 'g', costo_unitario: 7, costo_total: 3500 },
          { ingrediente_id: 22, nombre: 'Cebolla blanca', cantidad: 80, unidad_id: 1, unidad: 'g', costo_unitario: 5, costo_total: 400 },
        ],
        sub_recetas: [],
      },
    ],
  },
}

function emptyIngredient() {
  return { ingrediente_id: 0, nombre: '', cantidad: 0, unidad_id: 1, unidad: 'g', costo_unitario: 0, costo_total: 0, notas: '' }
}

function emptySubRecipe() {
  return { receta_base_id: 0, nombre: '', cantidad_g: 0, ingredientes: [emptyIngredient()], sub_recetas: [] }
}

function normalizeCategory(value) {
  const normalized = String(value || '').trim().toLowerCase()
  const category = categoryAliases[normalized] || normalized
  return categoryOptions.some((option) => option.value === category) ? category : 'otro'
}

function unitFromIngredient(ingredient) {
  return unitOptions.find((option) => option.id === Number(ingredient?.unidad_id))
    || unitOptions.find((option) => option.value === ingredient?.unidad)
    || unitOptions[0]
}

function normalizeIngredient(ingredient) {
  const unit = unitFromIngredient(ingredient)
  return {
    ...ingredient,
    unidad_id: unit.id,
    unidad: unit.value,
  }
}

function normalizeSubRecipe(subRecipe) {
  return {
    ...subRecipe,
    ingredientes: (subRecipe?.ingredientes || []).map(normalizeIngredient),
    sub_recetas: (subRecipe?.sub_recetas || []).map(normalizeSubRecipe),
  }
}

function normalizeDetail(detail, selectedId) {
  return {
    id: detail?.id || selectedId,
    nombre: detail?.nombre || 'Nueva receta',
    tipo: detail?.tipo || 'final',
    numero_receta: detail?.numero_receta || '',
    pax: Number(detail?.pax || 1),
    peso_porcion_g: detail?.peso_porcion_g || '',
    tiempo_prep_min: Number(detail?.tiempo_prep_min || 0),
    precio_venta: detail?.precio_venta ?? '',
    categoria_menu: normalizeCategory(detail?.categoria_menu),
    activa: detail?.activa ?? true,
    imagen_base64: detail?.imagen_base64 || null,
    ingredientes: (detail?.ingredientes || []).map(normalizeIngredient),
    sub_recetas: (detail?.sub_recetas || []).map(normalizeSubRecipe),
  }
}

function ingredientCost(ingredient) {
  const explicit = Number(ingredient.costo_total)
  if (Number.isFinite(explicit) && explicit > 0) return explicit
  return Number(ingredient.cantidad || 0) * Number(ingredient.costo_unitario || 0)
}

function subRecipeCost(subRecipe) {
  const ingredients = subRecipe.ingredientes || []
  const nested = subRecipe.sub_recetas || []
  return ingredients.reduce((sum, item) => sum + ingredientCost(item), 0)
    + nested.reduce((sum, item) => sum + subRecipeCost(item), 0)
}

const money = formatCOP

function optionalNumber(value) {
  if (value === '' || value === null || value === undefined) return null
  const numberValue = Number(value)
  return Number.isFinite(numberValue) ? numberValue : null
}

function numberOrFallback(value, fallback = 0) {
  const numberValue = Number(value)
  return Number.isFinite(numberValue) ? numberValue : fallback
}

function serializeIngredient(item) {
  const unit = unitFromIngredient(item)
  return {
    ...item,
    ingrediente_id: numberOrFallback(item.ingrediente_id, 0),
    unidad_id: unit.id,
    unidad: unit.value,
    cantidad: numberOrFallback(item.cantidad, 0),
    costo_unitario: optionalNumber(item.costo_unitario),
    costo_total: optionalNumber(item.costo_total),
  }
}

function serializeSubRecipe(item) {
  return {
    ...item,
    receta_base_id: numberOrFallback(item.receta_base_id, 0),
    cantidad_g: numberOrFallback(item.cantidad_g, 0),
    ingredientes: (item.ingredientes || []).map(serializeIngredient),
    sub_recetas: (item.sub_recetas || []).map(serializeSubRecipe),
  }
}

function IngredientRows({ ingredients, ingredientOptions, onChange, onRemove }) {
  return (
    <div className="recipe-table">
      <div className="recipe-table__head">
        <span>Ingrediente</span>
        <span>Cantidad</span>
        <span>Unidad</span>
        <span>Costo</span>
        <span />
      </div>
      {ingredients.map((ingredient, index) => (
        <div className="recipe-table__row" key={`${ingredient.ingrediente_id}-${index}`}>
          <input
            value={ingredient.nombre || ''}
            list="recetario-ingredientes"
            placeholder="Busca o escribe para crear"
            onChange={(event) => {
              const nombre = event.target.value
              const selected = ingredientOptions.find((option) => option.nombre.toLowerCase() === nombre.trim().toLowerCase())
              onChange(index, selected ? {
                ...ingredient,
                ingrediente_id: selected.id,
                nombre: selected.nombre,
                unidad_id: selected.unidad_id,
                unidad: selected.unidad,
                costo_unitario: selected.costo_unitario,
                costo_total: 0,
              } : { ...ingredient, ingrediente_id: 0, nombre })
            }}
          />
          <input
            type="number"
            min="0"
            value={ingredient.cantidad || 0}
            onChange={(event) => onChange(index, { ...ingredient, cantidad: Number(event.target.value) })}
          />
          <select
            value={unitFromIngredient(ingredient).id}
            onChange={(event) => {
              const unit = unitOptions.find((option) => option.id === Number(event.target.value)) || unitOptions[0]
              onChange(index, { ...ingredient, unidad_id: unit.id, unidad: unit.value })
            }}
          >
            {unitOptions.map((unit) => (
              <option key={unit.id} value={unit.id}>{unit.label}</option>
            ))}
          </select>
          <input
            type="number"
            min="0"
            value={ingredient.costo_unitario || 0}
            onChange={(event) => onChange(index, { ...ingredient, costo_unitario: Number(event.target.value), costo_total: 0 })}
          />
          <button type="button" className="recipe-icon-button" onClick={() => onRemove(index)} aria-label="Quitar ingrediente">
            x
          </button>
        </div>
      ))}
    </div>
  )
}

export default function RecetarioPage() {
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const fileInputRef = useRef(null)
  const [selectedId, setSelectedId] = useState(1)
  const [search, setSearch] = useState('')
  const [draft, setDraft] = useState(null)
  const [photoError, setPhotoError] = useState('')

  const recetasQuery = useQuery({
    queryKey: ['recetas'],
    queryFn: getRecetas,
    retry: 1,
  })
  const ingredientesQuery = useQuery({ queryKey: ['recetario-ingredientes'], queryFn: getIngredientesCatalogo })
  const subrecetasQuery = useQuery({ queryKey: ['recetario-subrecetas'], queryFn: getSubrecetasCatalogo })
  const ingredientOptions = ingredientesQuery.data || []
  const subrecipeOptions = subrecetasQuery.data || []

  const recetas = recetasQuery.data?.length ? recetasQuery.data : fallbackRecetas
  const selectedFromList = recetas.find((receta) => receta.id === selectedId) || recetas[0]

  useEffect(() => {
    if (!selectedId && recetas.length) setSelectedId(recetas[0].id)
  }, [recetas, selectedId])

  const detailQuery = useQuery({
    queryKey: ['receta-detalle', selectedId],
    queryFn: () => getRecetaDetalle(selectedId),
    enabled: Boolean(selectedId) && !draft?.is_new,
    retry: 1,
  })

  useEffect(() => {
    if (!selectedId) return
    if (draft?.is_new) return
    const source = detailQuery.data || fallbackDetalles[selectedId] || selectedFromList
    setDraft(normalizeDetail(source, selectedId))
  }, [detailQuery.data, draft?.is_new, selectedId, selectedFromList])

  const saveMutation = useMutation({
    mutationFn: (payload) => (payload.is_new ? createReceta(payload) : updateReceta(payload.id, payload)),
    onSuccess: (data) => {
      setDraft(normalizeDetail(data, data.id))
      setSelectedId(data.id)
      queryClient.invalidateQueries({ queryKey: ['recetas'] })
      queryClient.invalidateQueries({ queryKey: ['receta-detalle', data.id] })
    },
  })

  const filteredRecetas = useMemo(() => {
    const term = search.trim().toLowerCase()
    if (!term) return recetas
    return recetas.filter((receta) => `${receta.nombre} ${receta.categoria_menu || ''}`.toLowerCase().includes(term))
  }, [recetas, search])

  const totals = useMemo(() => {
    if (!draft) return { total: 0, portion: 0 }
    const total = draft.ingredientes.reduce((sum, item) => sum + ingredientCost(item), 0)
      + draft.sub_recetas.reduce((sum, item) => sum + subRecipeCost(item), 0)
    return { total, portion: total / Math.max(Number(draft.pax || 1), 1) }
  }, [draft])
  const foodCostPct = (totals.portion / Math.max(Number(draft?.precio_venta || 0), 1)) * 100

  const updateIngredient = (index, ingredient) => {
    setDraft((current) => ({
      ...current,
      ingredientes: current.ingredientes.map((item, itemIndex) => (itemIndex === index ? ingredient : item)),
    }))
  }

  const removeIngredient = (index) => {
    setDraft((current) => ({
      ...current,
      ingredientes: current.ingredientes.filter((_, itemIndex) => itemIndex !== index),
    }))
  }

  const updateSubRecipe = (index, subRecipe) => {
    setDraft((current) => ({
      ...current,
      sub_recetas: current.sub_recetas.map((item, itemIndex) => (itemIndex === index ? subRecipe : item)),
    }))
  }

  const handleSave = () => {
    if (!draft) return
    saveMutation.mutate({
      ...draft,
      numero_receta: draft.numero_receta || null,
      pax: numberOrFallback(draft.pax, 1),
      peso_porcion_g: optionalNumber(draft.peso_porcion_g),
      tiempo_prep_min: optionalNumber(draft.tiempo_prep_min),
      precio_venta: optionalNumber(draft.precio_venta) || Math.max(Math.round(totals.portion), 1),
      categoria_menu: normalizeCategory(draft.categoria_menu),
      ingredientes: draft.ingredientes.map(serializeIngredient),
      sub_recetas: draft.sub_recetas.map(serializeSubRecipe),
    })
  }

  const handlePhotoChange = (event) => {
    const file = event.target.files?.[0]
    if (!file) return

    if (!file.type.startsWith('image/')) {
      setPhotoError('Selecciona una imagen valida.')
      event.target.value = ''
      return
    }

    const maxSizeMb = 4
    if (file.size > maxSizeMb * 1024 * 1024) {
      setPhotoError(`La imagen no puede pesar mas de ${maxSizeMb} MB.`)
      event.target.value = ''
      return
    }

    const reader = new FileReader()
    reader.onload = () => {
      setDraft((current) => current ? { ...current, imagen_base64: reader.result } : current)
      setPhotoError('')
      event.target.value = ''
    }
    reader.onerror = () => {
      setPhotoError('No se pudo leer la imagen.')
      event.target.value = ''
    }
    reader.readAsDataURL(file)
  }

  const removePhoto = () => {
    setDraft((current) => current ? { ...current, imagen_base64: '' } : current)
    setPhotoError('')
    if (fileInputRef.current) fileInputRef.current.value = ''
  }

  if (!draft) {
    return <div className="recipe-page"><div className="recipe-empty-state">Cargando recetario...</div></div>
  }

  return (
    <div className="recipe-page">
      <aside className="recipe-sidebar">
        <div className="recipe-sidebar__top">
          <button type="button" className="recipe-back-button" onClick={() => navigate('/mesas')} aria-label="Volver">‹</button>
          <div className="recipe-book-mark">R</div>
          <strong>Recetario</strong>
        </div>

        <input
          className="recipe-search"
          value={search}
          placeholder="Buscar receta..."
          onChange={(event) => setSearch(event.target.value)}
        />

        <button
          type="button"
          className="recipe-new-button"
          onClick={() => {
            const newId = Date.now()
            setSelectedId(newId)
            setDraft({ ...normalizeDetail({ id: newId, nombre: 'Nueva receta', ingredientes: [], sub_recetas: [] }, newId), is_new: true })
          }}
        >
          + Nueva receta
        </button>

        <div className="recipe-list">
          {filteredRecetas.map((receta) => (
            <button
              type="button"
              key={receta.id}
              className={`recipe-list-item ${receta.id === selectedId ? 'is-active' : ''}`}
              onClick={() => {
                setDraft(null)
                setSelectedId(receta.id)
              }}
            >
              <span className="recipe-list-icon">□</span>
              <span>
                <strong>{receta.nombre}</strong>
                <small>{receta.categoria_menu || 'Sin categoria'} · {receta.pax || draft.pax || 1} porciones</small>
              </span>
            </button>
          ))}
        </div>

        <div className="recipe-sidebar__footer">
          <span>{recetas.length} recetas en total</span>
          <span>{recetas.filter((receta) => receta.tiene_subrecetas).length} con subrecetas</span>
        </div>
      </aside>

      <main className="recipe-editor">
        <header className="recipe-editor-header">
          <div className="recipe-title-block">
            <span className="recipe-edit-dot">/</span>
            <div>
              <h1>{draft.nombre}</h1>
              <p>Costo total: {money(totals.total)} / {money(totals.portion)} porcion</p>
            </div>
          </div>
          <div className="recipe-actions">
            <button type="button" onClick={() => navigate('/mesas')}>Cancelar</button>
            <button type="button" className="recipe-save-button" onClick={handleSave} disabled={saveMutation.isPending}>
              {saveMutation.isPending ? 'Guardando...' : 'Guardar receta'}
            </button>
          </div>
        </header>

        <section className="recipe-form-grid">
          <div className={`recipe-photo-drop ${draft.imagen_base64 ? 'has-photo' : ''}`}>
            <input
              ref={fileInputRef}
              type="file"
              accept="image/png,image/jpeg,image/jpg,image/webp"
              onChange={handlePhotoChange}
              className="recipe-photo-input"
              aria-label="Seleccionar foto de la receta"
            />
            {draft.imagen_base64 ? (
              <>
                <img src={draft.imagen_base64} alt={draft.nombre || 'Foto de receta'} />
                <div className="recipe-photo-actions">
                  <button type="button" onClick={() => fileInputRef.current?.click()}>
                    Cambiar foto
                  </button>
                  <button type="button" onClick={removePhoto}>
                    Quitar
                  </button>
                </div>
              </>
            ) : (
              <button type="button" className="recipe-photo-empty" onClick={() => fileInputRef.current?.click()}>
                <span>+</span>
                <strong>Subir foto del plato</strong>
                <small>JPG, PNG, WEBP</small>
              </button>
            )}
            {photoError ? <small className="recipe-photo-error">{photoError}</small> : null}
          </div>

          <div className="recipe-main-fields">
            <label className="recipe-field recipe-field--wide">
              <span>Nombre de la receta *</span>
              <input value={draft.nombre} onChange={(event) => setDraft({ ...draft, nombre: event.target.value })} />
            </label>

            <label className="recipe-field">
              <span>Categoria</span>
              <select value={normalizeCategory(draft.categoria_menu)} onChange={(event) => setDraft({ ...draft, categoria_menu: event.target.value })}>
                {categoryOptions.map((category) => (
                  <option key={category.value} value={category.value}>{category.label}</option>
                ))}
              </select>
            </label>

            <label className="recipe-field recipe-field--small">
              <span>Precio venta</span>
              <input type="number" min="1" value={draft.precio_venta} onChange={(event) => setDraft({ ...draft, precio_venta: event.target.value })} />
            </label>

            <label className="recipe-field recipe-field--small">
              <span>Porciones</span>
              <input type="number" min="1" value={draft.pax} onChange={(event) => setDraft({ ...draft, pax: Number(event.target.value) })} />
            </label>

            <label className="recipe-field recipe-field--small">
              <span>Tiempo preparacion</span>
              <input type="number" min="0" value={draft.tiempo_prep_min || 0} onChange={(event) => setDraft({ ...draft, tiempo_prep_min: Number(event.target.value) })} />
            </label>

            <div className="recipe-cost-card">
              <span>Costo total</span>
              <strong>{money(totals.total)}</strong>
            </div>
            <div className="recipe-cost-card recipe-cost-card--portion">
              <span>Costo / porcion</span>
              <strong>{money(totals.portion)}</strong>
            </div>
          </div>
        </section>

        {foodCostPct > 100 ? <div className="recipe-cost-alert"><b>Alerta de costeo:</b> el Food Cost es {foodCostPct.toFixed(1)}%. Revisa las unidades, cantidades y costos unitarios antes de guardar.</div> : null}

        <section className="recipe-panel recipe-panel--ingredients">
          <div className="recipe-panel__header">
            <strong>Ingredientes principales</strong>
          </div>
          <datalist id="recetario-ingredientes">
            {ingredientOptions.map((ingredient) => <option key={ingredient.id} value={ingredient.nombre}>{ingredient.unidad}</option>)}
          </datalist>
          <IngredientRows ingredients={draft.ingredientes} ingredientOptions={ingredientOptions} onChange={updateIngredient} onRemove={removeIngredient} />
          <p className="recipe-catalog-hint">Busca un ingrediente guardado o escribe uno nuevo: se creará al guardar la receta.</p>
          <button type="button" className="recipe-add-button" onClick={() => setDraft({ ...draft, ingredientes: [...draft.ingredientes, emptyIngredient()] })}>
            + Agregar ingrediente
          </button>
        </section>

        <section className="recipe-panel recipe-panel--subs">
          <div className="recipe-panel__header">
            <strong>Subrecetas</strong>
          </div>

          <div className="recipe-sub-list">
            {draft.sub_recetas.map((subRecipe, index) => (
              <div className="recipe-sub-card" key={`${subRecipe.receta_base_id}-${index}`}>
                <div className="recipe-sub-card__top">
                  <input
                    value={subRecipe.nombre || ''}
                    list="recetario-subrecetas"
                    placeholder="Busca o escribe para crear"
                    onChange={(event) => {
                      const nombre = event.target.value
                      const selected = subrecipeOptions.find((option) => option.nombre.toLowerCase() === nombre.trim().toLowerCase())
                      updateSubRecipe(index, selected
                        ? { ...subRecipe, receta_base_id: selected.id, nombre: selected.nombre, ingredientes: [] }
                        : { ...subRecipe, receta_base_id: 0, nombre })
                    }}
                  />
                  <input
                    type="number"
                    min="0"
                    value={subRecipe.cantidad_g || 0}
                    onChange={(event) => updateSubRecipe(index, { ...subRecipe, cantidad_g: Number(event.target.value) })}
                  />
                  <span>g</span>
                  <button
                    type="button"
                    className="recipe-icon-button"
                    onClick={() => setDraft({ ...draft, sub_recetas: draft.sub_recetas.filter((_, itemIndex) => itemIndex !== index) })}
                    aria-label="Quitar subreceta"
                  >
                    x
                  </button>
                </div>
                <IngredientRows
                  ingredients={subRecipe.ingredientes || []}
                  ingredientOptions={ingredientOptions}
                  onChange={(ingredientIndex, ingredient) => updateSubRecipe(index, {
                    ...subRecipe,
                    ingredientes: subRecipe.ingredientes.map((item, itemIndex) => (itemIndex === ingredientIndex ? ingredient : item)),
                  })}
                  onRemove={(ingredientIndex) => updateSubRecipe(index, {
                    ...subRecipe,
                    ingredientes: subRecipe.ingredientes.filter((_, itemIndex) => itemIndex !== ingredientIndex),
                  })}
                />
                <button
                  type="button"
                  className="recipe-add-button recipe-add-button--small"
                  onClick={() => updateSubRecipe(index, { ...subRecipe, ingredientes: [...(subRecipe.ingredientes || []), emptyIngredient()] })}
                >
                  + Agregar ingrediente a subreceta
                </button>
              </div>
            ))}
          </div>

          <datalist id="recetario-subrecetas">
            {subrecipeOptions.map((subrecipe) => <option key={subrecipe.id} value={subrecipe.nombre} />)}
          </datalist>
          <p className="recipe-catalog-hint">Selecciona una subreceta existente o escribe una nueva; se guardará como receta base al guardar.</p>

          <button type="button" className="recipe-add-button recipe-add-button--purple" onClick={() => setDraft({ ...draft, sub_recetas: [...draft.sub_recetas, emptySubRecipe()] })}>
            + Agregar subreceta
          </button>
        </section>

        <section className="recipe-panel recipe-panel--notes">
          <div className="recipe-panel__header">
            <strong>Notas de preparacion</strong>
          </div>
          <textarea placeholder="Instrucciones, tips de presentacion, temperatura, variaciones..." />
        </section>

        {saveMutation.isError ? (
          <div className="recipe-error">No se pudo guardar: {saveMutation.error?.response?.data?.detail || saveMutation.error?.message}</div>
        ) : null}
        {saveMutation.isSuccess ? <div className="recipe-success">Receta guardada.</div> : null}
      </main>
    </div>
  )
}
