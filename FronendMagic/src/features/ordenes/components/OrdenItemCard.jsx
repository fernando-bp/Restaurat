export default function OrdenItemCard({ item, onDecrease, onIncrease, onRemove }) {
  return (
    <div className="orden-item-card">
      <img src={item.image} alt={item.title} className="orden-item-card__image" />
      <div className="orden-item-card__content">
        <div className="orden-item-card__header">
          <div>
            <h3>{item.title}</h3>
            <p className="orden-item-card__price">${item.price.toFixed(2)} c/u</p>
          </div>
          <button
            type="button"
            className="orden-item-card__remove"
            onClick={() => onRemove(item.dbName)}
            aria-label={`Eliminar ${item.title}`}
          >
            ×
          </button>
        </div>

        <div className="orden-item-card__controls">
          <button type="button" onClick={() => onDecrease(item.dbName)} disabled={item.quantity <= 1}>−</button>
          <span>{item.quantity}</span>
          <button type="button" onClick={() => onIncrease(item.dbName)}>+</button>
        </div>
      </div>
    </div>
  )
}
