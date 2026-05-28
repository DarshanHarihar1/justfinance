import { useMutation } from "@tanstack/react-query";
import { FormEvent, useState } from "react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import type { MonthYear } from "@/hooks/useSelectedMonth";
import { ApiError, api } from "@/lib/api";

type Turn = { question: string; answer: string };

export function AskSection({ monthYear }: { monthYear: MonthYear }) {
  const [question, setQuestion] = useState("");
  const [turns, setTurns] = useState<Turn[]>([]);

  const ask = useMutation({
    mutationFn: (q: string) =>
      api.analytics.ask({
        question: q,
        month: monthYear.month,
        year: monthYear.year,
      }),
    onSuccess: (data, q) => {
      setTurns((prev) => [...prev, { question: q, answer: data.answer }]);
      setQuestion("");
    },
    onError: (err) => {
      if (err instanceof ApiError && err.status === 429) {
        toast.error("Too many questions — wait a minute and try again.");
      } else if (err instanceof ApiError && err.status === 503) {
        toast.error("Ask requires an OpenRouter API key on the backend.");
      } else {
        toast.error("Could not get an answer.");
      }
    },
  });

  function onSubmit(e: FormEvent) {
    e.preventDefault();
    const q = question.trim();
    if (!q || ask.isPending) return;
    ask.mutate(q);
  }

  return (
    <section className="mt-12">
      <h2 className="mb-4 text-sm font-medium text-[--color-text-muted]">
        Ask about your spending
      </h2>
      <form onSubmit={onSubmit} className="flex flex-col gap-3 sm:flex-row">
        <Input
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          placeholder="Where did most of my food spend go this month?"
          disabled={ask.isPending}
          className="flex-1"
        />
        <Button type="submit" disabled={ask.isPending || !question.trim()}>
          {ask.isPending ? "Asking…" : "Ask"}
        </Button>
      </form>

      {turns.length > 0 ? (
        <ul className="mt-6 space-y-4">
          {turns.map((turn, i) => (
            <li key={i} className="text-sm">
              <p className="font-medium text-[--color-text]">▸ {turn.question}</p>
              <p className="mt-1 text-[--color-text-muted]">{turn.answer}</p>
            </li>
          ))}
        </ul>
      ) : null}
    </section>
  );
}
