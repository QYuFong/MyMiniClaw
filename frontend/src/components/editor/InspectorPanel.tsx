'use client';

import { useState } from 'react';
import { useApp } from '@/lib/store';
import dynamic from 'next/dynamic';
import { FileText, Save, Folder, Wrench } from 'lucide-react';
import React from 'react';
import McpPanel from '@/components/mcp/McpPanel';

const Editor = dynamic(() => import('@monaco-editor/react'), {
  ssr: false,
  loading: () => (
    <div className="flex items-center justify-center h-full">
      <div className="text-gray-400">加载编辑器...</div>
    </div>
  ),
});

function EditorTab() {
  const { currentFile, currentFileContent, openFile, saveCurrentFile } = useApp();
  const [editorContent, setEditorContent] = useState('');
  const [hasChanges, setHasChanges] = useState(false);
  
  const files = [
    { path: 'memory/MEMORY.md', label: 'MEMORY.md', icon: '📝' },
    { path: 'workspace/SOUL.md', label: 'SOUL.md', icon: '🌟' },
    { path: 'workspace/IDENTITY.md', label: 'IDENTITY.md', icon: '🎭' },
    { path: 'workspace/USER.md', label: 'USER.md', icon: '👤' },
    { path: 'workspace/AGENTS.md', label: 'AGENTS.md', icon: '🤖' },
    { path: 'skills/get_weather/SKILL.md', label: 'get_weather', icon: '🌤️' },
  ];
  
  const handleOpenFile = async (path: string) => {
    await openFile(path);
    setHasChanges(false);
  };
  
  const handleSave = async () => {
    await saveCurrentFile(editorContent);
    setHasChanges(false);
  };
  
  const handleEditorChange = (value: string | undefined) => {
    if (value !== undefined) {
      setEditorContent(value);
      setHasChanges(value !== currentFileContent);
    }
  };
  
  React.useEffect(() => {
    setEditorContent(currentFileContent);
    setHasChanges(false);
  }, [currentFileContent]);
  
  return (
    <div className="h-full flex flex-col">
      {/* 文件列表 - 限制最大高度，超出时滚动 */}
      <div className="border-b border-gray-200 p-4 shrink-0 max-h-[40%] overflow-y-auto">
        <div className="flex items-center space-x-2 mb-3">
          <Folder size={18} className="text-gray-600" />
          <span className="font-medium text-gray-700">文件</span>
        </div>
        
        <div className="space-y-1">
          {files.map((file) => (
            <button
              key={file.path}
              onClick={() => handleOpenFile(file.path)}
              className={`w-full flex items-center space-x-2 px-3 py-2 rounded-lg text-left transition-colors ${
                currentFile === file.path
                  ? 'bg-blue-50 text-blue-700 border border-blue-200'
                  : 'hover:bg-gray-50 text-gray-700'
              }`}
            >
              <span>{file.icon}</span>
              <span className="text-sm">{file.label}</span>
            </button>
          ))}
        </div>
      </div>
      
      {/* 编辑器区域 */}
      <div className="flex-1 flex flex-col min-h-0">
        {currentFile ? (
          <>
            <div className="flex items-center justify-between px-4 py-3 border-b border-gray-200 bg-gray-50 shrink-0">
              <div className="flex items-center space-x-2">
                <FileText size={16} className="text-gray-600" />
                <span className="text-sm font-medium text-gray-700">
                  {currentFile}
                </span>
                {hasChanges && (
                  <span className="text-xs text-orange-600">●</span>
                )}
              </div>
              
              <button
                onClick={handleSave}
                disabled={!hasChanges}
                className="flex items-center space-x-1 px-3 py-1.5 bg-klein-blue text-white rounded text-sm hover:bg-blue-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              >
                <Save size={14} />
                <span>保存</span>
              </button>
            </div>
            
            <div className="relative flex-1 min-h-0">
              <div className="absolute inset-0">
                <Editor
                  height="100%"
                  value={editorContent}
                  onChange={handleEditorChange}
                  language="markdown"
                  theme="light"
                  options={{
                    minimap: { enabled: false },
                    fontSize: 13,
                    lineNumbers: 'on',
                    wordWrap: 'on',
                    scrollBeyondLastLine: false,
                    automaticLayout: true,
                  }}
                />
              </div>
            </div>
          </>
        ) : (
          <div className="flex-1 flex items-center justify-center">
            <div className="text-center text-gray-400">
              <FileText size={48} className="mx-auto mb-3 opacity-50" />
              <div className="text-sm">选择一个文件开始编辑</div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

export default function InspectorPanel() {
  const { inspectorTab, setInspectorTab } = useApp();
  
  const tabs = [
    { id: 'editor' as const, label: '文件编辑器', icon: FileText },
    { id: 'mcp' as const, label: 'MCP 配置', icon: Wrench },
  ];
  
  return (
    <div className="h-full bg-white border-l border-gray-200 flex flex-col">
      {/* Tab 栏 */}
      <div className="flex border-b border-gray-200">
        {tabs.map((tab) => {
          const Icon = tab.icon;
          const isActive = inspectorTab === tab.id;
          return (
            <button
              key={tab.id}
              onClick={() => setInspectorTab(tab.id)}
              className={`flex-1 flex items-center justify-center space-x-1.5 px-3 py-2.5 text-sm font-medium transition-colors ${
                isActive
                  ? 'text-blue-700 border-b-2 border-blue-600 bg-blue-50/50'
                  : 'text-gray-500 hover:text-gray-700 hover:bg-gray-50'
              }`}
            >
              <Icon size={15} />
              <span>{tab.label}</span>
            </button>
          );
        })}
      </div>
      
      {/* Tab 内容 */}
      <div className="flex-1 min-h-0 overflow-hidden">
        {inspectorTab === 'editor' ? <EditorTab /> : <McpPanel />}
      </div>
    </div>
  );
}
