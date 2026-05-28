"use client";

import { startTransition, useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import { Trash2 } from "lucide-react";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from "@/components/ui/alert-dialog"

interface ChatHistoryItem {
  threadId: string;
  title?: string;
}

export function ConfirmDeleteDialog({
  onConfirm,
  children,
}: {
  onConfirm: () => void;
  children: React.ReactNode;
}) {
  return (
    <AlertDialog>
      <AlertDialogTrigger asChild onClick={(e) => e.stopPropagation()}>
        {children}
      </AlertDialogTrigger>
      <AlertDialogContent>
        <AlertDialogHeader>
          <AlertDialogTitle>Delete Chat?</AlertDialogTitle>
          <AlertDialogDescription>
            Are you sure you want to delete this chat? This action cannot be undone.
          </AlertDialogDescription>
        </AlertDialogHeader>
        <AlertDialogFooter>
          <AlertDialogCancel onClick={(e) => e.stopPropagation()}>Cancel</AlertDialogCancel>
          <AlertDialogAction onClick={(e) => { e.stopPropagation(); onConfirm(); }} className="bg-destructive text-destructive-foreground hover:bg-destructive/90">Delete</AlertDialogAction>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  );
}

export function Sidebar({
  onNewChat,
  onSelectChat,
  onDeleteChat,
  refreshKey,
}: {
  onNewChat: () => void;
  onSelectChat: (threadId: string) => void;
  onDeleteChat: (threadId: string) => void;
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
            <div
              key={chat.threadId}
              onClick={() => onSelectChat(chat.threadId)}
              className="group relative flex items-center justify-between rounded-lg px-3 py-2 text-sm font-medium transition-colors hover:bg-accent hover:text-accent-foreground cursor-pointer"
            >
              <span className="truncate pr-6">
                {chat.title || `Chat ${chat.threadId.substring(0, 8)}`}
              </span>
              
              <ConfirmDeleteDialog onConfirm={() => onDeleteChat(chat.threadId)}>
                <button
                  className="right-2 opacity-0 group-hover:opacity-100 p-1 rounded-md hover:bg-destructive/20 hover:text-destructive transition-all"
                  aria-label="Delete chat"
                >
                  <Trash2 className="h-4 w-4" />
                </button>
              </ConfirmDeleteDialog>
            </div>
          ))
        )}
      </div>
    </div>
  );
}

export default Sidebar;
