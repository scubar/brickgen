/**
 * ConfirmDialog - Modal confirmation dialog
 */
function ConfirmDialog({ 
  isOpen,
  title,
  message,
  confirmText = 'Yes',
  cancelText = 'No',
  onConfirm,
  onCancel 
}) {
  if (!isOpen) return null

  return (
    <>
      <div className="fixed inset-0 bg-black/50 z-[70]" onClick={onCancel} />
      <div className="fixed top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2 z-[80] w-full max-w-md px-4">
        <div className="bg-dk-2 rounded-lg shadow-2xl border border-dk-3 p-6">
          <h3 className="text-xl font-bold text-dk-5 mb-3">{title}</h3>
          <p className="text-dk-5/90 mb-6">{message}</p>
          <div className="flex gap-3 justify-end">
            <button
              onClick={onCancel}
              className="px-4 py-2 bg-dk-3 text-dk-5 rounded-lg hover:bg-dk-3/80 transition"
            >
              {cancelText}
            </button>
            <button
              onClick={onConfirm}
              className="px-4 py-2 bg-danger text-white rounded-lg hover:opacity-90 transition"
            >
              {confirmText}
            </button>
          </div>
        </div>
      </div>
    </>
  )
}

export default ConfirmDialog
