import { useState } from 'react';
import { api } from '../services/api';
import ReactMarkdown from 'react-markdown';

interface ChatMessage {
  role: 'system' | 'user' | 'assistant';
  content: string;
  sources?: string[]; // Added to store the PDF citations from the backend
}

export default function Assistant() {
  const [input, setInput] = useState('');
  const [isTyping, setIsTyping] = useState(false);

  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      role: 'system',
      content: 'I am the FlameSync AI Assistant. I can analyze n-Heptane burn rates, cross-reference microgravity datasets, or summarize findings from the BASS-II and FLEX investigations. How can I assist your mission analysis today?'
    }
  ]);

  const handleSend = async () => {
    if (!input.trim()) return;

    // Add user message
    const userMessage = input;
    const newMessages: ChatMessage[] = [...messages, { role: 'user', content: userMessage }];
    setMessages(newMessages);
    setInput('');
    setIsTyping(true);

    try {
      // Call the FastAPI RAG endpoint
      const data = await api.post('/assistant/chat', { query: userMessage });

      setMessages([...newMessages, {
        role: 'assistant',
        content: data.answer,
        sources: data.sources
      }]);
    } catch (err) {
      console.error("Chat failed:", err);
      setMessages([...newMessages, {
        role: 'assistant',
        content: 'Error: Unable to reach the FlameSync vector database. Please ensure the backend is running.'
      }]);
    } finally {
      setIsTyping(false);
    }
  };

  return (
    <div className="flex flex-col h-full max-w-7xl mx-auto font-mono selection:bg-[#FF5500] selection:text-white gap-6 overflow-hidden">

      {/* Header */}
      <div className="shrink-0">
        <h1 className="text-xl font-bold text-white tracking-[0.2em] uppercase mb-1">Ask FlameSync</h1>
        <p className="text-gray-400 text-[10px] font-sans">Get evidence-based answers from the research database.</p>
      </div>

      {/* Main Chat Interface */}
      <div className="flex-1 bg-[#050505] border border-[#1a1a1a] rounded-xl flex flex-col overflow-hidden min-h-0 shadow-[0_0_15px_rgba(0,0,0,0.5)]">

        {/* Scrollable Message Log */}
        <div className="flex-1 p-6 overflow-y-auto flex flex-col gap-6">
          {messages.map((msg, idx) => (
            <div key={idx} className={`flex gap-4 max-w-[85%] ${msg.role === 'user' ? 'ml-auto justify-end' : ''}`}>

              {/* Avatar for System/Assistant */}
              {msg.role !== 'user' && (
                <div className="w-8 h-8 rounded border border-[#FF5500]/30 bg-[#FF5500]/5 flex items-center justify-center shrink-0">
                  <svg className="w-4 h-4 text-[#FF5500]" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
                    <path d="M12 2c0 0-4 3.2-6 8.5C6 15.3 9.4 19 12 22c2.6-3 6-6.7 6-11.5C18 5.2 14 2 14 2s-1.5 2.5-2 2.5S12 2 12 2zm0 15.5c-2.3 0-3.5-2.2-3.5-2.2 1.5.5 3 .5 3.5-.5 0 0 1.2 2.7 0 2.7z" />
                  </svg>
                </div>
              )}

              {/* Message Bubble */}
              <div className={`border p-4 rounded-xl text-[11px] font-sans leading-relaxed ${msg.role === 'user'
                ? 'bg-[#0a0a0a] border-[#1a1a1a] text-gray-300 rounded-tr-sm'
                : 'bg-black border-[#1a1a1a] text-gray-400 rounded-tl-sm w-full'
                }`}>
                {msg.role === 'system' && <span className="text-[#FF5500] font-mono mb-2 block text-[10px] tracking-widest">// SYSTEM INITIALIZED</span>}

                {/* NEW STUFF: Render the markdown answer with Tailwind Typography */}
                <div className="prose prose-invert prose-sm max-w-none text-gray-300">
                  <ReactMarkdown>{msg.content}</ReactMarkdown>
                </div>

                {/* Render citations if they exist */}
                {msg.sources && msg.sources.length > 0 && (
                  <div className="mt-4 pt-3 border-t border-[#1a1a1a] flex flex-col gap-1">
                    <span className="text-[#FF5500] font-mono text-[9px] tracking-widest uppercase">Sources:</span>
                    <div className="flex flex-wrap gap-2">
                      {msg.sources.map((src, i) => (
                        /^https?:\/\//i.test(src) ? (
                          <a
                            key={i}
                            href={src}
                            target="_blank"
                            rel="noreferrer"
                            className="px-2 py-1 bg-[#1a1a1a] rounded text-[9px] text-gray-400 font-mono hover:text-[#FF5500] break-all"
                          >
                            {src}
                          </a>
                        ) : (
                          <span key={i} className="px-2 py-1 bg-[#1a1a1a] rounded text-[9px] text-gray-400 font-mono">
                            {src}
                          </span>
                        )
                      ))}
                    </div>
                  </div>
                )}
              </div>
            </div>
          ))}
          {isTyping && (
            <div className="flex gap-4 max-w-[85%]">
               <div className="w-8 h-8 rounded border border-[#FF5500]/30 bg-[#FF5500]/5 shrink-0" />
               <div className="text-gray-500 text-[10px] italic">Assistant is generating...</div>
            </div>
          )}
        </div>

        {/* Input Area */}
        <div className="p-4 border-t border-[#1a1a1a] bg-[#050505]">
          <div className="flex gap-4">
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && handleSend()}
              placeholder="Ask a follow-up question..."
              className="flex-1 bg-black border border-[#1a1a1a] rounded-lg px-4 py-3 text-sm text-gray-300 focus:outline-none focus:border-[#FF5500] transition-colors"
            />
            <button
              onClick={handleSend}
              disabled={isTyping}
              className="px-6 py-3 bg-[#FF5500] text-black font-bold text-sm rounded-lg hover:bg-[#ff7733] transition-colors disabled:opacity-50"
            >
              SEND
            </button>
          </div>
        </div>

      </div>
    </div>
  );
}