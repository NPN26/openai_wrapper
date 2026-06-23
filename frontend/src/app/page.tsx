"use client";
import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Sidebar } from "@/components/sidebar";
import { MessagesContainer } from "@/components/messages-container";
import type { ChatMessage } from "@/components/messages-container";
import SettingsModal from "@/components/settings-modal";
import LangsmithSettingsModal, {
  LangsmithConfig,
} from "@/components/langsmith-settings-modal";
import { ConversationDownload } from "@/components/ai-elements/conversation";

type ChatConfig = { apiKey: string; baseUrl: string; model: string };

export default function Home() {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [showSettings, setShowSettings] = useState(true);
  const [validated, setValidated] = useState(false);
  const [chatConfig, setChatConfig] = useState<ChatConfig | null>(null);
  const [langsmithConfig, setLangsmithConfig] = useState<LangsmithConfig | null>(null);
  const [threadId, setThreadId] = useState(() => crypto.randomUUID());
  const [chatsRefreshKey, setChatsRefreshKey] = useState(0);
  const [canCloseSettings, setCanCloseSettings] = useState(false);
  const [showLangsmithSettings, setShowLangsmithSettings] = useState(false);

  const sendMessage = async () => {
    if (!input.trim()) return;

    if (!validated) {
      // require valid settings before sending messages
      setCanCloseSettings(false);
      setShowSettings(true);
      return;
    }

    if (!chatConfig) {
      setCanCloseSettings(false);
      setShowSettings(true);
      return;
    }

    const message = input.trim();
    const updated = [...messages, { role: "user" as const, content: message }];
    setMessages(updated);
    setInput("");
    setIsLoading(true);

    try {
      const langsmithPayload = langsmithConfig
        ? {
            langsmith_api_key: langsmithConfig.apiKey,
            langsmith_api_url: langsmithConfig.apiUrl,
            langsmith_workspace_id: langsmithConfig.workspaceId || undefined,
            langsmith_project: langsmithConfig.projectName,
          }
        : {};

      const res = await fetch("/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          thread_id: threadId,
          message,
          api_key: chatConfig.apiKey,
          model: chatConfig.model,
          base_url: chatConfig.baseUrl,
          ...langsmithPayload,
        }),
      });

      const raw = await res.text();
      let data: { reply?: string; detail?: string; message?: string } = {};
      if (raw) {
        try {
          data = JSON.parse(raw) as { reply?: string; detail?: string; message?: string };
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
          `Chat request failed with status ${res.status}`,
        );
      }

      const reply = data.reply?.trim();
      if (!reply) {
        throw new Error("Chat response did not include a reply.");
      }

      setMessages([...updated, { role: "assistant", content: reply }]);
      setChatsRefreshKey((value) => value + 1);
    } catch (err: unknown) {
      const errorMessage = err instanceof Error ? err.message : "Chat request failed";
      setMessages([
        ...updated,
        { role: "assistant", content: `Error: ${errorMessage}` },
      ]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleValidated = (cfg: ChatConfig) => {
    setChatConfig(cfg);
    setValidated(true);
    setShowSettings(false);
    setCanCloseSettings(false);
  };

  const handleNewChat = () => {
    setMessages([]);
    setThreadId(crypto.randomUUID());
  };

  const loadChatHistory = async (id: string) => {
    try {
      const res = await fetch(`/api/chat/${id}/history`);
      const data = (await res.json()) as ChatMessage[];

      if (!res.ok) {
        throw new Error("Failed to load chat history");
      }

      setMessages(Array.isArray(data) ? data : []);
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : "Failed to load chat history";
      setMessages([{ role: "assistant", content: `Error: ${errorMessage}` }]);
    }
  };

  const handleSelectChat = (id: string) => {
    setThreadId(id);
    void loadChatHistory(id);
  };

  const handleDeleteChat = async (id: string) => {
    try {
      const res = await fetch(`/api/chat/${id}`, {
        method: "DELETE",
      });

      if (!res.ok) {
        throw new Error("Failed to delete chat");
      }

      // If the deleted chat is currently loaded, clear the messages
      if (id === threadId) {
        setMessages([]);
        setThreadId(crypto.randomUUID());
      }

      setChatsRefreshKey((value) => value + 1);
    } catch (err) {
      console.error("Error deleting chat:", err);
    }
  };

  const handleOpenSettings = () => {
    setCanCloseSettings(true);
    setShowSettings(true);
  };

  const handleCancelSettings = () => {
    setShowSettings(false);
    setCanCloseSettings(false);
  };

  const handleOpenLangsmithSettings = () => {
    setShowLangsmithSettings(true);
  };

  const handleCancelLangsmithSettings = () => {
    setShowLangsmithSettings(false);
  };

  const handleLangsmithValidated = (cfg: LangsmithConfig) => {
    setLangsmithConfig(cfg);
    setShowLangsmithSettings(false);
  };

  if (!validated) {
    return (
      <div className="flex h-screen items-center justify-center">
        <SettingsModal
          open={showSettings}
          onValidated={handleValidated}
          onCancel={handleCancelSettings}
          allowClose={canCloseSettings}
          initialConfig={chatConfig}
        />
        <p className="text-muted-foreground">Please configure your settings to continue.</p>
      </div>
    );
  }

  return (
    <div className="grid h-screen w-full lg:grid-cols-[280px_1fr]">
      <Sidebar
        onNewChat={handleNewChat}
        onSelectChat={handleSelectChat}
        onDeleteChat={handleDeleteChat}
        refreshKey={chatsRefreshKey}
        currentThreadId={threadId}
      />

      <SettingsModal
        open={showSettings}
        onValidated={handleValidated}
        onCancel={handleCancelSettings}
        allowClose={canCloseSettings}
        initialConfig={chatConfig}
      />

      {showLangsmithSettings && (
        <LangsmithSettingsModal
          open
          onValidated={handleLangsmithValidated}
          onCancel={handleCancelLangsmithSettings}
          allowClose
          initialConfig={langsmithConfig}
        />
      )}

      {/* Main Chat Area */}
      <div className="flex-1 flex flex-col">
        <div className="flex items-center justify-between border-b px-6 py-3">
          <div className="text-sm font-semibold text-muted-foreground">Chat</div>
          <Button variant="outline" size="sm" onClick={handleOpenLangsmithSettings}>
            Add Langsmith Settings
          </Button>
          <Button variant="outline" size="sm" onClick={handleOpenSettings}>
            Edit API Settings
          </Button>
        </div>
        <MessagesContainer messages={messages} isLoading={isLoading} />

        {/* Input Area */}
        <div className="border-t p-4 bg-background flex justify-center sticky bottom-0 z-10">
          <div className="flex gap-2 max-w-2xl w-full">
            <Input
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && !e.shiftKey && sendMessage()}
              placeholder="Message..."
              disabled={isLoading}
              className="flex-1"
            />
            {messages.length > 0 && (
              <ConversationDownload
                messages={messages.map((m, i) => ({
                  id: i.toString(),
                  role: m.role,
                  content: m.content,
                  // Required for Vercel AI SDK v5 UIMessage format
                  parts: [{ type: "text", text: m.content }],
                })) as unknown as ConversationDownloadMessages}
              />
            )}
            <Button onClick={sendMessage} disabled={isLoading}>
              Send
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
}
