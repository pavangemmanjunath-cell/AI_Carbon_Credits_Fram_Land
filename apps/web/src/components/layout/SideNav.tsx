import { ShieldCheck } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { Link, useLocation } from 'react-router';
import { NAV_GROUPS, isNavItemActive } from './navItems';

/** Trimble-style left navigation: icon + label, grouped, settings and the privacy note at the bottom. */
export function SideNav({ onNavigate }: { onNavigate?: () => void }) {
  const { t } = useTranslation();
  const { pathname } = useLocation();
  const mainGroups = NAV_GROUPS.filter((g) => g.key !== 'system');
  const systemGroup = NAV_GROUPS.find((g) => g.key === 'system');

  const renderItems = (items: (typeof NAV_GROUPS)[number]['items']) =>
    items.map((item) => {
      const active = isNavItemActive(item, pathname);
      const Icon = item.icon;
      return (
        <li key={item.key}>
          <Link
            to={item.to}
            onClick={onNavigate}
            aria-current={active ? 'page' : undefined}
            className={`flex h-10 items-center gap-2.5 rounded-[10px] px-3 text-sm no-underline transition-colors ${
              active ? 'bg-mint font-semibold text-forest-deep' : 'text-ink-2 hover:bg-ground'
            }`}
          >
            <Icon size={18} aria-hidden="true" className={active ? 'text-forest' : 'text-muted'} />
            {t(`nav.${item.key}`)}
          </Link>
        </li>
      );
    });

  return (
    <nav aria-label={t('nav.sections')} className="flex h-full flex-col gap-3 p-2.5">
      {mainGroups.map((group) => (
        <div key={group.key} className="flex flex-col gap-1">
          <span className="px-3 pb-0.5 pt-1 text-[11px] font-semibold uppercase tracking-wider text-muted">{t(`nav.group_${group.key}`)}</span>
          <ul className="m-0 flex list-none flex-col gap-0.5 p-0">{renderItems(group.items)}</ul>
        </div>
      ))}
      <div className="mt-auto flex flex-col gap-2.5">
        {systemGroup && <ul className="m-0 flex list-none flex-col gap-0.5 border-t border-line p-0 pt-2.5">{renderItems(systemGroup.items)}</ul>}
        <div className="rounded-[10px] border border-line bg-ground p-3 text-[12px] leading-relaxed text-ink-2">
          <strong className="flex items-center gap-1.5 text-ink">
            <ShieldCheck size={14} className="text-forest" aria-hidden="true" />
            {t('nav.privateByDefault')}
          </strong>
          {t('nav.privateByDefaultNote')}
        </div>
      </div>
    </nav>
  );
}
