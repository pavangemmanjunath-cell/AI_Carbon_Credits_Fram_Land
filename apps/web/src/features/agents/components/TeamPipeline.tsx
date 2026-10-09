import { useTranslation } from 'react-i18next';
import { formatDuration, type PipelineRow } from '../logic/agentsLogic';
import type { AgentInfo } from '../types';
import type { AgentNames } from '../useAgentNames';
import { AgentAvatar } from './AgentAvatar';
import { StatusIcon } from './StatusIcon';

interface TeamPipelineProps {
  rows: PipelineRow[];
  planTitle: string;
  selected: string | null;
  onSelect: (agentId: string | null) => void;
  names: AgentNames;
  catalogAgents?: AgentInfo[];
  locale: string;
}

/**
 * The team for the chosen plan, in the order they work. Each row is a toggle: pick an agent to
 * show only its messages in the conversation.
 */
export function TeamPipeline({
  rows,
  planTitle,
  selected,
  onSelect,
  names,
  catalogAgents,
  locale,
}: TeamPipelineProps) {
  const { t } = useTranslation();
  const selectedInfo = selected ? catalogAgents?.find((a) => a.id === selected) : undefined;

  return (
    <section
      aria-label={t('agentsPage.teamTitle')}
      className="card flex flex-col gap-3 p-4 lg:sticky lg:top-4 lg:self-start"
    >
      <div className="flex flex-col gap-0.5">
        <h2 className="m-0 text-[16px]">{t('agentsPage.teamTitle')}</h2>
        <p className="m-0 text-[12.5px] text-muted">
          {planTitle ? `${planTitle} · ` : ''}
          {t('agentsPage.teamHint')}
        </p>
      </div>

      <ul className="m-0 flex list-none gap-2 overflow-x-auto p-0 pb-1 lg:flex-col lg:gap-1 lg:overflow-visible lg:pb-0">
        {rows.map((row, index) => {
          const isSelected = selected === row.agent;
          const duration = formatDuration(row.durationMs, locale);
          const title = names.title(row.agent);
          const role = names.role(row.agent);
          return (
            <li key={row.agent} className="relative shrink-0 lg:shrink">
              {index < rows.length - 1 && (
                <span
                  aria-hidden="true"
                  className="absolute bottom-[-14px] left-[27px] top-[46px] hidden w-px bg-line lg:block"
                />
              )}
              <button
                type="button"
                aria-pressed={isSelected}
                aria-label={`${title}: ${t(`agentsPage.status.${row.status}`)}${duration ? `, ${duration}` : ''}${
                  row.messageCount
                    ? `, ${t('agentsPage.messagesCount', { count: row.messageCount })}`
                    : ''
                }`}
                onClick={() => onSelect(isSelected ? null : row.agent)}
                className={`relative flex w-full items-start gap-2.5 rounded-[10px] border p-2.5 text-left transition-colors ${
                  isSelected ? 'border-forest bg-mint' : 'border-transparent hover:bg-ground'
                }`}
              >
                <AgentAvatar agent={row.agent} size="md" />
                <span className="min-w-0 flex-1">
                  <span className="block whitespace-nowrap text-[14px] font-semibold text-ink lg:whitespace-normal">
                    {title}
                  </span>
                  {role && (
                    <span className="mt-0.5 hidden text-[12.5px] leading-snug text-ink-2 lg:block">
                      {role}
                    </span>
                  )}
                </span>
                <span className="flex flex-col items-end gap-1 pt-0.5">
                  <StatusIcon status={row.status} />
                  {duration && <span className="font-mono text-[11px] text-muted">{duration}</span>}
                </span>
              </button>
            </li>
          );
        })}
      </ul>

      {selectedInfo && (
        <div className="flex flex-col gap-1.5 rounded-[10px] bg-ground p-3 text-[12.5px] leading-snug text-ink-2">
          {selectedInfo.says && (
            <p className="m-0">
              <strong className="font-semibold text-ink">{t('agentsPage.agentSays')}:</strong>{' '}
              {selectedInfo.says}
            </p>
          )}
          {selectedInfo.tools.length > 0 && (
            <p className="m-0">
              <strong className="font-semibold text-ink">{t('agentsPage.agentTools')}:</strong>{' '}
              <span className="font-mono text-[12px]">
                {selectedInfo.tools.map((tool) => tool.name).join(', ')}
              </span>
            </p>
          )}
        </div>
      )}
    </section>
  );
}
