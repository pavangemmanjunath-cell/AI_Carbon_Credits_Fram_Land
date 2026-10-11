import {
  Circle,
  FileUp,
  Keyboard,
  MapPin,
  Pencil,
  PenLine,
  Pentagon,
  Spline,
  Square,
  Trash2,
  type LucideIcon,
} from 'lucide-react';
import { useTranslation } from 'react-i18next';
import {
  isToolActive,
  LAND_TOOL_KEYS,
  SHAPE_OPTIONS,
  type AddLandOption,
  type LandInputMode,
  type LandToolAction,
  type ShapeOption,
} from '@/lib/landInput';

const ADD_ICONS: Record<AddLandOption, LucideIcon> = {
  boundary: Pentagon,
  'tree-line': Spline,
  pin: MapPin,
  coordinates: Keyboard,
  import: FileUp,
};

const SHAPE_ICONS: Record<ShapeOption, LucideIcon> = {
  pen: PenLine,
  rectangle: Square,
  circle: Circle,
};

function ToolButton({
  icon: Icon,
  label,
  hint,
  active,
  disabled,
  danger,
  onClick,
}: {
  icon: LucideIcon;
  label: string;
  hint: string;
  active?: boolean;
  disabled?: boolean;
  danger?: boolean;
  onClick: () => void;
}) {
  return (
    <button
      type="button"
      title={hint}
      aria-pressed={active}
      disabled={disabled}
      onClick={onClick}
      className={`flex min-h-[46px] w-full flex-col items-center justify-center gap-0.5 rounded-[8px] px-1 py-1 text-center text-[10.5px] font-medium leading-tight transition-colors disabled:opacity-40 ${
        active
          ? 'bg-mint text-forest-deep'
          : danger
            ? 'text-ink-2 hover:bg-amber-tint hover:text-amber-text'
            : 'text-ink-2 hover:bg-ground'
      }`}
    >
      <Icon size={18} aria-hidden="true" />
      <span className="break-words [hyphens:auto]">{label}</span>
    </button>
  );
}

interface Props {
  mode: LandInputMode;
  canEdit: boolean;
  onAction: (action: LandToolAction) => void;
}

/** "Mark your land" toolbar: clearly labelled ways to add land, then Edit and Delete for the selected plot. */
export function LandInputToolbar({ mode, canEdit, onAction }: Props) {
  const { t } = useTranslation();
  return (
    <div
      role="toolbar"
      aria-label={t('map.toolbarLabel')}
      aria-orientation="vertical"
      className="float-control grid w-[132px] grid-cols-2 gap-0.5 p-1"
    >
      {(Object.keys(ADD_ICONS) as AddLandOption[]).map((option) => (
        <ToolButton
          key={option}
          icon={ADD_ICONS[option]}
          label={t(`map.tool_${LAND_TOOL_KEYS[option]}`)}
          hint={t(`map.tool_${LAND_TOOL_KEYS[option]}Hint`)}
          active={isToolActive(option, mode)}
          onClick={() => onAction(option)}
        />
      ))}
      <span aria-hidden="true" className="col-span-2 mx-1 my-0.5 border-t border-line" />
      {SHAPE_OPTIONS.map((shape) => (
        <ToolButton
          key={shape}
          icon={SHAPE_ICONS[shape]}
          label={t(`map.tool_${shape}`)}
          hint={t(`map.tool_${shape}Hint`)}
          active={mode === shape}
          onClick={() => onAction(shape)}
        />
      ))}
      <span aria-hidden="true" className="col-span-2 mx-1 my-0.5 border-t border-line" />
      <ToolButton
        icon={Pencil}
        label={t('map.tool_edit')}
        hint={t('map.tool_editHint')}
        active={mode === 'edit'}
        disabled={!canEdit}
        onClick={() => onAction('edit')}
      />
      <ToolButton
        icon={Trash2}
        label={t('map.tool_delete')}
        hint={t('map.tool_deleteHint')}
        disabled={!canEdit}
        danger
        onClick={() => onAction('delete')}
      />
    </div>
  );
}
