export default function Button({ children, variant = 'primary', ...props }) {
  const styles = {
    primary: {
      background: '#7c3aed',
      color: '#fff',
    },
    danger: {
      background: '#dc2626',
      color: '#fff',
    },
    ghost: {
      background: 'transparent',
      color: '#111827',
      border: '1px solid #d1d5db',
    },
  }

  return (
    <button style={{ padding: '10px 14px', borderRadius: 10, border: 'none', cursor: 'pointer', ...styles[variant] }} {...props}>
      {children}
    </button>
  )
}
