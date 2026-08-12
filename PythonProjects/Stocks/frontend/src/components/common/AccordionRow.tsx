import { useState } from 'react'
import { AnimatePresence, motion } from 'framer-motion'
import { ChevronDown } from 'lucide-react'
import { cn } from '@/lib/utils'

interface AccordionRowProps {
  header: React.ReactNode
  children: React.ReactNode
  /** Default: false */
  defaultOpen?: boolean
  className?: string
}

const accordionVariants = {
  open: { height: 'auto', opacity: 1 },
  closed: { height: 0, opacity: 0 },
}

const accordionTransition = { duration: 0.25, ease: 'easeInOut' as const }

export function AccordionRow({ header, children, defaultOpen, className }: AccordionRowProps) {
  const [isOpen, setIsOpen] = useState(defaultOpen ?? false)

  return (
    <div className={cn('w-full', className)}>
      <button
        type="button"
        onClick={() => setIsOpen((prev) => !prev)}
        className="w-full flex items-center justify-between gap-2 px-4 py-3 text-left focus:outline-none focus-visible:ring-2 focus-visible:ring-indigo-500"
        aria-expanded={isOpen}
      >
        <span className="flex-1">{header}</span>
        <motion.span
          animate={{ rotate: isOpen ? 180 : 0 }}
          transition={accordionTransition}
          className="flex-shrink-0 text-slate-400"
        >
          <ChevronDown size={16} />
        </motion.span>
      </button>

      <AnimatePresence initial={false}>
        {isOpen && (
          <motion.div
            key="accordion-content"
            variants={accordionVariants}
            initial="closed"
            animate="open"
            exit="closed"
            transition={accordionTransition}
            className="overflow-hidden"
            data-testid="accordion-content"
          >
            {children}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}
