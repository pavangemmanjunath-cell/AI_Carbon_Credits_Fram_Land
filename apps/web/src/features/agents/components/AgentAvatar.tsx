import {
  Bot,
  Coins,
  Compass,
  FileText,
  Leaf,
  Map as MapIcon,
  Satellite,
  Scale,
  ShieldCheck,
  TreePine,
  type LucideIcon,
} from 'lucide-react';
import { agentVisual, type AgentIconKey, type AgentTone } from '../logic/agentsLogic';

const ICONS: Record<AgentIconKey, LucideIcon> = {
  compass: Compass,
  map: MapIcon,
  satellite: Satellite,
  tree: TreePine,
  leaf: Leaf,
  scale: Scale,
  coins: Coins,
  shield: ShieldCheck,
  file: FileText,
  bot: Bot,
};

const TONES: Record<AgentTone, string> = {
  indigo: 'bg-indigo-100 text-indigo-800',
  amber: 'bg-amber-tint text-amber-text',
  blue: 'bg-blue-tint text-blue-text',
  green: 'bg-mint text-forest-deep',
  teal: 'bg-teal-100 text-teal-800',
  violet: 'bg-violet-100 text-violet-800',
  yellow: 'bg-yellow-100 text-yellow-800',
  rose: 'bg-rose-100 text-rose-800',
  slate: 'bg-slate-200 text-slate-800',
};

const SIZES = { sm: 'h-7 w-7', md: 'h-9 w-9', lg: 'h-11 w-11' } as const;
const ICON_SIZES = { sm: 15, md: 18, lg: 22 } as const;

interface AgentAvatarProps {
  agent: string;
  size?: keyof typeof SIZES;
  className?: string;
}

/** Round avatar: a lucide icon on a soft colour that is the same everywhere this agent appears. */
export function AgentAvatar({ agent, size = 'md', className = '' }: AgentAvatarProps) {
  const visual = agentVisual(agent);
  const Icon = ICONS[visual.icon];
  return (
    <span
      aria-hidden="true"
      className={`grid shrink-0 place-items-center rounded-full ${SIZES[size]} ${TONES[visual.tone]} ${className}`}
    >
      <Icon size={ICON_SIZES[size]} />
    </span>
  );
}
