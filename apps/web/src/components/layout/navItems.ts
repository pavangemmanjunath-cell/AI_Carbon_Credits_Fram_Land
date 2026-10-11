/**
 * Left navigation model (Trimble-style: icon + label, a few calm groups).
 * Pure data and matching rules so the nav is unit-testable.
 */
import {
  Bot,
  Database,
  FileText,
  FlaskConical,
  Hourglass,
  Map as MapIcon,
  Settings,
  type LucideIcon,
} from 'lucide-react';

export type NavKey =
  'myLand' | 'data' | 'agents' | 'treeAge' | 'simulation' | 'reports' | 'settings';

export interface NavItem {
  key: NavKey;
  to: string;
  icon: LucideIcon;
  /** Other routes that belong to this section (detail pages). */
  matches: RegExp[];
}

export interface NavGroup {
  key: 'land' | 'insights' | 'share' | 'system';
  items: NavItem[];
}

export const NAV_GROUPS: NavGroup[] = [
  {
    key: 'land',
    items: [
      {
        key: 'myLand',
        to: '/app',
        icon: MapIcon,
        matches: [/^\/app\/?$/, /^\/app\/plots\/[^/]+\/results\/?$/],
      },
      {
        key: 'data',
        to: '/app/data',
        icon: Database,
        matches: [/^\/app\/data(\/|$)/, /^\/app\/plots\/?$/],
      },
    ],
  },
  {
    key: 'insights',
    items: [
      { key: 'agents', to: '/app/agents', icon: Bot, matches: [/^\/app\/agents(\/|$)/] },
      { key: 'treeAge', to: '/app/tree-age', icon: Hourglass, matches: [/^\/app\/tree-age(\/|$)/] },
      {
        key: 'simulation',
        to: '/app/simulate',
        icon: FlaskConical,
        matches: [/^\/app\/simulate(\/|$)/],
      },
    ],
  },
  {
    key: 'share',
    items: [
      {
        key: 'reports',
        to: '/app/reports',
        icon: FileText,
        matches: [/^\/app\/reports(\/|$)/, /^\/app\/plots\/[^/]+\/report\/?$/],
      },
    ],
  },
  {
    key: 'system',
    items: [
      {
        key: 'settings',
        to: '/app/settings',
        icon: Settings,
        matches: [/^\/app\/settings(\/|$)/, /^\/app\/species(\/|$)/],
      },
    ],
  },
];

export const NAV_ITEMS: NavItem[] = NAV_GROUPS.flatMap((g) => g.items);

export function isNavItemActive(item: NavItem, pathname: string): boolean {
  return item.matches.some((pattern) => pattern.test(pathname));
}

/** The section to highlight for a path (at most one). */
export function activeNavKey(pathname: string): NavKey | null {
  return NAV_ITEMS.find((item) => isNavItemActive(item, pathname))?.key ?? null;
}
