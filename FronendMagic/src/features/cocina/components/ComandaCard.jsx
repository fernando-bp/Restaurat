export default function ComandaCard({ orden }) {
  return (
    <div style={{ border: '1px solid #e5e7eb', borderRadius: 12, padding: 16 }}>
      <h2>Comanda mesa {orden.mesa_id}</h2>
      <div>{orden.comanda_ticket}</div>
    </div>
  )
}
