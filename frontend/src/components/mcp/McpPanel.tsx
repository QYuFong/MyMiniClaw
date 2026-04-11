'use client';

import { useState } from 'react';
import { useApp } from '@/lib/store';
import { Plus, RefreshCw, Trash2, Edit2, Power, ChevronDown, ChevronUp, Wrench, AlertCircle } from 'lucide-react';
import type { McpServer } from '@/lib/api';
import McpServerForm from './McpServerForm';

function StatusDot({ status }: { status?: string }) {
  const colorMap: Record<string, string> = {
    connected: 'bg-green-500',
    error: 'bg-red-500',
    disabled: 'bg-gray-400',
    disconnected: 'bg-yellow-500',
  };
  const color = colorMap[status || 'disconnected'] || 'bg-gray-400';
  return <span className={`inline-block w-2.5 h-2.5 rounded-full ${color}`} />;
}

function TransportBadge({ transport }: { transport: string }) {
  return (
    <span className="px-1.5 py-0.5 text-[10px] font-medium rounded bg-gray-100 text-gray-600 uppercase">
      {transport}
    </span>
  );
}

function ServerCard({ server }: { server: McpServer }) {
  const { toggleMcpServer, deleteMcpServer, reloadMcpServers } = useApp();
  const [expanded, setExpanded] = useState(false);
  const [showEdit, setShowEdit] = useState(false);
  const [loading, setLoading] = useState(false);

  const handleToggle = async () => {
    setLoading(true);
    try {
      await toggleMcpServer(server.id);
      await reloadMcpServers();
    } finally {
      setLoading(false);
    }
  };

  const handleDelete = async () => {
    if (!confirm(`确定要删除 MCP Server "${server.name}" 吗？`)) return;
    setLoading(true);
    try {
      await deleteMcpServer(server.id);
    } finally {
      setLoading(false);
    }
  };

  const toolCount = server.tools?.length || 0;

  return (
    <>
      <div className="border border-gray-200 rounded-lg p-3 mb-2">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-2 min-w-0 flex-1">
            <StatusDot status={server.status} />
            <span className="text-sm font-medium truncate">{server.name}</span>
            <TransportBadge transport={server.transport} />
            {toolCount > 0 && (
              <span className="text-xs text-gray-500">{toolCount} 工具</span>
            )}
          </div>

          <div className="flex items-center space-x-1 flex-shrink-0">
            <button
              onClick={handleToggle}
              disabled={loading}
              className={`p-1 rounded transition-colors ${
                server.enabled
                  ? 'text-green-600 hover:bg-green-50'
                  : 'text-gray-400 hover:bg-gray-50'
              }`}
              title={server.enabled ? '禁用' : '启用'}
            >
              <Power size={14} />
            </button>
            <button
              onClick={() => setShowEdit(true)}
              className="p-1 rounded text-gray-500 hover:bg-gray-50 transition-colors"
              title="编辑"
            >
              <Edit2 size={14} />
            </button>
            <button
              onClick={handleDelete}
              disabled={loading}
              className="p-1 rounded text-red-400 hover:bg-red-50 transition-colors"
              title="删除"
            >
              <Trash2 size={14} />
            </button>
          </div>
        </div>

        {server.error && (
          <div className="mt-2 flex items-start space-x-1 text-xs text-red-600 bg-red-50 rounded p-2">
            <AlertCircle size={12} className="flex-shrink-0 mt-0.5" />
            <span className="break-all">{server.error}</span>
          </div>
        )}

        {toolCount > 0 && (
          <button
            onClick={() => setExpanded(!expanded)}
            className="mt-2 flex items-center space-x-1 text-xs text-gray-500 hover:text-gray-700 transition-colors"
          >
            {expanded ? <ChevronUp size={12} /> : <ChevronDown size={12} />}
            <span>{expanded ? '收起工具列表' : '展开工具列表'}</span>
          </button>
        )}

        {expanded && server.tools && (
          <div className="mt-2 space-y-1">
            {server.tools.map((tool) => (
              <div key={tool.name} className="flex items-start space-x-2 text-xs p-1.5 bg-gray-50 rounded">
                <Wrench size={11} className="flex-shrink-0 mt-0.5 text-gray-400" />
                <div className="min-w-0">
                  <div className="font-mono text-gray-700 truncate">{tool.name}</div>
                  {tool.description && (
                    <div className="text-gray-500 mt-0.5 line-clamp-2">{tool.description}</div>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {showEdit && (
        <McpServerForm
          mode="edit"
          server={server}
          onClose={() => setShowEdit(false)}
        />
      )}
    </>
  );
}

export default function McpPanel() {
  const { mcpServers, mcpLoading, reloadMcpServers } = useApp();
  const [showAdd, setShowAdd] = useState(false);
  const [reloading, setReloading] = useState(false);

  const handleReload = async () => {
    setReloading(true);
    try {
      await reloadMcpServers();
    } catch {
      alert('重载失败，请查看后端日志');
    } finally {
      setReloading(false);
    }
  };

  return (
    <div className="h-full flex flex-col">
      {/* 顶部操作栏 */}
      <div className="p-4 border-b border-gray-200 flex items-center justify-between">
        <div className="flex items-center space-x-2">
          <Wrench size={18} className="text-gray-600" />
          <span className="font-medium text-gray-700">MCP Servers</span>
          {mcpLoading && (
            <RefreshCw size={14} className="animate-spin text-gray-400" />
          )}
        </div>
        <div className="flex items-center space-x-2">
          <button
            onClick={handleReload}
            disabled={reloading}
            className="flex items-center space-x-1 px-2.5 py-1.5 text-xs bg-gray-100 text-gray-700 rounded hover:bg-gray-200 transition-colors disabled:opacity-50"
          >
            <RefreshCw size={12} className={reloading ? 'animate-spin' : ''} />
            <span>重载</span>
          </button>
          <button
            onClick={() => setShowAdd(true)}
            className="flex items-center space-x-1 px-2.5 py-1.5 text-xs bg-klein-blue text-white rounded hover:bg-blue-700 transition-colors"
          >
            <Plus size={12} />
            <span>添加</span>
          </button>
        </div>
      </div>

      {/* Server 列表 */}
      <div className="flex-1 overflow-y-auto p-4">
        {mcpServers.length === 0 && !mcpLoading ? (
          <div className="flex flex-col items-center justify-center h-full text-center text-gray-400">
            <Wrench size={48} className="mb-3 opacity-30" />
            <div className="text-sm mb-4">尚未配置 MCP Server</div>
            <button
              onClick={() => setShowAdd(true)}
              className="flex items-center space-x-1 px-4 py-2 text-sm bg-klein-blue text-white rounded-lg hover:bg-blue-700 transition-colors"
            >
              <Plus size={14} />
              <span>添加第一个 MCP Server</span>
            </button>
          </div>
        ) : (
          mcpServers.map((server) => (
            <ServerCard key={server.id} server={server} />
          ))
        )}
      </div>

      {showAdd && (
        <McpServerForm
          mode="add"
          onClose={() => setShowAdd(false)}
        />
      )}
    </div>
  );
}
