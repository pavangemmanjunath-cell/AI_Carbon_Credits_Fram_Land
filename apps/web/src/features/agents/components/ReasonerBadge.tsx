import { Cpu, Sparkles } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { InfoButton } from '@/components/ui/InfoButton';
import { Badge } from './Badge';

interface ReasonerBadgeProps {
  llm: boolean;
  provider?: string | null;
}

/** "Deterministic · LLM off" (or "LLM narration on") with the privacy promise as a tip. */
export function ReasonerBadge({ llm, provider }: ReasonerBadgeProps) {
  const { t } = useTranslation();
  return (
    <span className="inline-flex items-center gap-2">
      <Badge tone={llm ? 'amber' : 'mint'} size="md">
        {llm ? <Sparkles size={13} aria-hidden="true" /> : <Cpu size={13} aria-hidden="true" />}
        {llm
          ? `${t('agentsPage.reasonerOn')}${provider ? ` · ${provider}` : ''}`
          : t('agentsPage.reasonerOff')}
      </Badge>
      <InfoButton label={t('agentsPage.reasonerInfoLabel')} text={t('agentsPage.reasonerInfo')} />
    </span>
  );
}
