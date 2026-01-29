/**
 * Monaco-based code editor for Vegas (.vg) files.
 */
import { useRef } from 'react';
import Editor, { OnMount, BeforeMount } from '@monaco-editor/react';
import type { editor } from 'monaco-editor';
import { registerVegasLanguage, vegasLanguageId } from '../../languages/vegas';

interface CodeEditorProps {
  /** Initial code content */
  value: string;
  /** Callback when content changes */
  onChange?: (value: string) => void;
  /** File language (defaults to vegas) */
  language?: string;
  /** Read-only mode */
  readOnly?: boolean;
  /** Editor height */
  height?: string | number;
}

export function CodeEditor({
  value,
  onChange,
  language = vegasLanguageId,
  readOnly = false,
  height = '100%',
}: CodeEditorProps) {
  const editorRef = useRef<editor.IStandaloneCodeEditor | null>(null);

  // Register Vegas language before Monaco mounts
  const handleBeforeMount: BeforeMount = (monaco) => {
    registerVegasLanguage(monaco);
  };

  // Store editor reference on mount
  const handleMount: OnMount = (editor) => {
    editorRef.current = editor;
  };

  // Handle content changes
  const handleChange = (newValue: string | undefined) => {
    if (onChange && newValue !== undefined) {
      onChange(newValue);
    }
  };

  return (
    <div className="code-editor" style={{ height, width: '100%' }}>
      <Editor
        height="100%"
        language={language}
        value={value}
        theme="vegas-dark"
        beforeMount={handleBeforeMount}
        onMount={handleMount}
        onChange={handleChange}
        options={{
          readOnly,
          minimap: { enabled: false },
          fontSize: 14,
          lineNumbers: 'on',
          scrollBeyondLastLine: false,
          wordWrap: 'on',
          automaticLayout: true,
          tabSize: 2,
          renderWhitespace: 'selection',
          bracketPairColorization: { enabled: true },
        }}
      />
    </div>
  );
}
