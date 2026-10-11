import { useTranslation } from 'react-i18next';
import { WifiOff } from 'lucide-react';
import { useUiStore } from '@/store/uiStore';

export function OfflineBanner() {
  const { t } = useTranslation();
  const apiStatus = useUiStore((s) => s.apiStatus);
  const dismissed = useUiStore((s) => s.offlineBannerDismissed);
  const dismiss = useUiStore((s) => s.dismissOfflineBanner);
  if (apiStatus !== 'offline' || dismissed) return null;
  return (
    <div
      role="status"
      className="flex items-center gap-3 border-b border-amber-tint bg-amber-tint px-4 py-2 text-[13px] text-amber-text"
    >
      <WifiOff size={16} aria-hidden="true" />
      <span className="flex-1">{t('banner.offline')}</span>
      <button
        type="button"
        onClick={dismiss}
        className="font-semibold underline-offset-2 hover:underline"
      >
        {t('banner.dismiss')}
      </button>
    </div>
  );
}
