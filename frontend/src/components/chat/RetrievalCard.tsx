'use client';

import { useState } from 'react';
import { ChevronDown, ChevronUp, Sparkles } from 'lucide-react';

interface Retrieval {
  text: string;
  score: number;
  source: string;
}

interface RetrievalCardProps {
  retrievals: Retrieval[];
}

export default function RetrievalCard({ retrievals }: RetrievalCardProps) {
  const [isExpanded, setIsExpanded] = useState(false);
  
  return (
    <div className="bg-purple-50 border border-purple-200 rounded-lg overflow-hidden">
      {/* 头部 */}
      <div
        className="px-4 py-3 flex items-center justify-between cursor-pointer hover:bg-purple-100 transition-colors"
        onClick={() => setIsExpanded(!isExpanded)}
      >
        <div className="flex items-center space-x-2">
          <Sparkles size={16} className="text-purple-600" />
          <span className="text-sm font-medium text-purple-900">
            记忆检索 ({retrievals.length})
          </span>
        </div>
        
        {isExpanded ? (
          <ChevronUp size={18} className="text-purple-600" />
        ) : (
          <ChevronDown size={18} className="text-purple-600" />
        )}
      </div>
      
      {/* 详情 */}
      {isExpanded && (
        <div className="border-t border-purple-200 p-4 space-y-3">
          {retrievals.map((retrieval, index) => (
            <div key={index} className="bg-white border border-purple-200 rounded p-3">
              <div className="flex items-center justify-between mb-2">
                <span className="text-xs text-purple-600 font-medium">
                  {retrieval.source}
                </span>
                <span className="text-xs text-gray-500">
                  相关度: {retrieval.score.toFixed(3)}
                </span>
              </div>
              
              <div className="text-sm text-gray-700 line-clamp-4">
                {retrieval.text}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
