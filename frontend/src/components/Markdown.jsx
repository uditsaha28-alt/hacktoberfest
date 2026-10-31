import ReactMarkdown from "react-markdown";

// react-markdown does not render raw HTML by default, so LLM output can't inject markup.
// Links open in a new tab.
const components = {
  a: ({ node, ...props }) => <a {...props} target="_blank" rel="noreferrer noopener" />,
};

export default function Markdown({ children }) {
  return (
    <div className="md">
      <ReactMarkdown components={components}>{children}</ReactMarkdown>
    </div>
  );
}
