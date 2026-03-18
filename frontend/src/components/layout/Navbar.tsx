'use client';

export default function Navbar() {
  return (
    <nav className="glass border-b border-gray-200 h-14 flex items-center justify-between px-6 sticky top-0 z-50">
      {/* 左侧标识 */}
      <div className="flex items-center space-x-2">
        <div className="text-xl font-semibold text-klein-blue">
          mini OpenClaw
        </div>
      </div>
      
      {/* 右侧链接 */}
      <div>
        <a
          href="https://fufan.ai"
          target="_blank"
          rel="noopener noreferrer"
          className="text-sm text-gray-600 hover:text-klein-blue transition-colors"
        >
          赋范空间
        </a>
      </div>
    </nav>
  );
}
