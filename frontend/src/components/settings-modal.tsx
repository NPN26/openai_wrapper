"use client";
import { useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card } from "@/components/ui/card";

type ChatConfig = { apiKey: string; baseUrl: string; model: string };

type Props = {
  open: boolean;
  onValidated: (cfg: ChatConfig) => void;
  onCancel?: () => void;
  allowClose?: boolean;
  initialConfig?: ChatConfig | null;
};

export function SettingsModal({
  open,
  onValidated,
  onCancel,
  allowClose = false,
  initialConfig,
}: Props) {
  const defaultBaseUrl = "https://api.openai.com/v1";
  const defaultModel = "gpt-4.1";
  const [apiKey, setApiKey] = useState("");
  const [baseUrl, setBaseUrl] = useState(defaultBaseUrl);
  const [model, setModel] = useState(defaultModel);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!open) return;
    setApiKey(initialConfig?.apiKey ?? "");
    setBaseUrl(initialConfig?.baseUrl ?? defaultBaseUrl);
    setModel(initialConfig?.model ?? defaultModel);
    setError(null);
  }, [open, initialConfig, defaultBaseUrl, defaultModel]);

  const submit = async () => {
    setError(null);
    if (!apiKey.trim()) return setError("API key is required");
    const normalizedBaseUrl = baseUrl.trim() || defaultBaseUrl;
    setIsLoading(true);
    try {
      const res = await fetch("/api/validate", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ api_key: apiKey, base_url: normalizedBaseUrl }),
      });

      const contentType = res.headers.get("content-type");
      let data: { valid?: boolean; message?: string; detail?: string } = {};

      if (contentType && contentType.includes("application/json")) {
        data = await res.json();
      } else {
        const raw = await res.text();
        if (!res.ok) {
          // Handle cases where the server returns an HTML error page (like a 500)
          if (raw.includes("<!DOCTYPE") || raw.includes("<html")) {
            throw new Error(`Backend Error (${res.status}): The API server is unreachable or failed to start. Check your BACKEND_URL and DB settings.`);
          }
          throw new Error(raw || `Error ${res.status}`);
        }
      }

      if (!res.ok) {
        throw new Error(
          data.detail ||
          data.message ||
          `Validation failed with status ${res.status}`,
        );
      }

      if (data.valid) {
        const cfg = { apiKey, baseUrl: normalizedBaseUrl, model };
        onValidated(cfg);
      } else {
        setError(data.message || "Validation failed");
      }
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : "Validation request failed";
      setError(message);
    } finally {
      setIsLoading(false);
    }
  };

  const handleCancel = () => {
    setError(null);
    onCancel?.();
  };

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
      <Card className="w-full max-w-lg p-6">
        <h2 className="text-xl font-semibold mb-4">Configure OpenAI</h2>
        <div className="grid gap-3">
          <label className="text-sm text-muted-foreground">Base URL (optional)</label>
          <Input
            value={baseUrl}
            onChange={(e) => setBaseUrl(e.target.value)}
            placeholder="https://api.openai.com/v1 or Azure resource endpoint"
          />

          <label className="text-sm text-muted-foreground">API Key</label>
          <Input
            value={apiKey}
            onChange={(e) => setApiKey(e.target.value)}
            placeholder="sk-... or azure key"
          />

          <label className="text-sm text-muted-foreground">Model / Deployment</label>
          <Input
            value={model}
            onChange={(e) => setModel(e.target.value)}
          />

          {error && <div className="text-sm text-destructive">{error}</div>}

          <div className="flex justify-end gap-2 mt-2">
            {allowClose && (
              <Button variant="outline" onClick={handleCancel} disabled={isLoading}>
                Cancel
              </Button>
            )}
            <Button variant="secondary" onClick={() => {
              // Clear in-memory form fields and keep modal open.
              setApiKey("");
              setBaseUrl(defaultBaseUrl);
              setModel(defaultModel);
            }}>
              Reset
            </Button>
            <Button onClick={submit} disabled={isLoading}>
              {isLoading ? "Validating..." : "Save & Validate"}
            </Button>
          </div>
        </div>
      </Card>
    </div>
  );
}

export default SettingsModal;
