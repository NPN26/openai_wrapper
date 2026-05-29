"use client";
import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card } from "@/components/ui/card";

export type LangsmithConfig = {
  apiKey: string;
  apiUrl: string;
  workspaceId: string;
  projectName: string;
};

type Props = {
  open: boolean;
  onValidated: (cfg: LangsmithConfig) => void;
  onCancel?: () => void;
  allowClose?: boolean;
  initialConfig?: LangsmithConfig | null;
};

export function LangsmithSettingsModal({
  open,
  onValidated,
  onCancel,
  allowClose = false,
  initialConfig,
}: Props) {
  const defaultApiUrl = "https://api.smith.langchain.com";
  const defaultProjectName = "openai_wrapper";
  const [apiKey, setApiKey] = useState(initialConfig?.apiKey ?? "");
  const [apiUrl, setApiUrl] = useState(initialConfig?.apiUrl ?? defaultApiUrl);
  const [workspaceId, setWorkspaceId] = useState(initialConfig?.workspaceId ?? "");
  const [projectName, setProjectName] = useState(
    initialConfig?.projectName ?? defaultProjectName,
  );
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const submit = async () => {
    setError(null);
    const trimmedApiKey = apiKey.trim();
    if (!trimmedApiKey) return setError("API key is required");
    const normalizedApiUrl = apiUrl.trim() || defaultApiUrl;
    const normalizedWorkspaceId = workspaceId.trim();
    const normalizedProjectName = projectName.trim() || defaultProjectName;
    setIsLoading(true);
    try {
      const res = await fetch("/api/validate-langsmith", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-LangSmith-Api-Key": trimmedApiKey,
        },
        body: JSON.stringify({
          api_url: normalizedApiUrl,
          workspace_id: normalizedWorkspaceId || undefined,
        }),
      });

      const raw = await res.text();
      let data: { valid?: boolean; message?: string; detail?: string } = {};
      if (raw) {
        try {
          data = JSON.parse(raw) as { valid?: boolean; message?: string; detail?: string };
        } catch {
          if (!res.ok) {
            throw new Error(raw);
          }
        }
      }

      if (!res.ok) {
        throw new Error(
          data.detail ||
          data.message ||
          raw ||
          `Validation failed with status ${res.status}`,
        );
      }

      if (data.valid === false) {
        setError(data.message || "Validation failed");
        return;
      }

      onValidated({
        apiKey: trimmedApiKey,
        apiUrl: normalizedApiUrl,
        workspaceId: normalizedWorkspaceId,
        projectName: normalizedProjectName,
      });
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
        <h2 className="text-xl font-semibold mb-4">Configure LangSmith</h2>
        <div className="grid gap-3">
          <label className="text-sm text-muted-foreground">API URL (optional)</label>
          <Input
            value={apiUrl}
            onChange={(e) => setApiUrl(e.target.value)}
            placeholder="https://api.smith.langchain.com"
          />

          <label className="text-sm text-muted-foreground">API Key</label>
          <Input
            value={apiKey}
            onChange={(e) => setApiKey(e.target.value)}
            placeholder="ls_..."
          />

          <label className="text-sm text-muted-foreground">Workspace ID (optional)</label>
          <Input
            value={workspaceId}
            onChange={(e) => setWorkspaceId(e.target.value)}
            placeholder="Optional workspace id"
          />

          <label className="text-sm text-muted-foreground">Project Name</label>
          <Input
            value={projectName}
            onChange={(e) => setProjectName(e.target.value)}
            placeholder={defaultProjectName}
          />

          {error && <div className="text-sm text-destructive">{error}</div>}

          <div className="flex justify-end gap-2 mt-2">
            {allowClose && (
              <Button variant="outline" onClick={handleCancel} disabled={isLoading}>
                Cancel
              </Button>
            )}
            <Button
              variant="secondary"
              onClick={() => {
                setApiKey("");
                setApiUrl(defaultApiUrl);
                setWorkspaceId("");
                setProjectName(defaultProjectName);
              }}
            >
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

export default LangsmithSettingsModal;
