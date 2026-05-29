"use client";
import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Sidebar } from "@/components/sidebar";
import SettingsModal from "@/components/settings-modal";

type Message = { role: "user" | "assistant"; content: string };
type ChatConfig = { apiKey: string; baseUrl: string; model: string };

export default function Home() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [showSettings, setShowSettings] = useState(true);
  const [validated, setValidated] = useState(false);
  const [chatConfig, setChatConfig] = useState<ChatConfig | null>(null);
  const [threadId, setThreadId] = useState(() => crypto.randomUUID());
  const [chatsRefreshKey, setChatsRefreshKey] = useState(0);
  const [canCloseSettings, setCanCloseSettings] = useState(false);

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
      const res = await fetch("/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          thread_id: threadId,
          message,
          api_key: chatConfig.apiKey,
          model: chatConfig.model,
          base_url: chatConfig.baseUrl,
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
      const data = (await res.json()) as Message[];

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
      />

      <SettingsModal
        open={showSettings}
        onValidated={handleValidated}
        onCancel={handleCancelSettings}
        allowClose={canCloseSettings}
        initialConfig={chatConfig}
      />

      {/* Main Chat Area */}
      <div className="flex-1 flex flex-col">
        <div className="flex items-center justify-between border-b px-6 py-3">
          <div className="text-sm font-semibold text-muted-foreground">Chat</div>
          <Button variant="outline" size="sm" onClick={handleOpenSettings}>
            Edit API Settings
          </Button>
        </div>
        {/* Messages Container */}
        <div className="flex-1 overflow-y-auto p-6 space-y-4">
          {messages.length === 0 ? (
            <div className="flex items-center justify-center h-full text-center">
              <div className="max-w-md">
                <h1 className="text-3xl font-bold mb-2">Chat</h1>
                <p className="text-muted-foreground">
                  Start a conversation by typing a message below
                </p>
              </div>
            </div>
          ) : (
            messages.map((m, i) => (
              <div
                key={i}
                className={`flex ${
                  m.role === "user" ? "justify-end" : "justify-start"
                }`}
              >
                <div
                  className={`max-w-md px-4 py-2 rounded-lg ${
                    m.role === "user"
                      ? "bg-primary text-primary-foreground"
                      : "bg-muted"
                  }`}
                >
                  <p className="text-sm">{m.content}</p>
                </div>
              </div>
            ))
          )}
          {isLoading && (
            <div className="flex justify-start">
              <div className="bg-muted px-4 py-2 rounded-lg">
                <p className="text-sm">Thinking...</p>
              </div>
            </div>
          )}
        </div>

        {/* Input Area */}
        <div className="border-t p-4 bg-background flex justify-center">
          <div className="flex gap-2 max-w-2xl w-full">
            <Input
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && !e.shiftKey && sendMessage()}
              placeholder="Message..."
              disabled={isLoading}
              className="flex-1"
            />
            <Button onClick={sendMessage} disabled={isLoading}>
              Send
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
}
