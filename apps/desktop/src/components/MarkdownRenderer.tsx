import React from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import rehypeRaw from "rehype-raw";

interface MarkdownRendererProps {
  content: string;
}

export const MarkdownRenderer: React.FC<MarkdownRendererProps> = ({ content }) => {
  return (
    <div className="prose-dark font-sans text-xs leading-relaxed text-slate-200 select-text overflow-hidden">
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        rehypePlugins={[rehypeRaw]}
        components={{
          // Headers
          h1: ({ children }) => (
            <h1 className="text-sm font-bold text-slate-100 mt-3 mb-1.5 first:mt-0 font-display">
              {children}
            </h1>
          ),
          h2: ({ children }) => (
            <h2 className="text-xs font-bold text-indigo-300 mt-2.5 mb-1 first:mt-0 font-display">
              {children}
            </h2>
          ),
          h3: ({ children }) => (
            <h3 className="text-xs font-semibold text-indigo-300 mt-2 mb-1 first:mt-0 font-display">
              {children}
            </h3>
          ),
          h4: ({ children }) => (
            <h4 className="text-[11px] font-semibold text-slate-300 mt-1.5 mb-0.5">
              {children}
            </h4>
          ),

          // Paragraphs & Inline Formatting
          p: ({ children }) => (
            <p className="mb-2 last:mb-0 leading-relaxed text-slate-200">{children}</p>
          ),
          strong: ({ children }) => (
            <strong className="font-semibold text-white tracking-tight">{children}</strong>
          ),
          em: ({ children }) => (
            <em className="italic text-slate-300">{children}</em>
          ),
          br: () => <br className="my-0.5" />,

          // Lists
          ul: ({ children }) => (
            <ul className="list-disc list-outside space-y-1.5 my-2 pl-4 text-slate-300">
              {children}
            </ul>
          ),
          ol: ({ children }) => (
            <ol className="list-decimal list-outside space-y-1.5 my-2 pl-4 text-slate-300">
              {children}
            </ol>
          ),
          li: ({ children }) => (
            <li className="text-slate-300 leading-relaxed">{children}</li>
          ),

          // Horizontal rule
          hr: () => <hr className="my-3 border-white/[0.08]" />,

          // Code blocks & Inline code
          code: ({ className, children, ...props }) => {
            const match = /language-(\w+)/.exec(className || "");
            const isInline = !match && !String(children).includes("\n");
            return isInline ? (
              <code
                className="px-1.5 py-0.5 rounded bg-[#080c14] border border-white/[0.08] text-indigo-300 font-mono text-[10px]"
                {...props}
              >
                {children}
              </code>
            ) : (
              <div className="my-2.5 rounded-lg bg-[#070b12] border border-white/[0.1] overflow-hidden shadow-inner">
                {match && (
                  <div className="px-3 py-1 bg-[#0f1422] border-b border-white/[0.06] text-[10px] font-mono text-slate-400">
                    {match[1]}
                  </div>
                )}
                <pre className="p-3 overflow-x-auto text-[11px] font-mono text-slate-200 scrollable">
                  <code>{children}</code>
                </pre>
              </div>
            );
          },

          // Tables (Rich GFM styling)
          table: ({ children }) => (
            <div className="my-3 overflow-x-auto rounded-lg border border-white/[0.1] bg-[#0c1220]/90 shadow-md">
              <table className="min-w-full text-left border-collapse text-[11px] font-sans">
                {children}
              </table>
            </div>
          ),
          thead: ({ children }) => (
            <thead className="bg-[#121a30] text-indigo-300 border-b border-white/[0.12] font-semibold text-[10.5px] uppercase tracking-wider">
              {children}
            </thead>
          ),
          tbody: ({ children }) => (
            <tbody className="divide-y divide-white/[0.06] text-slate-200">
              {children}
            </tbody>
          ),
          tr: ({ children }) => (
            <tr className="hover:bg-white/[0.03] transition-colors odd:bg-transparent even:bg-white/[0.01]">
              {children}
            </tr>
          ),
          th: ({ children }) => (
            <th className="px-3 py-2 font-semibold text-indigo-200 whitespace-nowrap">
              {children}
            </th>
          ),
          td: ({ children }) => (
            <td className="px-3 py-2 text-slate-300 align-top leading-relaxed">
              {children}
            </td>
          ),

          // Blockquotes
          blockquote: ({ children }) => (
            <blockquote className="border-l-2 border-indigo-500 pl-3 my-2 italic text-slate-400 bg-indigo-500/[0.03] py-1 rounded-r">
              {children}
            </blockquote>
          ),
        }}
      >
        {content || ""}
      </ReactMarkdown>
    </div>
  );
};

export default MarkdownRenderer;
