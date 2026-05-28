"use client";

import { useEffect, useState } from "react";
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
  title,
  description,
}: {
  onConfirm: () => void;
  children: React.ReactNode;
  title: string;
  description: string;
}) {
  return (
    <AlertDialog>
      <AlertDialogTrigger asChild onClick={(e) => e.stopPropagation()}>
        {children}
      </AlertDialogTrigger>
      <AlertDialogContent>
        <AlertDialogHeader>
          <AlertDialogTitle>{title}</AlertDialogTitle>
          <AlertDialogDescription>
            {description}
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
      setChatHistory(Array.isArray(data) ? data : []);
      setIsLoading(false);
    } catch (error) {
      console.error("Failed to fetch chat history:", error);
      setIsLoading(false);
    }
  };

  const deleteChats = async () => {
    try {      
      const res = await fetch("/api/chats", { method: "DELETE" });
      if (!res.ok) {
        throw new Error("Failed to delete chats");
      }
      setChatHistory([]);
    } catch (error) {
      console.error("Failed to delete chats:", error);
    }
  };


  useEffect(() => {
    void fetchChats();
  }, [refreshKey]);

  return (
    <div className="w-64 border-r bg-muted/50 flex flex-col p-4">
      <Button variant="outline" className="w-full mb-4" onClick={onNewChat}>
        + New Chat
      </Button>
      <div className="flex-1 overflow-y-auto space-y-2">
        <div className="text-sm font-semibold text-muted-foreground px-2">
          Recent
          <ConfirmDeleteDialog onConfirm={deleteChats} title="Delete all chats?" description="Are you sure you want to delete all chats? This action cannot be undone.">
            <button
              className="group-hover:opacity-100 p-1 rounded-md bg-destructive text-white hover:bg-destructive/20 hover:text-destructive transition-all"
              aria-label="Delete all chats"
            >
              Delete all Chats
            </button>
          </ConfirmDeleteDialog>
        </div>
        {isLoading ? (
          <div className="text-sm text-muted-foreground px-2">Loading...</div>
        ) : chatHistory.length === 0 ? (
          <div className="text-sm text-muted-foreground px-2">No chats yet.</div>
        ) : (
          chatHistory.map((chat) => (
            <div
              key={chat.threadId}
              className="group relative flex items-center rounded-lg text-sm font-medium transition-colors hover:bg-accent hover:text-accent-foreground"
            >
              <button
                type="button"
                onClick={() => onSelectChat(chat.threadId)}
                className="flex-1 text-left px-3 py-2 truncate pr-10"
              >
                {chat.title || `Chat ${chat.threadId.substring(0, 8)}`}
              </button>

              <div className="absolute right-2 opacity-0 group-hover:opacity-100 transition-opacity">
                <ConfirmDeleteDialog onConfirm={() => onDeleteChat(chat.threadId)} title="Delete Chat?" description="Are you sure you want to delete this chat? This action cannot be undone.">
                  <button
                    type="button"
                    className="p-1 rounded-md hover:bg-destructive/20 hover:text-destructive transition-colors"
                    aria-label="Delete chat"
                  >
                    <Trash2 className="h-4 w-4" />
                  </button>
                </ConfirmDeleteDialog>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
}

export default Sidebar;
