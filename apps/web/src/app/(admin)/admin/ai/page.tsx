"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { useApiClient } from "@/hooks/use-api-client";

// ── types ──────────────────────────────────────────────────────────────────
interface ProviderStatus {
  name: string;
  configured: boolean;
}

interface AIConfig {
  active_provider: string;
  active_model: string | null;
  fallback_providers: string[];
  temperature: number;
  max_tokens: number;
  timeout_seconds: number;
  max_retries: number;
  enabled: boolean;
  providers: ProviderStatus[];
}

interface HealthResult {
  provider: string;
  configured: boolean;
  healthy: boolean | null;
  latency_ms: number | null;
  error?: string;
}

const PROVIDER_LABELS: Record<string, { label: string; defaultModel: string; color: string }> = {
  gemini: {
    label: "Google Gemini",
    defaultModel: "gemini-1.5-flash",
    color: "text-blue-600",
  },
  openai: {
    label: "OpenAI",
    defaultModel: "gpt-4o-mini",
    color: "text-green-600",
  },
  anthropic: {
    label: "Anthropic Claude",
    defaultModel: "claude-3-haiku-20240307",
    color: "text-purple-600",
  },
};

const MODEL_OPTIONS: Record<string, string[]> = {
  gemini: ["gemini-1.5-flash", "gemini-1.5-pro", "gemini-2.0-flash-exp"],
  openai: ["gpt-4o-mini", "gpt-4o", "gpt-3.5-turbo"],
  anthropic: [
    "claude-3-haiku-20240307",
    "claude-3-5-sonnet-20240620",
    "claude-3-opus-20240229",
  ],
};

// ── component ──────────────────────────────────────────────────────────────
export default function AdminAIPage() {
  const api = useApiClient();
  const qc = useQueryClient();
  const [testPrompt, setTestPrompt] = useState(
    "What is a Labrador Retriever's daily calorie requirement for a 30kg adult?"
  );
  const [testProvider, setTestProvider] = useState("gemini");
  const [testResult, setTestResult] = useState<string | null>(null);

  // ── queries ──────────────────────────────────────────────────────────────

  interface TestResult {
    provider: string;
    model: string;
    latency_ms: number;
    prompt_tokens: number;
    completion_tokens: number;
    response_preview: string;
  }

  const configQuery = useQuery<AIConfig>({
    queryKey: ["admin", "ai", "config"],
    queryFn: () => api.get<AIConfig>("/api/v1/admin/ai/config").then((r) => r.data),
  });

  const healthQuery = useQuery<{ results: HealthResult[] }>({
    queryKey: ["admin", "ai", "health"],
    queryFn: () => api.get<{ results: HealthResult[] }>("/api/v1/admin/ai/health").then((r) => r.data),
    staleTime: 30_000,
  });

  // ── mutations ─────────────────────────────────────────────────────────────

  const updateMutation = useMutation({
    mutationFn: (updates: Partial<AIConfig>) =>
      api.put<AIConfig>("/api/v1/admin/ai/config", updates).then((r) => r.data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["admin", "ai", "config"] });
      toast.success("AI configuration updated");
    },
    onError: (e: Error) => toast.error(`Update failed: ${e.message}`),
  });

  const testMutation = useMutation<TestResult, Error, { provider: string; prompt: string }>({
    mutationFn: (body) =>
      api.post<TestResult>("/api/v1/admin/ai/test", body).then((r) => r.data),
    onSuccess: (data) => {
      setTestResult(
        `✓ ${data.provider} / ${data.model} — ${data.latency_ms}ms\n` +
          `Tokens: ${data.prompt_tokens} in, ${data.completion_tokens} out\n\n` +
          data.response_preview
      );
    },
    onError: (e: Error) => {
      setTestResult(`✗ Error: ${e.message}`);
      toast.error("Provider test failed");
    },
  });

  if (configQuery.isLoading) {
    return (
      <div className="p-8 text-center text-muted-foreground">
        Loading AI configuration…
      </div>
    );
  }

  const cfg = configQuery.data!;
  const health = healthQuery.data?.results ?? [];

  const statusBadge = (result?: HealthResult) => {
    if (!result) return <span className="text-xs text-muted-foreground">Not checked</span>;
    if (!result.configured)
      return <span className="text-xs bg-gray-100 text-gray-600 px-2 py-0.5 rounded-full">Not configured</span>;
    if (result.healthy === null)
      return <span className="text-xs bg-yellow-100 text-yellow-700 px-2 py-0.5 rounded-full">Unknown</span>;
    return result.healthy ? (
      <span className="text-xs bg-green-100 text-green-700 px-2 py-0.5 rounded-full">
        Healthy · {result.latency_ms}ms
      </span>
    ) : (
      <span className="text-xs bg-red-100 text-red-700 px-2 py-0.5 rounded-full">
        Unhealthy
      </span>
    );
  };

  return (
    <div className="max-w-3xl mx-auto py-8 px-4 space-y-8">
      <div>
        <h1 className="text-2xl font-bold">AI Provider Settings</h1>
        <p className="text-sm text-muted-foreground mt-1">
          Manage LLM providers for diet plan enrichment. API keys are configured
          via Railway environment variables and are{" "}
          <strong>never visible here</strong>.
        </p>
      </div>

      {/* Global toggle */}
      <section className="border rounded-lg p-5 space-y-3">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="font-semibold">AI Enrichment</h2>
            <p className="text-sm text-muted-foreground">
              When enabled, diet plans include LLM-generated feeding insights.
            </p>
          </div>
          <button
            onClick={() => updateMutation.mutate({ enabled: !cfg.enabled })}
            className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
              cfg.enabled ? "bg-primary" : "bg-gray-300"
            }`}
          >
            <span
              className={`inline-block h-4 w-4 rounded-full bg-white shadow transition-transform ${
                cfg.enabled ? "translate-x-6" : "translate-x-1"
              }`}
            />
          </button>
        </div>
        {!cfg.enabled && (
          <p className="text-xs text-amber-600 bg-amber-50 rounded p-2">
            AI enrichment is disabled. Diet plans will be generated without
            LLM-powered insights.
          </p>
        )}
      </section>

      {/* Provider status */}
      <section className="border rounded-lg p-5 space-y-4">
        <h2 className="font-semibold">Provider Status</h2>
        <p className="text-xs text-muted-foreground">
          "Not configured" means the API key is missing in Railway environment
          variables. Keys are never shown here.
        </p>
        <div className="space-y-3">
          {cfg.providers.map((p) => {
            const meta = PROVIDER_LABELS[p.name];
            const hResult = health.find((h) => h.provider === p.name);
            return (
              <div
                key={p.name}
                className="flex items-center justify-between py-2 border-b last:border-0"
              >
                <div className="flex items-center gap-3">
                  <span className={`font-medium text-sm ${meta?.color}`}>
                    {meta?.label ?? p.name}
                  </span>
                  {!p.configured && (
                    <span className="text-xs bg-gray-100 text-gray-500 px-2 py-0.5 rounded-full">
                      Key missing
                    </span>
                  )}
                </div>
                {statusBadge(hResult)}
              </div>
            );
          })}
        </div>
        <button
          onClick={() => qc.invalidateQueries({ queryKey: ["admin", "ai", "health"] })}
          className="text-xs text-primary underline"
        >
          Refresh health status
        </button>
      </section>

      {/* Active provider */}
      <section className="border rounded-lg p-5 space-y-4">
        <h2 className="font-semibold">Active Provider</h2>
        <div className="grid gap-4 sm:grid-cols-2">
          <div className="space-y-1">
            <label className="text-sm font-medium">Provider</label>
            <select
              value={cfg.active_provider}
              onChange={(e) =>
                updateMutation.mutate({
                  active_provider: e.target.value,
                  active_model: null, // reset model when switching providers
                })
              }
              className="w-full border rounded px-3 py-2 text-sm bg-background"
            >
              {cfg.providers.map((p) => (
                <option key={p.name} value={p.name} disabled={!p.configured}>
                  {PROVIDER_LABELS[p.name]?.label ?? p.name}
                  {!p.configured ? " (not configured)" : ""}
                </option>
              ))}
            </select>
          </div>

          <div className="space-y-1">
            <label className="text-sm font-medium">Model</label>
            <select
              value={cfg.active_model ?? ""}
              onChange={(e) =>
                updateMutation.mutate({ active_model: e.target.value || null })
              }
              className="w-full border rounded px-3 py-2 text-sm bg-background"
            >
              <option value="">
                Default ({PROVIDER_LABELS[cfg.active_provider]?.defaultModel})
              </option>
              {(MODEL_OPTIONS[cfg.active_provider] ?? []).map((m) => (
                <option key={m} value={m}>
                  {m}
                </option>
              ))}
            </select>
          </div>
        </div>

        {/* Fallback providers */}
        <div className="space-y-1">
          <label className="text-sm font-medium">Fallback chain</label>
          <p className="text-xs text-muted-foreground">
            Providers tried in order when the primary fails. Deselect to disable
            fallback.
          </p>
          <div className="flex flex-wrap gap-2 mt-1">
            {cfg.providers
              .filter((p) => p.name !== cfg.active_provider)
              .map((p) => {
                const isFallback = cfg.fallback_providers.includes(p.name);
                return (
                  <button
                    key={p.name}
                    disabled={!p.configured}
                    onClick={() => {
                      const updated = isFallback
                        ? cfg.fallback_providers.filter((x) => x !== p.name)
                        : [...cfg.fallback_providers, p.name];
                      updateMutation.mutate({ fallback_providers: updated });
                    }}
                    className={`text-xs px-3 py-1 rounded-full border transition-colors ${
                      isFallback
                        ? "bg-primary text-primary-foreground border-primary"
                        : "bg-background text-foreground border-border"
                    } disabled:opacity-40`}
                  >
                    {PROVIDER_LABELS[p.name]?.label ?? p.name}
                  </button>
                );
              })}
          </div>
        </div>
      </section>

      {/* Generation parameters */}
      <section className="border rounded-lg p-5 space-y-4">
        <h2 className="font-semibold">Generation Parameters</h2>
        <div className="grid gap-4 sm:grid-cols-3">
          {(
            [
              { key: "temperature", label: "Temperature", min: 0, max: 2, step: 0.1 },
              { key: "max_tokens", label: "Max tokens", min: 64, max: 2048, step: 64 },
              { key: "timeout_seconds", label: "Timeout (s)", min: 5, max: 120, step: 5 },
            ] as const
          ).map(({ key, label, min, max, step }) => (
            <div key={key} className="space-y-1">
              <label className="text-sm font-medium">{label}</label>
              <input
                type="number"
                min={min}
                max={max}
                step={step}
                defaultValue={cfg[key]}
                onBlur={(e) =>
                  updateMutation.mutate({ [key]: Number(e.target.value) })
                }
                className="w-full border rounded px-3 py-2 text-sm bg-background"
              />
            </div>
          ))}
        </div>
        <p className="text-xs text-muted-foreground">
          Changes reset on process restart. Update Railway environment variables
          for permanent changes.
        </p>
      </section>

      {/* Live test */}
      <section className="border rounded-lg p-5 space-y-4">
        <h2 className="font-semibold">Test Provider</h2>
        <div className="flex gap-2">
          <select
            value={testProvider}
            onChange={(e) => setTestProvider(e.target.value)}
            className="border rounded px-3 py-2 text-sm bg-background"
          >
            {cfg.providers.filter((p) => p.configured).map((p) => (
              <option key={p.name} value={p.name}>
                {PROVIDER_LABELS[p.name]?.label ?? p.name}
              </option>
            ))}
          </select>
        </div>
        <textarea
          value={testPrompt}
          onChange={(e) => setTestPrompt(e.target.value)}
          maxLength={500}
          rows={3}
          className="w-full border rounded px-3 py-2 text-sm bg-background resize-none"
        />
        <button
          onClick={() =>
            testMutation.mutate({ provider: testProvider, prompt: testPrompt })
          }
          disabled={testMutation.isPending}
          className="bg-primary text-primary-foreground px-4 py-2 rounded text-sm hover:opacity-90 disabled:opacity-50"
        >
          {testMutation.isPending ? "Sending…" : "Send test prompt"}
        </button>
        {testResult && (
          <pre className="bg-muted rounded p-3 text-xs whitespace-pre-wrap font-mono">
            {testResult}
          </pre>
        )}
      </section>
    </div>
  );
}
