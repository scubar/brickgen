import { useState } from 'react'
import Modal from './ui/Modal'

/**
 * Generic cache section: card with optional thumbnail, description, and "Manage cache" button
 * that opens a modal with the given children (list, clear options, etc.).
 */
export default function CacheSection({ id, title, description, thumbnailUrl, thumbnailAlt, children }) {
  const [modalOpen, setModalOpen] = useState(false)
  return (
    <div id={id} className="bg-dk-2 rounded-lg border border-dk-3 overflow-hidden">
      <div className="p-4 flex items-start gap-4">
        {thumbnailUrl && (
          <img src={thumbnailUrl} alt={thumbnailAlt || ''} className="w-16 h-16 object-contain bg-dk-1 rounded flex-shrink-0" />
        )}
        <div className="flex-1 min-w-0">
          <h3 className="text-lg font-semibold text-dk-5">{title}</h3>
          <p className="text-sm text-dk-5/80 mt-1">{description}</p>
          <button type="button" onClick={() => setModalOpen(true)} className="mt-3 px-4 py-2 bg-mint text-dk-1 rounded hover:opacity-90 text-sm font-medium">
            Manage cache
          </button>
        </div>
      </div>
      <Modal 
        open={modalOpen} 
        onClose={() => setModalOpen(false)} 
        title={title}
        maxWidth="max-w-2xl"
      >
        {children}
      </Modal>
    </div>
  )
}
