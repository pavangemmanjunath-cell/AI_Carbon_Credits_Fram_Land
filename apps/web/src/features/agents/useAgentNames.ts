import { useMemo } from 'react';
import { useTranslation } from 'react-i18next';
import { agentTitle, isKnownAgent } from './logic/agentsLogic';
import type { AgentInfo, AgentMessage } from './types';

export interface AgentNames {
  /** Translated title of an agent ("Carbon agent"); unknown agents use the API's title. */
  title: (agentId: string) => string;
  /** One-line role; unknown agents use the API's role. */
  role: (agentId: string) => string;
}

/**
 * One place that decides how an agent is named, so the Team column, the bubbles and the
 * hand-off arrows always say the same thing.
 */
export function useAgentNames(catalog?: AgentInfo[], messages?: AgentMessage[]): AgentNames {
  const { t } = useTranslation();
  return useMemo(
    () => ({
      title: (agentId) =>
        agentTitle(agentId, {
          catalog,
          messages,
          translated: isKnownAgent(agentId) ? t(`agentsPage.agents.${agentId}.title`) : null,
        }),
      role: (agentId) =>
        isKnownAgent(agentId)
          ? t(`agentsPage.agents.${agentId}.role`)
          : (catalog?.find((a) => a.id === agentId)?.role ?? ''),
    }),
    [t, catalog, messages],
  );
}
