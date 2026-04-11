/**
 * 全局状态管理（React Context）
 */
'use client';

import React, { createContext, useContext, useState, useEffect, ReactNode } from 'react';
import * as api from './api';

interface Message extends api.Message {
  id: string;
}

interface AppState {
  // 会话相关
  sessions: api.Session[];
  currentSessionId: string | null;
  messages: Message[];
  isStreaming: boolean;
  isCompressing: boolean;
  
  // UI 状态
  leftPanelWidth: number;
  rightPanelWidth: number;
  showRawMessages: boolean;
  ragMode: boolean;
  inspectorTab: 'editor' | 'mcp';
  
  // 编辑器状态
  currentFile: string | null;
  currentFileContent: string;
  
  // MCP 状态
  mcpServers: api.McpServer[];
  mcpLoading: boolean;
  
  // 方法
  loadSessions: () => Promise<void>;
  createSession: () => Promise<void>;
  switchSession: (sessionId: string) => Promise<void>;
  deleteSession: (sessionId: string) => Promise<void>;
  sendMessage: (message: string) => Promise<void>;
  compressCurrentSession: () => Promise<void>;
  
  setLeftPanelWidth: (width: number) => void;
  setRightPanelWidth: (width: number) => void;
  setShowRawMessages: (show: boolean) => void;
  toggleRAGMode: () => Promise<void>;
  setInspectorTab: (tab: 'editor' | 'mcp') => void;
  
  openFile: (path: string) => Promise<void>;
  saveCurrentFile: (content: string) => Promise<void>;
  
  // MCP 方法
  loadMcpServers: () => Promise<void>;
  addMcpServer: (server: api.McpServerInput) => Promise<void>;
  updateMcpServer: (id: string, updates: Partial<api.McpServerInput>) => Promise<void>;
  deleteMcpServer: (id: string) => Promise<void>;
  toggleMcpServer: (id: string) => Promise<void>;
  reloadMcpServers: () => Promise<void>;
}

const AppContext = createContext<AppState | null>(null);

export function AppProvider({ children }: { children: ReactNode }) {
  const [sessions, setSessions] = useState<api.Session[]>([]);
  const [currentSessionId, setCurrentSessionId] = useState<string | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [isStreaming, setIsStreaming] = useState(false);
  const [isCompressing, setIsCompressing] = useState(false);
  
  const [leftPanelWidth, setLeftPanelWidth] = useState(280);
  const [rightPanelWidth, setRightPanelWidth] = useState(400);
  const [showRawMessages, setShowRawMessages] = useState(false);
  const [ragMode, setRagMode] = useState(false);
  
  const [currentFile, setCurrentFile] = useState<string | null>(null);
  const [currentFileContent, setCurrentFileContent] = useState('');
  const [inspectorTab, setInspectorTab] = useState<'editor' | 'mcp'>('editor');
  
  const [mcpServers, setMcpServers] = useState<api.McpServer[]>([]);
  const [mcpLoading, setMcpLoading] = useState(false);
  
  // 加载会话列表
  const loadSessions = async () => {
    try {
      const sessions = await api.getSessions();
      setSessions(sessions);
    } catch (error) {
      console.error('Failed to load sessions:', error);
    }
  };
  
  // 创建新会话
  const createSession = async () => {
    try {
      const session = await api.createSession();
      await loadSessions();
      setCurrentSessionId(session.id);
      setMessages([]);
    } catch (error) {
      console.error('Failed to create session:', error);
    }
  };
  
  // 切换会话
  const switchSession = async (sessionId: string) => {
    try {
      setCurrentSessionId(sessionId);
      const history = await api.getSessionHistory(sessionId);
      setMessages(history.map((msg, i) => ({ ...msg, id: `${i}` })));
    } catch (error) {
      console.error('Failed to switch session:', error);
    }
  };
  
  // 删除会话
  const deleteSession = async (sessionId: string) => {
    try {
      await api.deleteSession(sessionId);
      await loadSessions();
      if (currentSessionId === sessionId) {
        setCurrentSessionId(null);
        setMessages([]);
      }
    } catch (error) {
      console.error('Failed to delete session:', error);
    }
  };
  
  // 发送消息
  const sendMessage = async (message: string) => {
    if (!currentSessionId || isStreaming) return;
    
    setIsStreaming(true);
    
    // 添加用户消息
    const userMsg: Message = {
      id: `${Date.now()}-user`,
      role: 'user',
      content: message,
    };
    setMessages(prev => [...prev, userMsg]);
    
    // 添加助手占位消息
    let assistantMsg: Message = {
      id: `${Date.now()}-assistant`,
      role: 'assistant',
      content: '',
      isStreaming: true,
    };
    setMessages(prev => [...prev, assistantMsg]);
    
    try {
      let currentSegment = assistantMsg;
      let segmentIndex = 0;
      
      for await (const event of api.streamChat(message, currentSessionId)) {
        if (event.type === 'retrieval') {
          // RAG 检索结果
          currentSegment.retrievals = event.results;
          setMessages(prev => [...prev.slice(0, -1), { ...currentSegment }]);
        } else if (event.type === 'token') {
          // Token 流
          currentSegment.content += event.content;
          setMessages(prev => [...prev.slice(0, -1), { ...currentSegment }]);
        } else if (event.type === 'tool_start') {
          // 工具调用开始
          if (!currentSegment.tool_calls) {
            currentSegment.tool_calls = [];
          }
          currentSegment.tool_calls.push({
            tool: event.tool,
            input: event.input,
            output: '',
          });
          setMessages(prev => [...prev.slice(0, -1), { ...currentSegment }]);
        } else if (event.type === 'tool_end') {
          // 工具调用结束
          if (currentSegment.tool_calls) {
            const lastTool = currentSegment.tool_calls[currentSegment.tool_calls.length - 1];
            lastTool.output = event.output;
          }
          setMessages(prev => [...prev.slice(0, -1), { ...currentSegment }]);
        } else if (event.type === 'new_response') {
          // 新的响应段
          segmentIndex++;
          currentSegment.isStreaming = false;
          
          const newSegment: Message = {
            id: `${Date.now()}-assistant-${segmentIndex}`,
            role: 'assistant',
            content: '',
            isStreaming: true,
          };
          currentSegment = newSegment;
          setMessages(prev => [...prev, newSegment]);
        } else if (event.type === 'done') {
          // 完成
          currentSegment.isStreaming = false;
          setMessages(prev => [...prev.slice(0, -1), { ...currentSegment }]);
          await loadSessions();
        } else if (event.type === 'title') {
          // 标题生成
          await loadSessions();
        } else if (event.type === 'error') {
          // 错误
          currentSegment.content += `\n\n[错误: ${event.error}]`;
          currentSegment.isStreaming = false;
          setMessages(prev => [...prev.slice(0, -1), { ...currentSegment }]);
        }
      }
    } catch (error) {
      console.error('Failed to send message:', error);
    } finally {
      setIsStreaming(false);
    }
  };
  
  // 压缩当前会话
  const compressCurrentSession = async () => {
    if (!currentSessionId || isCompressing) return;
    
    try {
      setIsCompressing(true);
      await api.compressSession(currentSessionId);
      await switchSession(currentSessionId);
    } catch (error) {
      console.error('Failed to compress session:', error);
      alert('压缩失败：' + error);
    } finally {
      setIsCompressing(false);
    }
  };
  
  // 切换 RAG 模式
  const toggleRAGMode = async () => {
    try {
      const newMode = !ragMode;
      await api.setRAGMode(newMode);
      setRagMode(newMode);
    } catch (error) {
      console.error('Failed to toggle RAG mode:', error);
    }
  };
  
  // 打开文件
  const openFile = async (path: string) => {
    try {
      const content = await api.readFile(path);
      setCurrentFile(path);
      setCurrentFileContent(content);
    } catch (error) {
      console.error('Failed to open file:', error);
      alert('打开文件失败：' + error);
    }
  };
  
  // 保存当前文件
  const saveCurrentFile = async (content: string) => {
    if (!currentFile) return;
    
    try {
      await api.saveFile(currentFile, content);
      setCurrentFileContent(content);
      alert('保存成功');
    } catch (error) {
      console.error('Failed to save file:', error);
      alert('保存失败：' + error);
    }
  };
  
  // MCP 方法
  const loadMcpServers = async () => {
    try {
      setMcpLoading(true);
      const servers = await api.getMcpServers();
      setMcpServers(servers);
    } catch (error) {
      console.error('Failed to load MCP servers:', error);
    } finally {
      setMcpLoading(false);
    }
  };

  const addMcpServerAction = async (server: api.McpServerInput) => {
    try {
      await api.addMcpServer(server);
      await loadMcpServers();
    } catch (error) {
      console.error('Failed to add MCP server:', error);
      throw error;
    }
  };

  const updateMcpServerAction = async (id: string, updates: Partial<api.McpServerInput>) => {
    try {
      await api.updateMcpServer(id, updates);
      await loadMcpServers();
    } catch (error) {
      console.error('Failed to update MCP server:', error);
      throw error;
    }
  };

  const deleteMcpServerAction = async (id: string) => {
    try {
      await api.deleteMcpServer(id);
      await loadMcpServers();
    } catch (error) {
      console.error('Failed to delete MCP server:', error);
      throw error;
    }
  };

  const toggleMcpServerAction = async (id: string) => {
    try {
      await api.toggleMcpServer(id);
      await loadMcpServers();
    } catch (error) {
      console.error('Failed to toggle MCP server:', error);
      throw error;
    }
  };

  const reloadMcpServersAction = async () => {
    try {
      setMcpLoading(true);
      const result = await api.reloadMcpServers();
      setMcpServers(result.servers);
    } catch (error) {
      console.error('Failed to reload MCP servers:', error);
      throw error;
    } finally {
      setMcpLoading(false);
    }
  };

  // 初始化
  useEffect(() => {
    loadSessions();
    loadMcpServers();
    
    // 加载 RAG 模式
    api.getRAGMode().then(setRagMode).catch(console.error);
  }, []);
  
  const value: AppState = {
    sessions,
    currentSessionId,
    messages,
    isStreaming,
    isCompressing,
    
    leftPanelWidth,
    rightPanelWidth,
    showRawMessages,
    ragMode,
    inspectorTab,
    
    currentFile,
    currentFileContent,
    
    mcpServers,
    mcpLoading,
    
    loadSessions,
    createSession,
    switchSession,
    deleteSession,
    sendMessage,
    compressCurrentSession,
    
    setLeftPanelWidth,
    setRightPanelWidth,
    setShowRawMessages,
    toggleRAGMode,
    setInspectorTab,
    
    openFile,
    saveCurrentFile,
    
    loadMcpServers,
    addMcpServer: addMcpServerAction,
    updateMcpServer: updateMcpServerAction,
    deleteMcpServer: deleteMcpServerAction,
    toggleMcpServer: toggleMcpServerAction,
    reloadMcpServers: reloadMcpServersAction,
  };
  
  return <AppContext.Provider value={value}>{children}</AppContext.Provider>;
}

export function useApp() {
  const context = useContext(AppContext);
  if (!context) {
    throw new Error('useApp must be used within AppProvider');
  }
  return context;
}
