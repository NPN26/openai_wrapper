import { Card } from "@/components/ui/card";

function getChats() {
    // This function would fetch and return the list of chats from storage in backend
    
}

export default function ChatList() {
  return (
    <Card className="w-full h-full flex items-center justify-center">
      <div className="text-muted-foreground">No chats yet. Start a new conversation!</div>
    </Card>
  );
}

export { ChatList };