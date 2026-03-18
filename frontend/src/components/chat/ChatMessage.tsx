'use client';

import ReactMarkdown from 'react-markdown';
import { User, Bot } from 'lucide-react';
import ThoughtChain from './ThoughtChain';
import RetrievalCard from './RetrievalCard';

interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  tool_calls?: Array<{
    tool: string;
    input: string;
    output: string;
  }>;
  retrievals?: Array<{
    text: string;
    score: number;
    source: string;
  }>;
  isStreaming?: boolean;
}

interface ChatMessageProps {
  message: Message;
}

export default function ChatMessage({ message }: ChatMessageProps) {
  const isUser = message.role === 'user';
  
  return (
    <div className={`flex ${isUser ? 'justify-end' : 'justify-start'}`}>
      <div className={`flex space-x-3 max-w-3xl ${isUser ? 'flex-row-reverse space-x-reverse' : ''}`}>
        {/* 头像 */}
        <div className={`flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center ${
          isUser ? 'bg-blue-500' : 'bg-gray-700'
        }`}>
          {isUser ? (
            <User size={18} className="text-white" />
          ) : (
            <Bot size={18} className="text-white" />
          )}
        </div>
        
        {/* 消息内容 */}
        <div className="flex-1 space-y-3">
          {/* RAG 检索结果 */}
          {message.retrievals && message.retrievals.length > 0 && (
            <RetrievalCard retrievals={message.retrievals} />
          )}
          
          {/* 工具调用链 */}
          {message.tool_calls && message.tool_calls.length > 0 && (
            <ThoughtChain toolCalls={message.tool_calls} />
          )}
          
          {/* 文本内容 */}
          {message.content && (
            <div className={`px-4 py-3 rounded-lg ${
              isUser
                ? 'bg-blue-500 text-white'
                : 'bg-white border border-gray-200 shadow-sm'
            }`}>
              <div className={`markdown ${isUser ? 'text-white' : 'text-gray-800'}`}>
                <ReactMarkdown>{message.content}</ReactMarkdown>
              </div>
              
              {message.isStreaming && (
                <span className="inline-block w-2 h-4 bg-current animate-pulse ml-1" />
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
