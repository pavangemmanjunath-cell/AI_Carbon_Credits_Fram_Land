import { CircleAlert, WifiOff } from 'lucide-react';
import { Trans, useTranslation } from 'react-i18next';
import { Button } from '@/components/ui/Button';
import { ApiError, isUnreachable } from '@/services/api';

interface ErrorNoticeProps {
  error: unknown;
  onRetry?: () => void;
}

/**
 * Two kinds of trouble, two messages: the API is not running (friendly, with the command to
 * start it) or the API answered with an RFC 7807 problem (its title and detail, as written).
 */
export function ErrorNotice({ error, onRetry }: ErrorNoticeProps) {
  const { t } = useTranslation();

  if (isUnreachable(error)) {
    return (
      <div
        role="alert"
        className="flex items-start gap-3 rounded-[12px] bg-amber-tint p-4 text-amber-text"
      >
        <WifiOff size={20} aria-hidden="true" className="mt-0.5 shrink-0" />
        <div className="flex min-w-0 flex-1 flex-col gap-1">
          <p className="m-0 text-[14.5px] font-semibold">{t('treeAge.offlineTitle')}</p>
          <p className="m-0 text-[13.5px] leading-relaxed">
            <Trans
              i18nKey="treeAge.offlineBody"
              components={{
                code: (
                  <code className="rounded bg-white/70 px-1.5 py-0.5 font-mono text-[12.5px]" />
                ),
              }}
            />
          </p>
        </div>
        {onRetry && (
          <Button size="sm" variant="secondary" onClick={onRetry}>
            {t('treeAge.retry')}
          </Button>
        )}
      </div>
    );
  }

  const problem = error instanceof ApiError ? error : null;
  const title = problem?.title ?? t('treeAge.errorTitle');
  const detail = problem?.detail ?? (error instanceof Error ? error.message : '');
  return (
    <div
      role="alert"
      className="flex items-start gap-3 rounded-[12px] bg-rose-50 p-4 text-rose-900"
    >
      <CircleAlert size={20} aria-hidden="true" className="mt-0.5 shrink-0" />
      <div className="flex min-w-0 flex-1 flex-col gap-1">
        <p className="m-0 text-[14.5px] font-semibold">{title}</p>
        {detail && <p className="m-0 break-words text-[13.5px] leading-relaxed">{detail}</p>}
        {problem && <p className="m-0 font-mono text-[11.5px] opacity-80">HTTP {problem.status}</p>}
      </div>
      {onRetry && (
        <Button size="sm" variant="secondary" onClick={onRetry}>
          {t('treeAge.retry')}
        </Button>
      )}
    </div>
  );
}
