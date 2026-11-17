import { ChatBoxView } from "@/features/game/components/ChatBoxView";
import { useChatBox } from "@/features/game/hooks/use-chat-box";

export const ChatBox = () => {
  const chat = useChatBox();

  return <ChatBoxView {...chat} />;
};
