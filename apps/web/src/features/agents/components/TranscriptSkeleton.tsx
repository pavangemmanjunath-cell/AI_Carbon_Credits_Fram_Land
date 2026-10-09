import { useTranslation } from 'react-i18next';
import { AgentAvatar } from './AgentAvatar';

/** Placeholder bubbles that appear one after another while the agents work. */
export function TranscriptSkeleton({ agents }: { agents: string[] }) {
  const { t } = useTranslation();
  const shown = agents.slice(0, 3);
  return (
    <div role="status" aria-live="polite" className="flex flex-col gap-4">
      <p className="m-0 text-[13px] text-muted">{t('agentsPage.running')}</p>
      {shown.map((agent, index) => (
        <div
          key={agent}
          aria-hidden="true"
          style={{ transitionDelay: `${index * 250}ms` }}
          className="flex gap-3 transition duration-500 starting:translate-y-1 starting:opacity-0"
        >
          <AgentAvatar agent={agent} size="md" className="opacity-60" />
          <div className="flex flex-1 flex-col gap-2">
            <span className="skeleton h-3.5 w-28" />
            <span className="skeleton h-16 w-full rounded-[12px]" />
          </div>
        </div>
      ))}
    </div>
  );
}
