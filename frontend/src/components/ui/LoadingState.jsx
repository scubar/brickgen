/**
 * Reusable LoadingState component for centered loading messages
 */
export default function LoadingState({ message = 'Loading...' }) {
  return (
    <div className="text-center py-8 text-dk-5">
      {message}
    </div>
  )
}
