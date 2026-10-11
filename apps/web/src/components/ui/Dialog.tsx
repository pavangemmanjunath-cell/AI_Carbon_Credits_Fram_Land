import { useEffect, useRef, type ReactNode } from 'react';
import { X } from 'lucide-react';
import { useTranslation } from 'react-i18next';

interface DialogProps {
  open: boolean;
  title: string;
  onClose: () => void;
  children: ReactNode;
  /** `lg` is used by the Import dialog; `md` (default) keeps the original width. */
  size?: 'md' | 'lg';
  /** Sticky footer (buttons), separated from the body by a line. */
  footer?: ReactNode;
}

/** Native <dialog>-based modal: focus trapping and Escape handling come for free. */
export function Dialog({ open, title, onClose, children, size = 'md', footer }: DialogProps) {
  const ref = useRef<HTMLDialogElement>(null);
  const { t } = useTranslation();

  useEffect(() => {
    const node = ref.current;
    if (!node) return;
    if (open && !node.open) node.showModal();
    if (!open && node.open) node.close();
  }, [open]);

  const width = size === 'lg' ? 'w-[min(680px,94vw)]' : 'w-[min(560px,92vw)]';
  return (
    <dialog
      ref={ref}
      onClose={onClose}
      onClick={(event) => {
        if (event.target === ref.current) onClose();
      }}
      className={`m-auto max-h-[92vh] ${width} rounded-[14px] border border-line bg-surface p-0 text-ink shadow-float backdrop:bg-[rgba(20,33,26,0.45)]`}
    >
      <div className="flex max-h-[92vh] flex-col">
        <div className="flex items-center justify-between border-b border-line px-5 py-4">
          <h2 className="text-[17px]">{title}</h2>
          <button
            type="button"
            onClick={onClose}
            aria-label={t('app.close')}
            className="flex h-9 w-9 items-center justify-center rounded-full hover:bg-ground"
          >
            <X size={18} />
          </button>
        </div>
        <div className="min-h-0 flex-1 overflow-y-auto px-5 py-4">{children}</div>
        {footer && (
          <div className="flex flex-wrap items-center justify-end gap-2 border-t border-line px-5 py-3.5">
            {footer}
          </div>
        )}
      </div>
    </dialog>
  );
}
