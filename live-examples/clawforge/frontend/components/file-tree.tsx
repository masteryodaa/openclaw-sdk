import type { GeneratedFile } from "@/lib/types";

interface FileTreeProps {
  files: GeneratedFile[];
  onSelect: (file: GeneratedFile) => void;
  selected?: string;
}

export function FileTree({ files, onSelect, selected }: FileTreeProps) {
  return (
    <div className="space-y-0.5 py-2">
      {files.map((file) => (
        <button
          key={file.id}
          onClick={() => onSelect(file)}
          className={`flex w-full items-center gap-2 rounded px-3 py-1.5 text-left text-sm transition-colors ${
            selected === file.id
              ? "bg-emerald-500/10 text-emerald-400"
              : "text-zinc-300 hover:bg-zinc-800"
          }`}
        >
          <span className="text-xs">&#x1f4c4;</span>
          <span className="truncate font-mono text-xs">{file.path || file.name}</span>
          <span className="ml-auto text-xs text-zinc-600">
            {file.size_bytes > 0 ? `${(file.size_bytes / 1024).toFixed(1)}KB` : ""}
          </span>
        </button>
      ))}
    </div>
  );
}
