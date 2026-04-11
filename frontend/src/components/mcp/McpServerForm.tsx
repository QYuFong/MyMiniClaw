'use client';

import { useState } from 'react';
import { useApp } from '@/lib/store';
import { X, Plus, Trash2 } from 'lucide-react';
import type { McpServer, McpServerInput } from '@/lib/api';

interface Props {
  mode: 'add' | 'edit';
  server?: McpServer;
  onClose: () => void;
}

function KeyValueEditor({
  label,
  entries,
  onChange,
}: {
  label: string;
  entries: [string, string][];
  onChange: (entries: [string, string][]) => void;
}) {
  const addEntry = () => onChange([...entries, ['', '']]);
  const removeEntry = (idx: number) => onChange(entries.filter((_, i) => i !== idx));
  const updateEntry = (idx: number, key: string, value: string) => {
    const updated = [...entries];
    updated[idx] = [key, value];
    onChange(updated);
  };

  return (
    <div>
      <div className="flex items-center justify-between mb-1">
        <label className="text-xs font-medium text-gray-600">{label}</label>
        <button
          type="button"
          onClick={addEntry}
          className="text-xs text-blue-600 hover:text-blue-800 flex items-center space-x-0.5"
        >
          <Plus size={10} />
          <span>添加</span>
        </button>
      </div>
      {entries.length === 0 && (
        <div className="text-xs text-gray-400 py-1">无</div>
      )}
      {entries.map(([k, v], idx) => (
        <div key={idx} className="flex items-center space-x-1 mb-1">
          <input
            type="text"
            value={k}
            onChange={(e) => updateEntry(idx, e.target.value, v)}
            placeholder="Key"
            className="flex-1 px-2 py-1 text-xs border border-gray-200 rounded focus:outline-none focus:ring-1 focus:ring-blue-400"
          />
          <input
            type="text"
            value={v}
            onChange={(e) => updateEntry(idx, k, e.target.value)}
            placeholder="Value"
            className="flex-1 px-2 py-1 text-xs border border-gray-200 rounded focus:outline-none focus:ring-1 focus:ring-blue-400"
          />
          <button
            type="button"
            onClick={() => removeEntry(idx)}
            className="p-0.5 text-red-400 hover:text-red-600"
          >
            <Trash2 size={12} />
          </button>
        </div>
      ))}
    </div>
  );
}

export default function McpServerForm({ mode, server, onClose }: Props) {
  const { addMcpServer, updateMcpServer, reloadMcpServers } = useApp();

  const [name, setName] = useState(server?.name || '');
  const [transport, setTransport] = useState<'stdio' | 'sse'>(server?.transport || 'stdio');
  const [enabled, setEnabled] = useState(server?.enabled ?? true);
  const [command, setCommand] = useState(server?.command || '');
  const [args, setArgs] = useState(server?.args?.join(', ') || '');
  const [envEntries, setEnvEntries] = useState<[string, string][]>(
    server?.env ? Object.entries(server.env) : []
  );
  const [url, setUrl] = useState(server?.url || '');
  const [headerEntries, setHeaderEntries] = useState<[string, string][]>(
    server?.headers ? Object.entries(server.headers) : []
  );
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState('');

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');

    if (!name.trim()) {
      setError('请输入 Server 名称');
      return;
    }

    if (transport === 'stdio' && !command.trim()) {
      setError('stdio 模式需要填写 Command');
      return;
    }

    if (transport === 'sse' && !url.trim()) {
      setError('SSE 模式需要填写 URL');
      return;
    }

    const parsedArgs = args
      .split(',')
      .map((a) => a.trim())
      .filter(Boolean);

    const envObj: Record<string, string> = {};
    for (const [k, v] of envEntries) {
      if (k.trim()) envObj[k.trim()] = v;
    }

    const headersObj: Record<string, string> = {};
    for (const [k, v] of headerEntries) {
      if (k.trim()) headersObj[k.trim()] = v;
    }

    const payload: McpServerInput = {
      name: name.trim(),
      enabled,
      transport,
      ...(transport === 'stdio'
        ? {
            command: command.trim(),
            args: parsedArgs.length > 0 ? parsedArgs : undefined,
            env: Object.keys(envObj).length > 0 ? envObj : undefined,
          }
        : {
            url: url.trim(),
            headers: Object.keys(headersObj).length > 0 ? headersObj : undefined,
          }),
    };

    setSubmitting(true);
    try {
      if (mode === 'add') {
        await addMcpServer(payload);
      } else if (server) {
        await updateMcpServer(server.id, payload);
      }
      await reloadMcpServers();
      onClose();
    } catch (err: any) {
      setError(err.message || '操作失败');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/30">
      <div className="bg-white rounded-xl shadow-xl w-full max-w-md mx-4 max-h-[85vh] flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between px-5 py-4 border-b border-gray-200">
          <h3 className="font-semibold text-gray-800">
            {mode === 'add' ? '添加 MCP Server' : '编辑 MCP Server'}
          </h3>
          <button onClick={onClose} className="p-1 text-gray-400 hover:text-gray-600 rounded">
            <X size={18} />
          </button>
        </div>

        {/* Form */}
        <form onSubmit={handleSubmit} className="flex-1 overflow-y-auto px-5 py-4 space-y-4">
          {/* Server 名称 */}
          <div>
            <label className="text-xs font-medium text-gray-600 block mb-1">名称 *</label>
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="如：文件系统、Web 搜索"
              className="w-full px-3 py-2 text-sm border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-400"
            />
          </div>

          {/* Transport 类型 */}
          <div>
            <label className="text-xs font-medium text-gray-600 block mb-1">Transport 类型 *</label>
            <div className="flex space-x-2">
              <button
                type="button"
                onClick={() => setTransport('stdio')}
                className={`flex-1 py-2 text-sm rounded-lg border transition-colors ${
                  transport === 'stdio'
                    ? 'border-blue-400 bg-blue-50 text-blue-700'
                    : 'border-gray-200 text-gray-600 hover:bg-gray-50'
                }`}
              >
                Stdio
              </button>
              <button
                type="button"
                onClick={() => setTransport('sse')}
                className={`flex-1 py-2 text-sm rounded-lg border transition-colors ${
                  transport === 'sse'
                    ? 'border-blue-400 bg-blue-50 text-blue-700'
                    : 'border-gray-200 text-gray-600 hover:bg-gray-50'
                }`}
              >
                SSE
              </button>
            </div>
          </div>

          {/* 启用开关 */}
          <div className="flex items-center justify-between">
            <label className="text-xs font-medium text-gray-600">启用</label>
            <button
              type="button"
              onClick={() => setEnabled(!enabled)}
              className={`w-10 h-5 rounded-full transition-colors relative ${
                enabled ? 'bg-blue-500' : 'bg-gray-300'
              }`}
            >
              <span
                className={`absolute top-0.5 w-4 h-4 rounded-full bg-white shadow transition-transform ${
                  enabled ? 'translate-x-5' : 'translate-x-0.5'
                }`}
              />
            </button>
          </div>

          {/* stdio 模式字段 */}
          {transport === 'stdio' && (
            <>
              <div>
                <label className="text-xs font-medium text-gray-600 block mb-1">Command *</label>
                <input
                  type="text"
                  value={command}
                  onChange={(e) => setCommand(e.target.value)}
                  placeholder="如：npx, python, node"
                  className="w-full px-3 py-2 text-sm border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-400"
                />
              </div>
              <div>
                <label className="text-xs font-medium text-gray-600 block mb-1">Args（逗号分隔）</label>
                <input
                  type="text"
                  value={args}
                  onChange={(e) => setArgs(e.target.value)}
                  placeholder="如：-y, @modelcontextprotocol/server-filesystem, /path"
                  className="w-full px-3 py-2 text-sm border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-400"
                />
              </div>
              <KeyValueEditor
                label="环境变量"
                entries={envEntries}
                onChange={setEnvEntries}
              />
            </>
          )}

          {/* SSE 模式字段 */}
          {transport === 'sse' && (
            <>
              <div>
                <label className="text-xs font-medium text-gray-600 block mb-1">URL *</label>
                <input
                  type="text"
                  value={url}
                  onChange={(e) => setUrl(e.target.value)}
                  placeholder="如：http://localhost:3001/sse"
                  className="w-full px-3 py-2 text-sm border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-400"
                />
              </div>
              <KeyValueEditor
                label="Headers"
                entries={headerEntries}
                onChange={setHeaderEntries}
              />
            </>
          )}

          {error && (
            <div className="text-xs text-red-600 bg-red-50 rounded-lg p-2">{error}</div>
          )}
        </form>

        {/* Footer */}
        <div className="flex items-center justify-end space-x-2 px-5 py-4 border-t border-gray-200">
          <button
            type="button"
            onClick={onClose}
            className="px-4 py-2 text-sm text-gray-600 bg-gray-100 rounded-lg hover:bg-gray-200 transition-colors"
          >
            取消
          </button>
          <button
            onClick={handleSubmit}
            disabled={submitting}
            className="px-4 py-2 text-sm text-white bg-klein-blue rounded-lg hover:bg-blue-700 transition-colors disabled:opacity-50"
          >
            {submitting ? '提交中...' : mode === 'add' ? '添加' : '保存'}
          </button>
        </div>
      </div>
    </div>
  );
}
