"use client";

import { startTransition, useEffect, useState } from "react";
import { Button } from "@/components/ui/button";

interface ChatHistoryItem {
  threadId: string;
  title?: string;
}

export default function Sidebar({
  onNewChat,
  onSelectChat,
  refreshKey,
}: {
  onNewChat: () => void;
  onSelectChat: (threadId: string) => void;
  refreshKey: number;
}) {
  const [chatHistory, setChatHistory] = useState<ChatHistoryItem[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  const fetchChats = async () => {
    try {
      const res = await fetch("/api/chats");
      const data = await res.json();
      startTransition(() => {
        setChatHistory(Array.isArray(data) ? data : []);
        setIsLoading(false);
      });
    } catch (error) {
      console.error("Failed to fetch chat history:", error);
      setIsLoading(false);
    }
  };

  useEffect(() => {
    const timeoutId = window.setTimeout(() => {
      void fetchChats();
    }, 0);

    return () => window.clearTimeout(timeoutId);
  }, [refreshKey]);

  return (
    <div className="w-64 border-r bg-muted/50 flex flex-col p-4">
      <Button variant="outline" className="w-full mb-4" onClick={onNewChat}>
        + New Chat
      </Button>
      <div className="flex-1 overflow-y-auto space-y-2">
        <div className="text-sm font-semibold text-muted-foreground px-2">
          Recent
        </div>
        {isLoading ? (
          <div className="text-sm text-muted-foreground px-2">Loading...</div>
        ) : chatHistory.length === 0 ? (
          <div className="text-sm text-muted-foreground px-2">No chats yet.</div>
        ) : (
          chatHistory.map((chat) => (
            <Button
              key={chat.threadId}
              variant="ghost"
              className="w-full justify-start"
              onClick={() => onSelectChat(chat.threadId)}
            >
              {chat.threadId === "default" ? "Default Chat" : chat.title || "Chat " + chat.threadId.slice(0, 8)}
            </Button>
          ))
        )}
      </div>
    </div>
  );
}

export { Sidebar };
