import {
  ArrowRight,
  CircleCheck,
  CircleMinus,
  CircleX,
  ExternalLink,
  Flag,
  ListChecks,
  MessageCircle,
  Search,
  TriangleAlert,
  Wrench,
  type LucideIcon,
} from 'lucide-react';
import { useTranslation } from 'react-i18next';
import {
  factChips,
  formatClock,
  formatDuration,
  humanizeKey,
  kindStyle,
  recipientAgentId,
  safeHttpUrl,
  summarizeRecord,
  type KindIconKey,
} from '../logic/agentsLogic';
import type { AgentNames } from '../useAgentNames';
import type { AgentMessage, AgentToolCall, ToolCallStatus } from '../types';
import { AgentAvatar } from './AgentAvatar';
import { Badge } from './Badge';
import { Disclosure } from './Disclosure';

const KIND_ICONS: Record<KindIconKey, LucideIcon> = {
  plan: ListChecks,
  finding: Search,
  warning: TriangleAlert,
  handoff: ArrowRight,
  answer: MessageCircle,
  summary: Flag,
};

const BUBBLE_STYLES: Record<string, string> = {
  plan: 'border-line bg-ground',
  warning: 'border-amber-text/30 bg-amber-tint',
  handoff: 'border-dashed border-line bg-ground',
  answer: 'border-forest/40 bg-mint',
};

const TOOL_STATUS: Record<ToolCallStatus, { icon: LucideIcon; className: string }> = {
  ok: { icon: CircleCheck, className: 'text-forest' },
  error: { icon: CircleX, className: 'text-rose-700' },
  skipped: { icon: CircleMinus, className: 'text-muted' },
};

function ToolCallRow({ call, locale }: { call: AgentToolCall; locale: string }) {
  const { t } = useTranslation();
  const status = TOOL_STATUS[call.status] ?? TOOL_STATUS.ok;
  const StatusGlyph = status.icon;
  const input = summarizeRecord(call.input);
  const output = summarizeRecord(call.output);
  const duration = formatDuration(call.duration_ms, locale);
  return (
    <li className="rounded-[10px] border border-line bg-ground px-3 py-2">
      <div className="flex flex-wrap items-center gap-x-2.5 gap-y-1">
        <Wrench size={13} aria-hidden="true" className="text-muted" />
        <code className="font-mono text-[12.5px] font-medium text-ink">{call.tool}</code>
        <span
          className={`inline-flex items-center gap-1 text-[12px] font-semibold ${status.className}`}
        >
          <StatusGlyph size={13} aria-hidden="true" />
          {t(`agentsPage.toolStatus.${call.status}`, { defaultValue: call.status })}
        </span>
        {duration && <span className="font-mono text-[11px] text-muted">{duration}</span>}
      </div>
      {input && (
        <p className="m-0 mt-1.5 break-words font-mono text-[12px] leading-snug text-ink-2">
          <span className="text-muted">{t('agentsPage.toolInput')} </span>
          {input}
        </p>
      )}
      {output && (
        <p className="m-0 mt-1 break-words font-mono text-[12px] leading-snug text-ink-2">
          <span className="text-muted">{t('agentsPage.toolOutput')} </span>
          {output}
        </p>
      )}
    </li>
  );
}

function HowIKnow({ message, locale }: { message: AgentMessage; locale: string }) {
  const { t } = useTranslation();
  const tools = message.tool_calls;
  const evidence = message.evidence;
  if (tools.length === 0 && evidence.length === 0 && !message.confidence) return null;

  const meta = [
    tools.length > 0 ? t('agentsPage.toolsCount', { count: tools.length }) : null,
    evidence.length > 0 ? t('agentsPage.sourcesCount', { count: evidence.length }) : null,
  ]
    .filter(Boolean)
    .join(' · ');

  return (
    <Disclosure
      label={t('agentsPage.howIKnow')}
      meta={meta ? `(${meta})` : undefined}
      className="mt-2.5"
    >
      <div className="flex flex-col gap-3 border-t border-line pt-3">
        {tools.length > 0 && (
          <div className="flex flex-col gap-1.5">
            <span className="eyebrow">{t('agentsPage.toolsUsed')}</span>
            <ul className="m-0 flex list-none flex-col gap-1.5 p-0">
              {tools.map((call, index) => (
                <ToolCallRow key={`${call.tool}-${index}`} call={call} locale={locale} />
              ))}
            </ul>
          </div>
        )}
        {evidence.length > 0 && (
          <div className="flex flex-col gap-1.5">
            <span className="eyebrow">{t('agentsPage.sources')}</span>
            <ul className="m-0 flex list-none flex-col gap-1 p-0">
              {evidence.map((item, index) => {
                const href = safeHttpUrl(item.url);
                return (
                  <li key={`${item.label}-${index}`} className="text-[13px]">
                    {href ? (
                      <a
                        href={href}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="inline-flex items-center gap-1 font-medium text-forest underline-offset-2 hover:underline"
                      >
                        {item.label}
                        <ExternalLink size={12} aria-hidden="true" />
                        <span className="sr-only">{t('agentsPage.opensNewTab')}</span>
                      </a>
                    ) : (
                      <span className="text-ink">{item.label}</span>
                    )}
                    {item.source && (
                      <span className="ml-2 font-mono text-[11px] text-muted">{item.source}</span>
                    )}
                  </li>
                );
              })}
            </ul>
          </div>
        )}
        {message.confidence && (
          <p className="m-0 text-[13px] text-ink-2">
            {t('agentsPage.confidenceLabel')}:{' '}
            <strong className="font-semibold text-ink">
              {t(`agentsPage.confidenceLevel.${message.confidence}`, {
                defaultValue: message.confidence,
              })}
            </strong>
          </p>
        )}
      </div>
    </Disclosure>
  );
}

function FactChips({ message, locale }: { message: AgentMessage; locale: string }) {
  const { t } = useTranslation();
  const { chips, hidden } = factChips(message.facts, locale, 6, {
    yes: t('agentsPage.yes'),
    no: t('agentsPage.no'),
  });
  if (chips.length === 0) return null;
  return (
    <ul
      className="m-0 mt-2.5 flex list-none flex-wrap gap-1.5 p-0"
      aria-label={t('agentsPage.facts.title')}
    >
      {chips.map((chip) => (
        <li
          key={chip.key}
          className="inline-flex items-baseline gap-1.5 rounded-full bg-ground px-2.5 py-1 text-[12px]"
        >
          <span className="text-muted">
            {t(`agentsPage.facts.${chip.base}`, { defaultValue: humanizeKey(chip.base) })}
          </span>
          <span className="font-mono font-medium text-ink">{chip.value}</span>
        </li>
      ))}
      {hidden > 0 && (
        <li className="inline-flex items-center rounded-full px-2 py-1 text-[12px] text-muted">
          {t('agentsPage.moreFacts', { count: hidden })}
        </li>
      )}
    </ul>
  );
}

interface MessageBubbleProps {
  message: AgentMessage;
  names: AgentNames;
  locale: string;
  /** Position in the transcript; only used to stagger the entrance animation. */
  index?: number;
}

/** One message: who said it, what kind it is, the text, a few facts, and how they know. */
export function MessageBubble({ message, names, locale, index = 0 }: MessageBubbleProps) {
  const { t } = useTranslation();
  const title = names.title(message.agent);
  const style = kindStyle(message.kind);
  const KindIcon = KIND_ICONS[style.icon];
  const kindLabel = t(`agentsPage.kind.${message.kind}`, {
    defaultValue: humanizeKey(message.kind),
  });
  const recipient = recipientAgentId(message.to);
  const clock = formatClock(message.created_at, locale);
  const compact = message.kind === 'handoff';

  return (
    <article
      aria-label={`${title} — ${kindLabel}`}
      style={{ transitionDelay: `${Math.min(index, 8) * 50}ms` }}
      className="flex gap-3 transition duration-300 starting:translate-y-1 starting:opacity-0"
    >
      <AgentAvatar agent={message.agent} size="md" className="mt-0.5" />
      <div className="min-w-0 flex-1">
        <header className="flex flex-wrap items-center gap-x-2 gap-y-1">
          <span className="text-[14px] font-semibold text-ink">{title}</span>
          <Badge tone={style.tone}>
            <KindIcon size={12} aria-hidden="true" />
            {kindLabel}
          </Badge>
          {recipient && (
            <span className="inline-flex items-center gap-1 text-[12.5px] font-medium text-ink-2">
              <span className="sr-only">{t('agentsPage.to')}</span>
              <span aria-hidden="true">→</span> {names.title(recipient)}
            </span>
          )}
          {clock && (
            <time
              dateTime={message.created_at}
              className="ml-auto font-mono text-[11px] text-muted"
            >
              {clock}
            </time>
          )}
        </header>
        <div
          className={`mt-1.5 rounded-[12px] rounded-tl-[4px] border px-4 py-3 ${BUBBLE_STYLES[message.kind] ?? 'border-line bg-surface'}`}
        >
          <p
            className={`m-0 whitespace-pre-line leading-relaxed text-ink ${compact ? 'text-[14px] text-ink-2' : 'text-[15px]'}`}
          >
            {message.text}
          </p>
          <FactChips message={message} locale={locale} />
          <HowIKnow message={message} locale={locale} />
        </div>
      </div>
    </article>
  );
}
