import * as Dialog from '@radix-ui/react-dialog';
import { X } from 'lucide-react';
import type { ReactNode } from 'react';
import { Button } from './Button';

interface SheetProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  title: string;
  description?: string;
  children: ReactNode;
}

/** Bottom sheet (Radix Dialog): foco atrapado, Esc para cerrar, aria correcto. */
export function Sheet({ open, onOpenChange, title, description, children }: SheetProps) {
  return (
    <Dialog.Root open={open} onOpenChange={onOpenChange}>
      <Dialog.Portal>
        <Dialog.Overlay className="animate-fade-in fixed inset-0 z-40 bg-ink/45" />
        <Dialog.Content
          aria-describedby={description ? undefined : undefined}
          className="animate-sheet-up fixed bottom-0 left-1/2 z-50 flex max-h-[92dvh] w-full max-w-[480px] -translate-x-1/2 flex-col rounded-t-[24px] bg-surface shadow-xl"
        >
          <div className="flex items-center justify-between gap-3 px-5 pb-2 pt-4">
            <Dialog.Title className="font-display text-xl font-bold">{title}</Dialog.Title>
            <Dialog.Close
              aria-label="Cerrar"
              className="flex h-11 w-11 items-center justify-center rounded-ctl2 bg-bg text-ink hover:bg-line-soft"
            >
              <X size={20} aria-hidden="true" />
            </Dialog.Close>
          </div>
          {description ? (
            <Dialog.Description className="px-5 pb-2 text-sm text-muted">{description}</Dialog.Description>
          ) : (
            <Dialog.Description className="sr-only">{title}</Dialog.Description>
          )}
          <div className="overflow-y-auto px-5 pb-6 pt-2 pb-safe">{children}</div>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}

interface ConfirmProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  title: string;
  message: string;
  confirmLabel?: string;
  loading?: boolean;
  error?: string | null;
  onConfirm: () => void;
}

export function ConfirmSheet({ open, onOpenChange, title, message, confirmLabel = 'Eliminar', loading, error, onConfirm }: ConfirmProps) {
  return (
    <Sheet open={open} onOpenChange={onOpenChange} title={title} description={message}>
      <div className="flex flex-col gap-3 pt-2">
        {error && (
          <p role="alert" className="rounded-ctl bg-expense-tint px-3 py-2 text-sm text-danger-ink">
            {error}
          </p>
        )}
        <Button variant="danger" block loading={loading} onClick={onConfirm}>
          {confirmLabel}
        </Button>
        <Button variant="secondary" block onClick={() => onOpenChange(false)}>
          Cancelar
        </Button>
      </div>
    </Sheet>
  );
}
