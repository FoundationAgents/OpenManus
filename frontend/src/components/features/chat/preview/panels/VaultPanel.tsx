/**
 * VaultPanel — Force-directed graph visualization for Obsidian vault notes.
 *
 * Replaces the old two-number summary card with an interactive canvas graph
 * showing notes as nodes and wikilinks as edges, plus an import button.
 */
import { useCallback, useEffect, useRef, useState } from 'react';
import { useAsync } from '@/hooks/use-async';
import { getObsidianGraph, importObsidianNotes, type ObsidianGraph } from '@/services/conversations';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface SimNode {
  id: string;
  title: string;
  path: string;
  tags: string[];
  x: number;
  y: number;
  vx: number;
  vy: number;
  linkCount: number;
}

interface SimEdge {
  source: string;
  target: string;
  relation: string;
}

// ---------------------------------------------------------------------------
// Force simulation (lightweight, no dependency)
// ---------------------------------------------------------------------------

function initSimulation(graph: ObsidianGraph, width: number, height: number) {
  const nodeMap = new Map<string, SimNode>();
  // Count links per node for sizing
  const linkCounts = new Map<string, number>();
  for (const edge of graph.edges) {
    linkCounts.set(edge.source, (linkCounts.get(edge.source) || 0) + 1);
    linkCounts.set(edge.target, (linkCounts.get(edge.target) || 0) + 1);
  }

  const nodes: SimNode[] = graph.nodes.map((n, i) => {
    const angle = (2 * Math.PI * i) / Math.max(graph.nodes.length, 1);
    const radius = Math.min(width, height) * 0.3;
    return {
      id: n.id,
      title: n.title,
      path: n.path,
      tags: n.tags || [],
      x: width / 2 + Math.cos(angle) * radius + (Math.random() - 0.5) * 40,
      y: height / 2 + Math.sin(angle) * radius + (Math.random() - 0.5) * 40,
      vx: 0,
      vy: 0,
      linkCount: linkCounts.get(n.id) || 0,
    };
  });

  for (const n of nodes) nodeMap.set(n.id, n);

  const edges: SimEdge[] = graph.edges
    .filter(e => nodeMap.has(e.source) && nodeMap.has(e.target))
    .map(e => ({ source: e.source, target: e.target, relation: e.relation }));

  return { nodes, edges, nodeMap };
}

function tickSimulation(
  nodes: SimNode[],
  edges: SimEdge[],
  nodeMap: Map<string, SimNode>,
  width: number,
  height: number,
  alpha: number,
) {
  const cx = width / 2;
  const cy = height / 2;

  // Repulsion (charge)
  for (let i = 0; i < nodes.length; i++) {
    for (let j = i + 1; j < nodes.length; j++) {
      const a = nodes[i];
      const b = nodes[j];
      let dx = b.x - a.x;
      let dy = b.y - a.y;
      const dist = Math.sqrt(dx * dx + dy * dy) || 1;
      const force = (800 / (dist * dist)) * alpha;
      dx = (dx / dist) * force;
      dy = (dy / dist) * force;
      a.vx -= dx;
      a.vy -= dy;
      b.vx += dx;
      b.vy += dy;
    }
  }

  // Attraction (spring)
  for (const edge of edges) {
    const a = nodeMap.get(edge.source);
    const b = nodeMap.get(edge.target);
    if (!a || !b) continue;
    const dx = b.x - a.x;
    const dy = b.y - a.y;
    const dist = Math.sqrt(dx * dx + dy * dy) || 1;
    const force = ((dist - 100) * 0.004) * alpha;
    const fx = (dx / dist) * force;
    const fy = (dy / dist) * force;
    a.vx += fx;
    a.vy += fy;
    b.vx -= fx;
    b.vy -= fy;
  }

  // Center gravity
  for (const n of nodes) {
    n.vx += (cx - n.x) * 0.002 * alpha;
    n.vy += (cy - n.y) * 0.002 * alpha;
  }

  // Apply velocity + damping
  for (const n of nodes) {
    n.vx *= 0.85;
    n.vy *= 0.85;
    n.x += n.vx;
    n.y += n.vy;
    // Bounds
    n.x = Math.max(20, Math.min(width - 20, n.x));
    n.y = Math.max(20, Math.min(height - 20, n.y));
  }
}

// ---------------------------------------------------------------------------
// Color palette
// ---------------------------------------------------------------------------

const NODE_COLORS = {
  default: '#6366f1',     // indigo
  autoSync: '#22d3ee',    // cyan
  imported: '#a78bfa',    // violet
  selected: '#f59e0b',    // amber
};

function nodeColor(node: SimNode, selectedId: string | null): string {
  if (node.id === selectedId) return NODE_COLORS.selected;
  if (node.path.includes('workspace-auto-sync')) return NODE_COLORS.autoSync;
  return NODE_COLORS.imported;
}

function nodeRadius(node: SimNode): number {
  return Math.min(6 + node.linkCount * 1.5, 18);
}

// ---------------------------------------------------------------------------
// Canvas drawing
// ---------------------------------------------------------------------------

function drawGraph(
  ctx: CanvasRenderingContext2D,
  nodes: SimNode[],
  edges: SimEdge[],
  nodeMap: Map<string, SimNode>,
  selectedId: string | null,
  width: number,
  height: number,
  dpr: number,
) {
  ctx.clearRect(0, 0, width * dpr, height * dpr);
  ctx.save();
  ctx.scale(dpr, dpr);

  // Edges
  ctx.lineWidth = 1;
  ctx.strokeStyle = 'rgba(148, 163, 184, 0.35)';
  for (const edge of edges) {
    const a = nodeMap.get(edge.source);
    const b = nodeMap.get(edge.target);
    if (!a || !b) continue;
    ctx.beginPath();
    ctx.moveTo(a.x, a.y);
    ctx.lineTo(b.x, b.y);
    ctx.stroke();
  }

  // Nodes
  for (const node of nodes) {
    const r = nodeRadius(node);
    const color = nodeColor(node, selectedId);

    // Glow for selected
    if (node.id === selectedId) {
      ctx.shadowColor = color;
      ctx.shadowBlur = 12;
    }

    ctx.beginPath();
    ctx.arc(node.x, node.y, r, 0, Math.PI * 2);
    ctx.fillStyle = color;
    ctx.fill();

    ctx.shadowColor = 'transparent';
    ctx.shadowBlur = 0;

    // Label
    ctx.font = '11px Inter, system-ui, sans-serif';
    ctx.fillStyle = '#e2e8f0';
    ctx.textAlign = 'center';
    ctx.fillText(node.title, node.x, node.y + r + 13, 120);
  }

  ctx.restore();
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export const VaultPanel = ({ conversationId }: { conversationId: string }) => {
  const { data: graph, isLoading, refresh } = useAsync(
    async () => getObsidianGraph(conversationId),
    [],
    { deps: [conversationId] },
  );

  const canvasRef = useRef<HTMLCanvasElement>(null);
  const simRef = useRef<ReturnType<typeof initSimulation> | null>(null);
  const animRef = useRef<number>(0);
  const alphaRef = useRef(1);
  const [selectedNode, setSelectedNode] = useState<SimNode | null>(null);
  const [importing, setImporting] = useState(false);

  const lastSync = graph?.nodes
    ?.map(n => n.updated_at)
    .filter(Boolean)
    .sort()
    .at(-1) ?? null;

  // Initialize simulation when graph data changes
  useEffect(() => {
    if (!graph || !graph.nodes.length || !canvasRef.current) return;
    const canvas = canvasRef.current;
    const rect = canvas.getBoundingClientRect();
    const w = rect.width || 600;
    const h = rect.height || 400;
    const dpr = window.devicePixelRatio || 1;
    canvas.width = w * dpr;
    canvas.height = h * dpr;

    const sim = initSimulation(graph, w, h);
    simRef.current = sim;
    alphaRef.current = 1;

    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    function animate() {
      if (!simRef.current || alphaRef.current < 0.01) return;
      tickSimulation(simRef.current.nodes, simRef.current.edges, simRef.current.nodeMap, w, h, alphaRef.current);
      drawGraph(ctx!, simRef.current.nodes, simRef.current.edges, simRef.current.nodeMap, selectedNode?.id ?? null, w, h, dpr);
      alphaRef.current *= 0.99;
      animRef.current = requestAnimationFrame(animate);
    }
    animate();

    return () => cancelAnimationFrame(animRef.current);
  }, [graph, selectedNode]);

  // Click handler for node selection
  const handleCanvasClick = useCallback((e: React.MouseEvent<HTMLCanvasElement>) => {
    if (!simRef.current || !canvasRef.current) return;
    const rect = canvasRef.current.getBoundingClientRect();
    const mx = e.clientX - rect.left;
    const my = e.clientY - rect.top;

    let closest: SimNode | null = null;
    let minDist = Infinity;
    for (const node of simRef.current.nodes) {
      const dx = node.x - mx;
      const dy = node.y - my;
      const dist = Math.sqrt(dx * dx + dy * dy);
      const r = nodeRadius(node);
      if (dist < r + 8 && dist < minDist) {
        closest = node;
        minDist = dist;
      }
    }
    setSelectedNode(closest);
    // Re-render with selection highlight
    alphaRef.current = Math.max(alphaRef.current, 0.02);
    if (canvasRef.current) {
      const ctx = canvasRef.current.getContext('2d');
      const rect2 = canvasRef.current.getBoundingClientRect();
      const dpr = window.devicePixelRatio || 1;
      if (ctx && simRef.current) {
        drawGraph(ctx, simRef.current.nodes, simRef.current.edges, simRef.current.nodeMap, closest?.id ?? null, rect2.width, rect2.height, dpr);
      }
    }
  }, []);

  // Import handler
  const handleImport = useCallback(async () => {
    const input = document.createElement('input');
    input.type = 'file';
    input.multiple = true;
    input.accept = '.md';
    input.webkitdirectory = true;

    input.onchange = async () => {
      if (!input.files?.length) return;
      setImporting(true);
      try {
        const notes: Array<{ path: string; title: string; content: string; tags: string[] }> = [];
        for (const file of Array.from(input.files)) {
          if (!file.name.endsWith('.md')) continue;
          const content = await file.text();
          const path = file.webkitRelativePath || file.name;
          const title = file.name.replace(/\.md$/, '');
          // Extract tags
          const tagMatches = content.match(/(^|\s)#([A-Za-z0-9_\-/]+)/g) || [];
          const tags = tagMatches.map(t => t.trim().replace(/^#/, '')).filter(Boolean);
          notes.push({ path, title, content, tags });
        }
        if (notes.length > 0) {
          await importObsidianNotes(conversationId, notes);
          refresh();
        }
      } catch (err) {
        console.error('Vault import failed:', err);
      } finally {
        setImporting(false);
      }
    };
    input.click();
  }, [conversationId, refresh]);

  // Compute connected nodes for selected
  const connectedIds = new Set<string>();
  if (selectedNode && graph) {
    for (const edge of graph.edges) {
      if (edge.source === selectedNode.id) connectedIds.add(edge.target);
      if (edge.target === selectedNode.id) connectedIds.add(edge.source);
    }
  }

  return (
    <div className="flex h-full min-h-0 flex-col gap-3 p-4">
      {/* Stats bar */}
      <div className="flex items-center justify-between gap-2">
        <div className="flex items-center gap-3">
          <Badge variant="outline" className="font-mono">
            {graph?.node_count ?? 0} notes
          </Badge>
          <Badge variant="outline" className="font-mono">
            {graph?.edge_count ?? 0} links
          </Badge>
          {lastSync && (
            <span className="text-muted-foreground text-xs">
              Last sync: {new Date(lastSync).toLocaleString()}
            </span>
          )}
        </div>
        <button
          onClick={handleImport}
          disabled={importing}
          className="rounded-md border border-indigo-500/30 bg-indigo-500/10 px-3 py-1 text-xs font-medium text-indigo-400 transition hover:bg-indigo-500/20 disabled:opacity-50"
        >
          {importing ? 'Importing…' : 'Import Vault'}
        </button>
      </div>

      {/* Main content */}
      <Card className="flex min-h-0 flex-1 flex-col overflow-hidden">
        <CardHeader className="pb-2">
          <CardTitle className="text-base">Knowledge Graph</CardTitle>
          <CardDescription>
            Obsidian vault notes and wikilink connections. Click a node to inspect.
          </CardDescription>
        </CardHeader>
        <CardContent className="relative min-h-0 flex-1">
          {isLoading ? (
            <div className="text-muted-foreground flex h-full items-center justify-center text-sm">
              Loading vault graph…
            </div>
          ) : !graph?.nodes.length ? (
            <div className="text-muted-foreground flex h-full flex-col items-center justify-center gap-2 text-sm">
              <span>No notes in this conversation yet.</span>
              <span className="text-xs">
                Use <strong>Import Vault</strong> to load your Obsidian vault, or notes will appear automatically from agent workspace files.
              </span>
            </div>
          ) : (
            <div className="flex h-full min-h-0 gap-3">
              {/* Canvas */}
              <canvas
                ref={canvasRef}
                onClick={handleCanvasClick}
                className="min-h-0 flex-1 cursor-crosshair rounded-md border border-slate-700/50"
                style={{ background: 'rgba(15, 23, 42, 0.6)' }}
              />

              {/* Detail sidebar */}
              {selectedNode && (
                <div className="flex w-56 flex-col gap-2 overflow-auto rounded-md border border-slate-700/50 p-3">
                  <div className="text-sm font-semibold text-amber-400">{selectedNode.title}</div>
                  <div className="text-muted-foreground truncate font-mono text-xs">{selectedNode.path}</div>
                  {selectedNode.tags.length > 0 && (
                    <div className="flex flex-wrap gap-1">
                      {selectedNode.tags.slice(0, 8).map(tag => (
                        <Badge key={tag} variant="secondary" className="text-xs">
                          #{tag}
                        </Badge>
                      ))}
                    </div>
                  )}
                  <div className="text-muted-foreground text-xs">
                    {connectedIds.size} connection{connectedIds.size !== 1 ? 's' : ''}
                  </div>
                  {connectedIds.size > 0 && (
                    <div className="space-y-1">
                      <div className="text-muted-foreground text-xs font-medium">Linked to:</div>
                      {Array.from(connectedIds).slice(0, 12).map(id => {
                        const linked = graph?.nodes.find(n => n.id === id);
                        return linked ? (
                          <div
                            key={id}
                            className="cursor-pointer truncate text-xs text-indigo-400 hover:underline"
                            onClick={() => {
                              const simNode = simRef.current?.nodeMap.get(id);
                              if (simNode) setSelectedNode(simNode);
                            }}
                          >
                            {linked.title}
                          </div>
                        ) : null;
                      })}
                    </div>
                  )}
                </div>
              )}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
};
