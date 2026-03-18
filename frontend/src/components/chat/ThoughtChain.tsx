'use client';

import { useState } from 'react';
import { ChevronDown, ChevronUp, Wrench } from 'lucide-react';

interface ToolCall {
  tool: string;
  input: string;
  output: string;
}

interface ThoughtChainProps {
  toolCalls: ToolCall[];
}

export default function ThoughtChain({ toolCalls }: ThoughtChainProps) {
  const [isExpanded, setIsExpanded] = useState(false);
  
  return (
    <div className="bg-amber-50 border border-amber-200 rounded-lg overflow-hidden">
      {/* 头部 */}
      <div
        className="px-4 py-3 flex items-center justify-between cursor-pointer hover:bg-amber-100 transition-colors"
        onClick={() => setIsExpanded(!isExpanded)}
      >
        <div className="flex items-center space-x-2">
          <Wrench size={16} className="text-amber-600" />
          <span className="text-sm font-medium text-amber-900">
            工具调用 ({toolCalls.length})
          </span>
        </div>
        
        {isExpanded ? (
          <ChevronUp size={18} className="text-amber-600" />
        ) : (
          <ChevronDown size={18} className="text-amber-600" />
        )}
      </div>
      
      {/* 详情 */}
      {isExpanded && (
        <div className="border-t border-amber-200 p-4 space-y-3">
          {toolCalls.map((call, index) => (
            <div key={index} className="bg-white border border-amber-200 rounded p-3">
              <div className="text-sm font-medium text-amber-900 mb-2">
                {call.tool}
              </div>
              
              <div className="text-xs space-y-2">
                <div>
                  <span className="text-gray-500">输入：</span>
                  <div className="mt-1 p-2 bg-gray-50 rounded font-mono text-gray-700 break-all">
                    {call.input}
                  </div>
                </div>
                
                {call.output && (
                  <div>
                    <span className="text-gray-500">输出：</span>
                    <div className="mt-1 p-2 bg-gray-50 rounded font-mono text-gray-700 break-all max-h-32 overflow-y-auto">
                      {call.output}
                    </div>
                  </div>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
