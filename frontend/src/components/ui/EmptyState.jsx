/**
 * Reusable EmptyState component for no-data messages with optional action button
 */
export default function EmptyState({ message, action }) {
  return (
    <div className="text-center py-8 text-dk-5">
      <p className="mb-4">{message}</p>
      {action && <div>{action}</div>}
    </div>
  )
}
