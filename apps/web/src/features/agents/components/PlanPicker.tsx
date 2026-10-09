import { CircleCheck, Layers, TreePine, Zap, type LucideIcon } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { planAgentIds } from '../logic/agentsLogic';
import type { AgentPlanInfo } from '../types';
import type { AgentNames } from '../useAgentNames';

const PLAN_ICONS: Record<string, LucideIcon> = {
  'full-assessment': Layers,
  'quick-estimate': Zap,
  'tree-age-check': TreePine,
};

interface PlanPickerProps {
  plans: AgentPlanInfo[];
  value: string;
  onChange: (planId: string) => void;
  names: AgentNames;
  disabled?: boolean;
}

/** Three simple cards. They are real radio buttons, so the arrow keys and screen readers just work. */
export function PlanPicker({ plans, value, onChange, names, disabled }: PlanPickerProps) {
  const { t } = useTranslation();
  return (
    <fieldset className="m-0 min-w-0 border-0 p-0" disabled={disabled}>
      <legend className="mb-2 p-0 text-[12px] font-medium text-ink-2">
        {t('agentsPage.plan')}
      </legend>
      <div className="grid grid-cols-1 gap-2.5 md:grid-cols-3">
        {plans.map((plan) => {
          const Icon = PLAN_ICONS[plan.id] ?? Layers;
          const agentCount = planAgentIds(plan.steps).length;
          const title = t(`agentsPage.plans.${plan.id}.title`, { defaultValue: plan.title });
          const description = t(`agentsPage.plans.${plan.id}.description`, {
            defaultValue: plan.description ?? plan.steps.map((id) => names.title(id)).join(' → '),
          });
          return (
            <label
              key={plan.id}
              className="group relative flex cursor-pointer items-start gap-3 rounded-[12px] border border-line bg-surface p-3.5 transition-colors hover:bg-ground has-[:checked]:border-forest has-[:checked]:bg-mint has-[:focus-visible]:outline-2 has-[:focus-visible]:outline-offset-2 has-[:focus-visible]:outline-forest has-[:disabled]:cursor-not-allowed has-[:disabled]:opacity-60"
            >
              <input
                type="radio"
                name="agent-plan"
                value={plan.id}
                checked={value === plan.id}
                onChange={() => onChange(plan.id)}
                className="sr-only"
              />
              <span className="grid h-9 w-9 shrink-0 place-items-center rounded-full bg-ground text-forest group-has-[:checked]:bg-white">
                <Icon size={18} aria-hidden="true" />
              </span>
              <span className="min-w-0 flex-1">
                <span className="block text-[14.5px] font-semibold text-ink">{title}</span>
                <span className="mt-0.5 block text-[12.5px] leading-snug text-ink-2">
                  {description}
                </span>
                <span className="mt-1.5 block font-mono text-[11px] text-muted">
                  {t('agentsPage.agentsCount', { count: agentCount })}
                </span>
              </span>
              <CircleCheck
                size={18}
                aria-hidden="true"
                className="invisible mt-0.5 shrink-0 text-forest group-has-[:checked]:visible"
              />
            </label>
          );
        })}
      </div>
    </fieldset>
  );
}
