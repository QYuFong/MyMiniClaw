'use client';

import { useApp } from '@/lib/store';
import { MessageSquare, Trash2, Plus, Wrench, Sparkles } from 'lucide-react';

export default function Sidebar() {
  const {
    sessions,
    currentSessionId,
    createSession,
    switchSession,
    deleteSession,
    showRawMessages,
    setShowRawMessages,
    compressCurrentSession,
    isCompressing,
    ragMode,
    toggleRAGMode,
  } = useApp();
  
  return (
    <div className="h-full bg-white border-r border-gray-200 flex flex-col">
      {/* 头部：新建对话按钮 */}
      <div className="p-4 border-b border-gray-200">
        <button
          onClick={createSession}
          className="w-full flex items-center justify-center space-x-2 px-4 py-2 bg-klein-blue text-white rounded-lg hover:bg-blue-700 transition-colors"
        >
          <Plus size={18} />
          <span>新建对话</span>
        </button>
      </div>
      
      {/* 会话列表 */}
      <div className="flex-1 overflow-y-auto p-2">
        {sessions.map((session) => (
          <div
            key={session.id}
            className={`group flex items-center justify-between p-3 rounded-lg cursor-pointer mb-1 ${
              currentSessionId === session.id
                ? 'bg-blue-50 border border-blue-200'
                : 'hover:bg-gray-50'
            }`}
            onClick={() => switchSession(session.id)}
          >
            <div className="flex items-center space-x-2 flex-1 min-w-0">
              <MessageSquare size={16} className="flex-shrink-0 text-gray-500" />
              <span className="text-sm truncate">{session.title}</span>
            </div>
            
            <button
              onClick={(e) => {
                e.stopPropagation();
                if (confirm('确定要删除这个会话吗？')) {
                  deleteSession(session.id);
                }
              }}
              className="opacity-0 group-hover:opacity-100 p-1 hover:bg-red-50 rounded transition-opacity"
            >
              <Trash2 size={14} className="text-red-500" />
            </button>
          </div>
        ))}
        
        {sessions.length === 0 && (
          <div className="text-center text-gray-400 text-sm mt-8">
            暂无会话
          </div>
        )}
      </div>
      
      {/* 底部：工具栏 */}
      <div className="border-t border-gray-200 p-4 space-y-2">
        {/* 压缩按钮 */}
        <button
          onClick={() => {
            if (confirm('确定要压缩当前会话历史吗？前 50% 的消息将被归档。')) {
              compressCurrentSession();
            }
          }}
          disabled={!currentSessionId || isCompressing}
          className="w-full flex items-center justify-center space-x-2 px-4 py-2 bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
        >
          <Wrench size={16} />
          <span className="text-sm">压缩历史</span>
        </button>
        
        {/* RAG 模式切换 */}
        <button
          onClick={toggleRAGMode}
          className={`w-full flex items-center justify-center space-x-2 px-4 py-2 rounded-lg transition-colors ${
            ragMode
              ? 'bg-purple-100 text-purple-700 hover:bg-purple-200'
              : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
          }`}
        >
          <Sparkles size={16} />
          <span className="text-sm">{ragMode ? 'RAG: ON' : 'RAG: OFF'}</span>
        </button>
        
        {/* Raw Messages 切换 */}
        <button
          onClick={() => setShowRawMessages(!showRawMessages)}
          className={`w-full px-4 py-2 rounded-lg transition-colors text-sm ${
            showRawMessages
              ? 'bg-orange-100 text-orange-700 hover:bg-orange-200'
              : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
          }`}
        >
          {showRawMessages ? 'Raw: ON' : 'Raw: OFF'}
        </button>
      </div>
    </div>
  );
}
