'use client';

import Navbar from '@/components/layout/Navbar';
import Sidebar from '@/components/layout/Sidebar';
import ChatPanel from '@/components/chat/ChatPanel';
import InspectorPanel from '@/components/editor/InspectorPanel';
import ResizeHandle from '@/components/layout/ResizeHandle';
import { useApp } from '@/lib/store';

export default function Home() {
  const { leftPanelWidth, rightPanelWidth, setLeftPanelWidth, setRightPanelWidth } = useApp();
  
  return (
    <div className="flex flex-col h-screen">
      {/* 顶部导航栏 */}
      <Navbar />
      
      {/* 主内容区 */}
      <div className="flex-1 flex overflow-hidden">
        {/* 左侧边栏 */}
        <div style={{ width: leftPanelWidth }} className="flex-shrink-0">
          <Sidebar />
        </div>
        
        {/* 左侧调整手柄 */}
        <ResizeHandle
          onResize={(delta) => {
            const newWidth = Math.max(200, Math.min(500, leftPanelWidth + delta));
            setLeftPanelWidth(newWidth);
          }}
        />
        
        {/* 中间聊天面板 */}
        <div className="flex-1 min-w-0">
          <ChatPanel />
        </div>
        
        {/* 右侧调整手柄 */}
        <ResizeHandle
          onResize={(delta) => {
            const newWidth = Math.max(300, Math.min(800, rightPanelWidth - delta));
            setRightPanelWidth(newWidth);
          }}
        />
        
        {/* 右侧检查器面板 */}
        <div style={{ width: rightPanelWidth }} className="flex-shrink-0">
          <InspectorPanel />
        </div>
      </div>
    </div>
  );
}
