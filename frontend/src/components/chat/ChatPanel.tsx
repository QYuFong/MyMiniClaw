'use client';

import { useApp } from '@/lib/store';
import ChatMessage from './ChatMessage';
import ChatInput from './ChatInput';

export default function ChatPanel() {
  const { messages, currentSessionId, isCompressing } = useApp();
  
  return (
    <div className="h-full flex flex-col bg-gradient-to-br from-white to-gray-50">
      {/* 消息列表 */}
      <div className="flex-1 overflow-y-auto p-6">
        {!currentSessionId ? (
          <div className="h-full flex items-center justify-center">
            <div className="text-center">
              <div className="text-6xl mb-4">💬</div>
              <div className="text-xl text-gray-600 mb-2">欢迎使用 Mini OpenClaw</div>
              <div className="text-sm text-gray-400">选择或创建一个会话开始对话</div>
            </div>
          </div>
        ) : messages.length === 0 ? (
          <div className="h-full flex items-center justify-center">
            <div className="text-center">
              <div className="text-4xl mb-4">👋</div>
              <div className="text-lg text-gray-600">开始新的对话</div>
            </div>
          </div>
        ) : (
          <div className="max-w-4xl mx-auto space-y-6">
            {messages.map((message) => (
              <ChatMessage key={message.id} message={message} />
            ))}
          </div>
        )}
      </div>

      {currentSessionId && isCompressing && (
        <div className="border-t border-amber-200 bg-amber-50">
          <div className="max-w-4xl mx-auto px-6 py-3 text-sm text-amber-700">
            正在压缩对话历史，请稍后...
          </div>
        </div>
      )}
      
      {/* 输入框 */}
      {currentSessionId && (
        <div className="border-t border-gray-200 bg-white">
          <ChatInput />
        </div>
      )}
    </div>
  );
}
