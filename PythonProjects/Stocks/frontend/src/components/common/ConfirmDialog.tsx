import { AnimatePresence, motion } from 'framer-motion'
import { cn } from '@/lib/utils'

interface ConfirmDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  title: string
  description: string
  confirmLabel?: string
  cancelLabel?: string
  onConfirm: () => void
  destructive?: boolean
}

export function ConfirmDialog({
  open,
  onOpenChange,
  title,
  description,
  confirmLabel = 'Confirm',
  cancelLabel = 'Cancel',
  onConfirm,
  destructive = false,
}: ConfirmDialogProps) {
  const handleConfirm = () => {
    onConfirm()
    onOpenChange(false)
  }

  const handleCancel = () => {
    onOpenChange(false)
  }

  return (
    <AnimatePresence>
      {open && (
        <>
          {/* Backdrop */}
          <motion.div
            key="backdrop"
            className="fixed inset-0 z-50 bg-black/60"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.15 }}
            onClick={handleCancel}
            aria-hidden="true"
          />

          {/* Dialog panel */}
          <motion.div
            key="dialog"
            role="alertdialog"
            aria-modal="true"
            aria-labelledby="confirm-dialog-title"
            aria-describedby="confirm-dialog-description"
            className="fixed left-1/2 top-1/2 z-50 w-full max-w-md -translate-x-1/2 -translate-y-1/2 px-4"
            initial={{ opacity: 0, scale: 0.96, y: '-48%' }}
            animate={{ opacity: 1, scale: 1, y: '-50%' }}
            exit={{ opacity: 0, scale: 0.96, y: '-48%' }}
            transition={{ duration: 0.15, ease: 'easeOut' }}
          >
            <div className="bg-card border border-border rounded-lg shadow-xl p-6 flex flex-col gap-4">
              {/* Title */}
              <h2
                id="confirm-dialog-title"
                className="text-lg font-semibold text-foreground"
              >
                {title}
              </h2>

              {/* Description */}
              <p
                id="confirm-dialog-description"
                className="text-sm text-muted-foreground"
              >
                {description}
              </p>

              {/* Actions */}
              <div className="flex items-center justify-end gap-3 pt-2">
                {/* Cancel */}
                <button
                  type="button"
                  onClick={handleCancel}
                  className={cn(
                    'px-4 py-2 rounded-md text-sm font-medium transition-colors',
                    'bg-secondary text-secondary-foreground',
                    'hover:bg-secondary/80'
                  )}
                >
                  {cancelLabel}
                </button>

                {/* Confirm */}
                <button
                  type="button"
                  onClick={handleConfirm}
                  className={cn(
                    'px-4 py-2 rounded-md text-sm font-medium transition-colors',
                    destructive
                      ? 'bg-destructive text-destructive-foreground hover:bg-destructive/90'
                      : 'bg-primary text-primary-foreground hover:bg-primary/90'
                  )}
                >
                  {confirmLabel}
                </button>
              </div>
            </div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  )
}
