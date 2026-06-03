"use client";

import { memo, useCallback, type ComponentProps } from "react";

import {
  Conversation,
  ConversationContent,
  ConversationEmptyState,
  ConversationScrollButton,
  ConversationDownload,
} from "@/components/ai-elements/conversation";
import {
  Message,
  MessageAction,
  MessageActions,
  MessageContent,
  MessageResponse,
} from "@/components/ai-elements/message";
import { CopyIcon } from "lucide-react";

export type ChatMessage = { role: "user" | "assistant"; content: string };

type ConversationDownloadMessages = ComponentProps<
  typeof ConversationDownload
>["messages"];

type MessagesContainerProps = {
  messages: ChatMessage[];
  isLoading: boolean;
};

const handleCopy = (content: string) => {
  navigator.clipboard.writeText(content);
};

interface CopyActionProps {
  content: string;
}

const CopyAction = memo(({ content }: CopyActionProps) => {
  const handleClick = useCallback(() => handleCopy(content), [content]);
  return (
    <MessageAction
      label="Copy"
      onClick={handleClick}
      tooltip="Copy to clipboard"
    >
      <CopyIcon className="size-4" />
    </MessageAction>
  );
});

CopyAction.displayName = "CopyAction";

export function MessagesContainer({
  messages,
  isLoading,
}: MessagesContainerProps) {
  if (messages.length === 0 && !isLoading) {
    return (
      <Conversation>
        <ConversationEmptyState
          title="Chat"
          description="Start a conversation by typing a message below"
        />
      </Conversation>
    );
  }

  return (
    <Conversation>
      <ConversationContent className="gap-4 p-6">
        {messages.map((message, index) => (
          <Message from={message.role} key={`${message.role}-${index}`}>
            <MessageContent className="max-w-full overflow-hidden">
              <div className="prose prose-slate dark:prose-invert max-w-none 
                prose-headings:font-bold prose-headings:tracking-tight
                prose-h1:text-3xl prose-h1:mb-4 prose-h2:text-2xl prose-h2:mb-3 
                prose-h3:text-xl prose-h3:mb-2 prose-h4:text-lg
                prose-ul:list-disc prose-ol:list-decimal prose-li:my-1">
                <MessageResponse>{message.content}</MessageResponse>
              </div>
            </MessageContent>
            {message.role === "assistant" && (
              <MessageActions>
                <CopyAction content={message.content} />
              </MessageActions>
            )}
          </Message>
        ))}

        {isLoading && (
          <Message from="assistant">
            <MessageContent>
              <p className="text-sm">Thinking...</p>
            </MessageContent>
          </Message>
        )}
      </ConversationContent>
      <ConversationDownload
        messages={messages.map((m, i) => ({
          id: i.toString(),
          role: m.role,
          content: m.content,
        })) as unknown as ConversationDownloadMessages}
      />
      <ConversationScrollButton />
    </Conversation>
  );
}
