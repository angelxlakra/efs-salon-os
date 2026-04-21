"use client"

import * as React from "react"
import { createPortal } from "react-dom"
import { XIcon } from "lucide-react"

import { cn } from "@/lib/utils"

// ─── Scroll lock (nested-safe via counter) ──────────────────
let scrollLockCount = 0
let savedOverflow = ""

function lockScroll() {
  if (scrollLockCount === 0) {
    savedOverflow = document.body.style.overflow
    document.body.style.overflow = "hidden"
  }
  scrollLockCount++
}

function unlockScroll() {
  scrollLockCount = Math.max(0, scrollLockCount - 1)
  if (scrollLockCount === 0) {
    document.body.style.overflow = savedOverflow
  }
}

// ─── Focus trap helpers ─────────────────────────────────────
const FOCUSABLE =
  'a[href], button:not([disabled]), input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])'

// ─── Context ────────────────────────────────────────────────
interface DialogContextValue {
  open: boolean
  onOpenChange: (open: boolean) => void
  titleId: string
  descriptionId: string
}

const DialogContext = React.createContext<DialogContextValue | null>(null)

function useDialog() {
  const ctx = React.useContext(DialogContext)
  if (!ctx) throw new Error("Dialog components must be used within <Dialog>")
  return ctx
}

// ─── Dialog (context provider — renders no DOM) ─────────────
interface DialogProps {
  open?: boolean
  onOpenChange?: (open: boolean) => void
  defaultOpen?: boolean
  modal?: boolean // accepted for API compat, always behaves as modal
  children?: React.ReactNode
}

function Dialog({
  open: controlledOpen,
  onOpenChange,
  defaultOpen = false,
  children,
}: DialogProps) {
  const [uncontrolledOpen, setUncontrolledOpen] = React.useState(defaultOpen)
  const isControlled = controlledOpen !== undefined
  const open = isControlled ? controlledOpen : uncontrolledOpen

  const handleOpenChange = React.useCallback(
    (value: boolean) => {
      if (!isControlled) setUncontrolledOpen(value)
      onOpenChange?.(value)
    },
    [isControlled, onOpenChange]
  )

  const id = React.useId()
  const value = React.useMemo<DialogContextValue>(
    () => ({
      open,
      onOpenChange: handleOpenChange,
      titleId: `dlg-title-${id}`,
      descriptionId: `dlg-desc-${id}`,
    }),
    [open, handleOpenChange, id]
  )

  return <DialogContext.Provider value={value}>{children}</DialogContext.Provider>
}

// ─── DialogTrigger / DialogClose ────────────────────────────
function DialogTrigger({
  children,
  ...props
}: React.ComponentProps<"button">) {
  const { onOpenChange } = useDialog()
  return (
    <button
      type="button"
      data-slot="dialog-trigger"
      onClick={() => onOpenChange(true)}
      {...props}
    >
      {children}
    </button>
  )
}

function DialogClose({
  children,
  ...props
}: React.ComponentProps<"button">) {
  const { onOpenChange } = useDialog()
  return (
    <button
      type="button"
      data-slot="dialog-close"
      onClick={() => onOpenChange(false)}
      {...props}
    >
      {children}
    </button>
  )
}

// ─── No-op exports (portaling & overlay handled inside DialogContent) ──
function DialogOverlay(_props: Record<string, unknown>) {
  return null
}

function DialogPortal(_props: Record<string, unknown>) {
  return null
}

// ─── Size classes (explicit px — immune to Tailwind namespace conflicts) ──
const dialogSizeClasses = {
  sm: "max-w-[384px]",
  default: "max-w-[448px]",
  md: "max-w-[512px]",
  lg: "max-w-[672px]",
  xl: "max-w-[896px]",
  full: "max-w-[calc(100vw-4rem)]",
} as const

type DialogSize = keyof typeof dialogSizeClasses

// ─── DialogContent (the actual modal panel + overlay) ───────
function DialogContent({
  className,
  children,
  showCloseButton = true,
  size = "default",
  style: styleProp,
  ...props
}: React.ComponentProps<"div"> & {
  showCloseButton?: boolean
  size?: DialogSize
}) {
  const { open, onOpenChange, titleId, descriptionId } = useDialog()
  const contentRef = React.useRef<HTMLDivElement>(null)
  const previousFocusRef = React.useRef<Element | null>(null)
  const scrollLockedRef = React.useRef(false)
  const [mounted, setMounted] = React.useState(false)
  const [animState, setAnimState] = React.useState<"open" | "closed">("closed")

  // ── Mount / unmount with exit-animation delay ──
  React.useEffect(() => {
    if (open) {
      previousFocusRef.current = document.activeElement
      setMounted(true)
      // Double-RAF ensures the DOM has painted the initial (closed) frame
      // before we flip to "open" so the CSS entrance animation triggers
      requestAnimationFrame(() => {
        requestAnimationFrame(() => setAnimState("open"))
      })
      if (!scrollLockedRef.current) {
        lockScroll()
        scrollLockedRef.current = true
      }
    } else if (mounted) {
      setAnimState("closed")
      const timer = setTimeout(() => {
        setMounted(false)
        if (scrollLockedRef.current) {
          unlockScroll()
          scrollLockedRef.current = false
        }
        if (previousFocusRef.current instanceof HTMLElement) {
          previousFocusRef.current.focus()
        }
      }, 150)
      return () => clearTimeout(timer)
    }
  }, [open]) // eslint-disable-line react-hooks/exhaustive-deps

  // ── Safety: unlock scroll if component unmounts while open ──
  React.useEffect(() => {
    return () => {
      if (scrollLockedRef.current) {
        unlockScroll()
        scrollLockedRef.current = false
      }
    }
  }, [])

  // ── Auto-focus first focusable element on open ──
  React.useEffect(() => {
    if (!mounted || animState !== "open") return
    const el = contentRef.current
    if (!el) return
    const first = el.querySelector<HTMLElement>(FOCUSABLE)
    if (first) first.focus()
    else el.focus()
  }, [mounted, animState])

  // ── Keyboard: Escape to close + Tab focus trap ──
  const handleKeyDown = React.useCallback(
    (e: React.KeyboardEvent) => {
      if (e.key === "Escape") {
        e.stopPropagation()
        onOpenChange(false)
        return
      }
      if (e.key === "Tab" && contentRef.current) {
        const focusable =
          contentRef.current.querySelectorAll<HTMLElement>(FOCUSABLE)
        if (focusable.length === 0) {
          e.preventDefault()
          return
        }
        const first = focusable[0]
        const last = focusable[focusable.length - 1]
        if (e.shiftKey && document.activeElement === first) {
          e.preventDefault()
          last.focus()
        } else if (!e.shiftKey && document.activeElement === last) {
          e.preventDefault()
          first.focus()
        }
      }
    },
    [onOpenChange]
  )

  if (!mounted) return null

  return createPortal(
    <>
      {/* Overlay */}
      <div
        data-slot="dialog-overlay"
        data-state={animState}
        className="fixed inset-0 z-50 bg-black/50 data-[state=open]:animate-in data-[state=closed]:animate-out data-[state=open]:fade-in-0 data-[state=closed]:fade-out-0"
        onClick={() => onOpenChange(false)}
        aria-hidden="true"
      />
      {/* Panel */}
      <div
        ref={contentRef}
        data-slot="dialog-content"
        data-state={animState}
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
        aria-describedby={descriptionId}
        tabIndex={-1}
        onKeyDown={handleKeyDown}
        className={cn(
          "bg-background fixed top-1/2 left-1/2 z-50 flex flex-col w-[calc(100%-2rem)] rounded-lg border shadow-lg outline-none overflow-hidden",
          dialogSizeClasses[size],
          "data-[state=open]:animate-in data-[state=closed]:animate-out",
          "data-[state=open]:fade-in-0 data-[state=closed]:fade-out-0",
          "data-[state=open]:zoom-in-95 data-[state=closed]:zoom-out-95",
          "duration-200",
          className
        )}
        style={{
          maxHeight: "90dvh",
          transform: "translate(-50%, -50%)",
          ...styleProp,
        }}
        {...props}
      >
        {children}
        {showCloseButton && (
          <button
            type="button"
            data-slot="dialog-close"
            className="ring-offset-background focus:ring-ring absolute top-4 right-4 rounded-xs opacity-70 transition-opacity hover:opacity-100 focus:ring-2 focus:ring-offset-2 focus:outline-hidden disabled:pointer-events-none [&_svg]:pointer-events-none [&_svg]:shrink-0 [&_svg:not([class*='size-'])]:size-4"
            onClick={() => onOpenChange(false)}
            aria-label="Close"
          >
            <XIcon />
            <span className="sr-only">Close</span>
          </button>
        )}
      </div>
    </>,
    document.body
  )
}

// ─── Layout sub-components ──────────────────────────────────
function DialogHeader({ className, ...props }: React.ComponentProps<"div">) {
  return (
    <div
      data-slot="dialog-header"
      className={cn(
        "flex flex-col gap-2 text-center sm:text-left flex-shrink-0 px-4 pt-4 pr-10 sm:px-6 sm:pt-6",
        className
      )}
      {...props}
    />
  )
}

function DialogBody({ className, ...props }: React.ComponentProps<"div">) {
  return (
    <div
      data-slot="dialog-body"
      className={cn("flex-1 overflow-y-auto min-h-0 px-4 py-4 sm:px-6", className)}
      {...props}
    />
  )
}

function DialogFooter({ className, ...props }: React.ComponentProps<"div">) {
  return (
    <div
      data-slot="dialog-footer"
      className={cn(
        "flex flex-col-reverse gap-2 sm:flex-row sm:justify-end flex-shrink-0 px-4 pb-4 pt-4 sm:px-6 sm:pb-6",
        className
      )}
      {...props}
    />
  )
}

function DialogTitle({
  className,
  ...props
}: React.ComponentProps<"h2">) {
  const { titleId } = useDialog()
  return (
    <h2
      id={titleId}
      data-slot="dialog-title"
      className={cn("text-lg leading-none font-semibold", className)}
      {...props}
    />
  )
}

function DialogDescription({
  className,
  ...props
}: React.ComponentProps<"p">) {
  const { descriptionId } = useDialog()
  return (
    <p
      id={descriptionId}
      data-slot="dialog-description"
      className={cn("text-muted-foreground text-sm", className)}
      {...props}
    />
  )
}

export {
  Dialog,
  DialogBody,
  DialogClose,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogOverlay,
  DialogPortal,
  DialogTitle,
  DialogTrigger,
}

export type { DialogProps, DialogSize }
