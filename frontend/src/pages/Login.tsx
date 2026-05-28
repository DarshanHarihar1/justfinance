import { useMutation, useQuery } from "@tanstack/react-query";
import { FormEvent, useState } from "react";
import { Navigate, useNavigate } from "react-router-dom";

import { ApiError, api } from "@/lib/api";
import { queryClient } from "@/lib/query";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

export default function Login() {
  const navigate = useNavigate();
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);

  const { isSuccess: authed } = useQuery({
    queryKey: ["auth", "me"],
    queryFn: () => api.auth.me(),
    retry: false,
  });

  const login = useMutation({
    mutationFn: () => api.auth.login(password),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["auth", "me"] });
      navigate("/upload", { replace: true });
    },
    onError: (err) => {
      if (err instanceof ApiError) {
        if (err.status === 401) setError("Incorrect password.");
        else if (err.status === 429)
          setError("Too many attempts. Try again in a few minutes.");
        else setError("Could not sign in. Try again.");
      } else {
        setError("Network error. Try again.");
      }
    },
  });

  if (authed) return <Navigate to="/upload" replace />;

  function onSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    login.mutate();
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-[--color-bg] px-4">
      <div className="w-full max-w-sm">
        <h1 className="mb-8 text-center text-2xl font-semibold tracking-tight">Finance</h1>
        <form
          onSubmit={onSubmit}
          className="rounded-[--radius-lg] border border-[--color-border] bg-[--color-bg-elevated] p-6"
        >
          <label className="mb-4 block text-sm text-[--color-text-muted]" htmlFor="password">
            Password
          </label>
          <Input
            id="password"
            type="password"
            autoComplete="current-password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            disabled={login.isPending}
          />
          {error ? (
            <p className="mt-3 text-sm text-[--color-danger]" role="alert">
              {error}
            </p>
          ) : null}
          <Button type="submit" className="mt-6 w-full" disabled={login.isPending}>
            {login.isPending ? "Signing in…" : "Continue"}
          </Button>
        </form>
      </div>
    </div>
  );
}
