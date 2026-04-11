/**
 * 后端 API 客户端
 */

// 动态获取 API 地址（支持本机和局域网）
const API_BASE = typeof window !== 'undefined'
  ? `http://${window.location.hostname}:8002`
  : 'http://localhost:8002';

export interface Message {
  role: 'user' | 'assistant';
  content: string;
  tool_calls?: ToolCall[];
  retrievals?: RetrievalResult[];
  isStreaming?: boolean;
}

export interface ToolCall {
  tool: string;
  input: string;
  output: string;
}

export interface RetrievalResult {
  text: string;
  score: number;
  source: string;
}

export interface Session {
  id: string;
  title: string;
  created_at: number;
  updated_at: number;
  message_count: number;
}

export interface SSEEvent {
  type: 'retrieval' | 'token' | 'tool_start' | 'tool_end' | 'new_response' | 'done' | 'title' | 'error';
  [key: string]: any;
}

/**
 * 流式聊天（SSE）
 */
export async function* streamChat(
  message: string,
  sessionId: string
): AsyncGenerator<SSEEvent> {
  const response = await fetch(`${API_BASE}/api/chat`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      message,
      session_id: sessionId,
      stream: true,
    }),
  });

  if (!response.ok) {
    throw new Error(`HTTP ${response.status}: ${response.statusText}`);
  }

  const reader = response.body?.getReader();
  if (!reader) {
    throw new Error('Response body is null');
  }

  const decoder = new TextDecoder();
  let buffer = '';

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });

    // 解析 SSE 事件
    const lines = buffer.split('\n');
    buffer = lines.pop() || ''; // 保留最后一行（可能不完整）

    for (const line of lines) {
      if (line.startsWith('event: ')) {
        const eventType = line.slice(7).trim();
        continue;
      }

      if (line.startsWith('data: ')) {
        const data = line.slice(6).trim();
        try {
          const event = JSON.parse(data);
          yield event;
        } catch (e) {
          console.error('Failed to parse SSE data:', data);
        }
      }
    }
  }
}

/**
 * 获取会话列表
 */
export async function getSessions(): Promise<Session[]> {
  const response = await fetch(`${API_BASE}/api/sessions`);
  if (!response.ok) {
    throw new Error('Failed to fetch sessions');
  }
  return response.json();
}

/**
 * 创建新会话
 */
export async function createSession(title: string = '新对话'): Promise<Session> {
  const response = await fetch(`${API_BASE}/api/sessions`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ title }),
  });
  if (!response.ok) {
    throw new Error('Failed to create session');
  }
  return response.json();
}

/**
 * 重命名会话
 */
export async function renameSession(sessionId: string, title: string): Promise<void> {
  const response = await fetch(`${API_BASE}/api/sessions/${sessionId}`, {
    method: 'PUT',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ title }),
  });
  if (!response.ok) {
    throw new Error('Failed to rename session');
  }
}

/**
 * 删除会话
 */
export async function deleteSession(sessionId: string): Promise<void> {
  const response = await fetch(`${API_BASE}/api/sessions/${sessionId}`, {
    method: 'DELETE',
  });
  if (!response.ok) {
    throw new Error('Failed to delete session');
  }
}

/**
 * 获取会话历史
 */
export async function getSessionHistory(sessionId: string): Promise<Message[]> {
  const response = await fetch(`${API_BASE}/api/sessions/${sessionId}/history`);
  if (!response.ok) {
    throw new Error('Failed to fetch session history');
  }
  return response.json();
}

/**
 * 压缩会话历史
 */
export async function compressSession(sessionId: string): Promise<any> {
  const response = await fetch(`${API_BASE}/api/sessions/${sessionId}/compress`, {
    method: 'POST',
  });
  if (!response.ok) {
    throw new Error('Failed to compress session');
  }
  return response.json();
}

/**
 * 读取文件
 */
export async function readFile(path: string): Promise<string> {
  const response = await fetch(`${API_BASE}/api/files?path=${encodeURIComponent(path)}`);
  if (!response.ok) {
    throw new Error('Failed to read file');
  }
  const data = await response.json();
  return data.content;
}

/**
 * 保存文件
 */
export async function saveFile(path: string, content: string): Promise<void> {
  const response = await fetch(`${API_BASE}/api/files`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ path, content }),
  });
  if (!response.ok) {
    throw new Error('Failed to save file');
  }
}

/**
 * 获取 RAG 模式状态
 */
export async function getRAGMode(): Promise<boolean> {
  const response = await fetch(`${API_BASE}/api/config/rag-mode`);
  if (!response.ok) {
    throw new Error('Failed to get RAG mode');
  }
  const data = await response.json();
  return data.enabled;
}

/**
 * 设置 RAG 模式
 */
export async function setRAGMode(enabled: boolean): Promise<void> {
  const response = await fetch(`${API_BASE}/api/config/rag-mode`, {
    method: 'PUT',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ enabled }),
  });
  if (!response.ok) {
    throw new Error('Failed to set RAG mode');
  }
}

/**
 * 获取会话 Token 统计
 */
export async function getSessionTokens(sessionId: string): Promise<{
  system_tokens: number;
  message_tokens: number;
  total_tokens: number;
}> {
  const response = await fetch(`${API_BASE}/api/tokens/session/${sessionId}`);
  if (!response.ok) {
    throw new Error('Failed to get session tokens');
  }
  return response.json();
}

// ==================== MCP API ====================

export interface McpServerTool {
  name: string;
  description: string;
}

export interface McpServer {
  id: string;
  name: string;
  enabled: boolean;
  transport: 'stdio' | 'sse';
  command?: string;
  args?: string[];
  env?: Record<string, string>;
  url?: string;
  headers?: Record<string, string>;
  status?: 'connected' | 'disconnected' | 'error' | 'disabled';
  tools?: McpServerTool[];
  error?: string | null;
}

export type McpServerInput = Omit<McpServer, 'id' | 'status' | 'tools' | 'error'>;

export async function getMcpServers(): Promise<McpServer[]> {
  const response = await fetch(`${API_BASE}/api/mcp/servers`);
  if (!response.ok) {
    throw new Error('Failed to fetch MCP servers');
  }
  return response.json();
}

export async function addMcpServer(server: McpServerInput): Promise<McpServer> {
  const response = await fetch(`${API_BASE}/api/mcp/servers`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(server),
  });
  if (!response.ok) {
    throw new Error('Failed to add MCP server');
  }
  return response.json();
}

export async function updateMcpServer(id: string, updates: Partial<McpServerInput>): Promise<McpServer> {
  const response = await fetch(`${API_BASE}/api/mcp/servers/${id}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(updates),
  });
  if (!response.ok) {
    throw new Error('Failed to update MCP server');
  }
  return response.json();
}

export async function deleteMcpServer(id: string): Promise<void> {
  const response = await fetch(`${API_BASE}/api/mcp/servers/${id}`, {
    method: 'DELETE',
  });
  if (!response.ok) {
    throw new Error('Failed to delete MCP server');
  }
}

export async function toggleMcpServer(id: string): Promise<McpServer> {
  const response = await fetch(`${API_BASE}/api/mcp/servers/${id}/toggle`, {
    method: 'POST',
  });
  if (!response.ok) {
    throw new Error('Failed to toggle MCP server');
  }
  return response.json();
}

export async function reloadMcpServers(): Promise<{ tools_count: number; servers: McpServer[] }> {
  const response = await fetch(`${API_BASE}/api/mcp/reload`, {
    method: 'POST',
  });
  if (!response.ok) {
    throw new Error('Failed to reload MCP servers');
  }
  return response.json();
}
