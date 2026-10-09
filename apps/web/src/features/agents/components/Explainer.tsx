import {
  BookOpen,
  ExternalLink,
  ListOrdered,
  ShieldCheck,
  UserRoundCog,
  Wrench,
  type LucideIcon,
} from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { LinkButton } from '@/components/ui/Button';
import { AGENTS_DOCS_URL } from '../logic/agentsLogic';
import { Disclosure } from './Disclosure';

const ITEMS: { key: 'agent' | 'tool' | 'plan' | 'guardrail'; icon: LucideIcon }[] = [
  { key: 'agent', icon: UserRoundCog },
  { key: 'tool', icon: Wrench },
  { key: 'plan', icon: ListOrdered },
  { key: 'guardrail', icon: ShieldCheck },
];

/** Plain-language answers to "what is an agent, a tool, a plan, a guardrail?" — collapsed by default. */
export function Explainer() {
  const { t } = useTranslation();
  return (
    <section className="card p-5" aria-label={t('agentsPage.explainerTitle')}>
      <Disclosure
        label={
          <span className="inline-flex items-center gap-2 text-[15px]">
            <BookOpen size={17} aria-hidden="true" />
            {t('agentsPage.explainerTitle')}
          </span>
        }
      >
        <div className="flex flex-col gap-4">
          <dl className="m-0 grid grid-cols-1 gap-x-8 gap-y-4 md:grid-cols-2">
            {ITEMS.map(({ key, icon: Icon }) => (
              <div key={key} className="flex gap-3">
                <span className="grid h-9 w-9 shrink-0 place-items-center rounded-full bg-mint text-forest-deep">
                  <Icon size={17} aria-hidden="true" />
                </span>
                <div>
                  <dt className="text-[14px] font-semibold text-ink">
                    {t(`agentsPage.explainer.${key}.term`)}
                  </dt>
                  <dd className="m-0 mt-0.5 text-[13.5px] leading-relaxed text-ink-2">
                    {t(`agentsPage.explainer.${key}.text`)}
                  </dd>
                </div>
              </div>
            ))}
          </dl>
          <div>
            <LinkButton to={AGENTS_DOCS_URL} external variant="secondary" size="sm">
              {t('agentsPage.explainerDocs')}
              <ExternalLink size={14} aria-hidden="true" />
            </LinkButton>
          </div>
        </div>
      </Disclosure>
    </section>
  );
}
