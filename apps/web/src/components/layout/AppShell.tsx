import { lazy, Suspense, useEffect, useState } from 'react';
import { CloudUpload, Menu, UserRound, X } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { Link, Outlet, useLocation } from 'react-router';
import { LogoMark, Wordmark } from '@/components/brand/Logo';
import { LanguageSelect } from '@/components/ui/LanguageSelect';
import { OfflineBanner } from '@/components/ui/OfflineBanner';
import { useUiStore } from '@/store/uiStore';
import { Stepper, type StepKey } from './Stepper';
import { SideNav } from './SideNav';

const ImportDialog = lazy(() =>
  import('@/components/import/ImportDialog').then((m) => ({ default: m.ImportDialog })),
);

function stepForPath(pathname: string): { current: StepKey; completed: StepKey[] } {
  if (
    pathname.includes('/results') ||
    pathname.includes('/report') ||
    pathname.includes('/simulate')
  ) {
    return { current: 'carbonPotential', completed: ['selectLand', 'addTrees', 'analyze'] };
  }
  if (pathname.startsWith('/app/data')) return { current: 'selectLand', completed: [] };
  if (pathname.startsWith('/app/agents') || pathname.startsWith('/app/tree-age'))
    return { current: 'analyze', completed: ['selectLand', 'addTrees'] };
  return { current: 'addTrees', completed: ['selectLand'] };
}

export function AppShell() {
  const { t } = useTranslation();
  const location = useLocation();
  const [navOpen, setNavOpen] = useState(false);
  const importOpen = useUiStore((s) => s.importOpen);
  const setImportOpen = useUiStore((s) => s.setImportOpen);
  const step = stepForPath(location.pathname);
  // A new page starts at the top (e.g. "Simulate this land" from the bottom of the workspace).
  useEffect(() => {
    window.scrollTo(0, 0);
  }, [location.pathname]);

  return (
    <div className="flex min-h-screen flex-col bg-ground text-ink">
      <a
        href="#main"
        className="sr-only focus:not-sr-only focus:absolute focus:left-2 focus:top-2 focus:z-50 focus:rounded-md focus:bg-surface focus:px-3 focus:py-2"
      >
        {t('app.skipToContent')}
      </a>
      <OfflineBanner />
      <header className="flex items-center gap-2.5 border-b border-line bg-surface px-3 py-2 lg:gap-5 lg:px-5">
        <button
          type="button"
          className="flex h-10 w-10 shrink-0 items-center justify-center rounded-[10px] border border-line lg:hidden"
          aria-label={t('app.menu')}
          aria-expanded={navOpen}
          onClick={() => setNavOpen((v) => !v)}
        >
          {navOpen ? <X size={18} /> : <Menu size={18} />}
        </button>
        <Link to="/" className="flex shrink-0 items-center gap-2.5 no-underline">
          <LogoMark size={34} />
          <span className="hidden md:block">
            <Wordmark />
          </span>
        </Link>
        <div className="hidden min-w-0 flex-1 md:block">
          <Stepper current={step.current} completed={step.completed} />
        </div>
        <div className="ml-auto flex shrink-0 items-center gap-2">
          <button
            type="button"
            onClick={() => setImportOpen(true)}
            aria-label={t('nav.importData')}
            title={t('nav.importData')}
            className="inline-flex h-9 items-center justify-center gap-2 rounded-[10px] bg-forest px-2.5 text-[13px] font-semibold text-white transition-colors hover:bg-forest-deep lg:px-3.5"
          >
            <CloudUpload size={17} aria-hidden="true" />
            <span className="hidden lg:inline">{t('nav.import')}</span>
          </button>
          <LanguageSelect compact />
          {/* No sign-in in this release: the profile button opens Settings (language, units, imagery, privacy). */}
          <Link
            to="/app/settings"
            aria-label={t('app.account')}
            title={t('nav.settings')}
            className="flex h-9 w-9 items-center justify-center rounded-full border border-line bg-ground hover:border-forest"
          >
            <UserRound size={17} className="text-ink-2" aria-hidden="true" />
          </Link>
        </div>
      </header>
      <div className="flex flex-1">
        <aside className="hidden w-[208px] shrink-0 border-r border-line bg-surface lg:block">
          <SideNav />
        </aside>
        {navOpen && (
          <div className="fixed inset-0 z-40 flex lg:hidden">
            <div className="h-full w-[260px] overflow-y-auto bg-surface shadow-float">
              <SideNav onNavigate={() => setNavOpen(false)} />
            </div>
            <button
              type="button"
              aria-label={t('app.close')}
              className="flex-1 bg-[rgba(20,33,26,0.4)]"
              onClick={() => setNavOpen(false)}
            />
          </div>
        )}
        <main id="main" className="min-w-0 flex-1">
          <Outlet />
        </main>
      </div>
      {importOpen && (
        <Suspense fallback={null}>
          <ImportDialog onClose={() => setImportOpen(false)} />
        </Suspense>
      )}
    </div>
  );
}
