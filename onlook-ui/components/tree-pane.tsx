import { collectTreeStats } from "@/lib/review-adapter";
import type { ReviewTreeNode } from "@/lib/review-types";

type TreePaneProps = {
  root: ReviewTreeNode | null;
  selectedTreeId: string | null;
  onSelectTree: (treeId: string) => void;
};

type TreeBranchProps = {
  node: ReviewTreeNode;
  depth: number;
  selectedTreeId: string | null;
  onSelectTree: (treeId: string) => void;
};

function TreeBranch({
  node,
  depth,
  selectedTreeId,
  onSelectTree,
}: TreeBranchProps) {
  const selected = selectedTreeId === node.tree_id;

  return (
    <li className="space-y-2">
      <button
        type="button"
        className={`flex w-full items-center gap-2 rounded-xl px-3 py-2 text-left text-sm transition hover:bg-slate-100 ${selected ? "bg-sky-50 text-sky-900 ring-1 ring-sky-200" : "text-slate-700"}`}
        style={{ paddingLeft: `${depth * 0.9 + 0.75}rem` }}
        onClick={() => onSelectTree(node.tree_id)}
      >
        <span className="w-14 shrink-0 text-[11px] font-semibold uppercase tracking-[0.12em] text-slate-400">
          {node.is_dir ? "dir" : "file"}
        </span>
        <span className="min-w-0 truncate">{node.name}</span>
      </button>
      {node.children && node.children.length > 0 ? (
        <ul className="space-y-1">
          {node.children.map((child) => (
            <TreeBranch
              key={child.tree_id}
              node={child}
              depth={depth + 1}
              selectedTreeId={selectedTreeId}
              onSelectTree={onSelectTree}
            />
          ))}
        </ul>
      ) : null}
    </li>
  );
}

export function TreePane({
  root,
  selectedTreeId,
  onSelectTree,
}: TreePaneProps) {
  const stats = root ? collectTreeStats(root) : null;

  return (
    <section className="flex min-h-[24rem] flex-col rounded-3xl border border-slate-200 bg-white shadow-sm">
      <div className="border-b border-slate-200 px-5 py-4">
        <div className="flex items-center justify-between gap-3">
          <div>
            <h2 className="text-lg font-semibold text-slate-950">Tree pane</h2>
            <p className="mt-1 text-sm text-slate-600">
              Strict filesystem tree from the overview payload.
            </p>
          </div>
          {stats ? (
            <div className="text-right text-xs text-slate-500">
              <div>{stats.directories} directories</div>
              <div>{stats.files} files</div>
            </div>
          ) : null}
        </div>
      </div>

      {!root ? (
        <div className="flex flex-1 items-center justify-center px-5 py-12 text-sm text-slate-500">
          Load an overview to inspect the runtime tree.
        </div>
      ) : (
        <div className="flex-1 overflow-auto px-3 py-4">
          <ul className="space-y-1">
            <TreeBranch
              node={root}
              depth={0}
              selectedTreeId={selectedTreeId}
              onSelectTree={onSelectTree}
            />
          </ul>
        </div>
      )}
    </section>
  );
}
