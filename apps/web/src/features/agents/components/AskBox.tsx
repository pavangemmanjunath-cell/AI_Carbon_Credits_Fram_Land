import { useState, type FormEvent } from 'react';
import { Send } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { Button } from '@/components/ui/Button';
import {
  MAX_QUESTION_LENGTH,
  SUGGESTED_QUESTION_KEYS,
  validateQuestion,
} from '../logic/agentsLogic';

interface AskBoxProps {
  onAsk: (question: string) => void;
  disabled?: boolean;
  busy?: boolean;
}

/** Free-text question (max 500 characters) plus four ready-made questions. */
export function AskBox({ onAsk, disabled = false, busy = false }: AskBoxProps) {
  const { t } = useTranslation();
  const [text, setText] = useState('');
  const [touched, setTouched] = useState(false);
  const check = validateQuestion(text);
  const blocked = disabled || busy;

  const submit = (event: FormEvent) => {
    event.preventDefault();
    setTouched(true);
    if (!check.ok || blocked) return;
    onAsk(check.question);
    setText('');
    setTouched(false);
  };

  const askSuggestion = (question: string) => {
    if (blocked) return;
    onAsk(question);
    setText('');
    setTouched(false);
  };

  return (
    <form onSubmit={submit} className="card flex flex-col gap-3 p-4" noValidate>
      <label htmlFor="agent-question" className="text-[15px] font-semibold text-ink">
        {t('agentsPage.askTitle')}
      </label>
      <div className="flex flex-col gap-2 sm:flex-row">
        <input
          id="agent-question"
          type="text"
          value={text}
          maxLength={MAX_QUESTION_LENGTH}
          disabled={disabled}
          placeholder={t('agentsPage.askPlaceholder')}
          aria-describedby="agent-question-help"
          aria-invalid={touched && !check.ok}
          onChange={(event) => setText(event.target.value)}
          className="field-input h-11 flex-1 text-[15px]"
        />
        <Button type="submit" size="lg" disabled={blocked}>
          <Send size={16} aria-hidden="true" />
          {t('agentsPage.askButton')}
        </Button>
      </div>
      <p
        id="agent-question-help"
        className="m-0 flex flex-wrap items-center justify-between gap-2 text-[12px] text-muted"
      >
        <span className={touched && !check.ok ? 'font-medium text-rose-700' : ''}>
          {touched && !check.ok
            ? t(check.reason === 'empty' ? 'agentsPage.askEmpty' : 'agentsPage.askTooLong')
            : disabled
              ? t('agentsPage.askNeedsPlot')
              : t('agentsPage.askPrivacy')}
        </span>
        <span className="font-mono">
          {text.length}/{MAX_QUESTION_LENGTH}
        </span>
      </p>
      <ul
        className="m-0 flex list-none flex-wrap gap-2 p-0"
        aria-label={t('agentsPage.suggestionsLabel')}
      >
        {SUGGESTED_QUESTION_KEYS.map((key) => {
          const question = t(`agentsPage.suggestions.${key}`);
          return (
            <li key={key}>
              <button
                type="button"
                disabled={blocked}
                onClick={() => askSuggestion(question)}
                className="rounded-full border border-line bg-surface px-3.5 py-2 text-left text-[13px] text-ink-2 transition-colors hover:bg-mint hover:text-forest-deep disabled:opacity-50"
              >
                {question}
              </button>
            </li>
          );
        })}
      </ul>
    </form>
  );
}
