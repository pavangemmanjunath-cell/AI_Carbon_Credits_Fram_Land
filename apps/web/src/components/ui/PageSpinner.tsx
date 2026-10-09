import { useTranslation } from 'react-i18next';

export function PageSpinner({ label }: { label?: string }) {
  const { t } = useTranslation();
  return (
    <div
      role="status"
      aria-live="polite"
      className="flex min-h-[40vh] w-full items-center justify-center gap-3 text-muted"
    >
      <span
        aria-hidden="true"
        className="h-5 w-5 animate-spin rounded-full border-2 border-line border-t-forest"
      />
      <span className="text-sm">{label ?? t('app.loading')}</span>
    </div>
  );
}
