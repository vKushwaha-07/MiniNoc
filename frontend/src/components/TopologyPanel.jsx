import { useState, useEffect, useCallback, useMemo } from 'react';
import ReactFlow, {
    Controls,
    Background,
    useNodesState,
    useEdgesState,
    MarkerType,
    Handle,
    Position
} from 'reactflow';
import 'reactflow/dist/style.css';
import { ComputerDesktopIcon, ServerIcon, GlobeAltIcon } from '@heroicons/react/24/solid';
import * as api from '../services/api';

// --- Custom Nodes ---

const GatewayNode = ({ data }) => (
    <div className="px-4 py-2 shadow-lg rounded-md bg-white border-2 border-blue-500 min-w-[150px]">
        <Handle type="target" position={Position.Top} className="w-16 !bg-blue-500" />
        <div className="flex items-center">
            <div className="rounded-full w-10 h-10 flex items-center justify-center bg-blue-100 text-blue-600">
                <GlobeAltIcon className="w-6 h-6" />
            </div>
            <div className="ml-3">
                <div className="text-sm font-bold text-gray-900">Gateway</div>
                <div className="text-xs text-gray-500">router</div>
            </div>
        </div>
        <Handle type="source" position={Position.Bottom} className="w-16 !bg-blue-500" />
    </div>
);

const DeviceNode = ({ data }) => (
    <div className={`px-4 py-2 shadow-md rounded-md bg-white border-2 min-w-[180px] transition-all hover:shadow-xl ${data.status === 'UP' ? 'border-emerald-500' : 'border-red-500'
        }`}>
        <Handle type="target" position={Position.Top} className="!bg-gray-400" />
        <div className="flex items-center">
            <div className={`rounded-full w-10 h-10 flex items-center justify-center ${data.status === 'UP' ? 'bg-emerald-100 text-emerald-600' : 'bg-red-100 text-red-600'
                }`}>
                {data.role === 'server' ? <ServerIcon className="w-6 h-6" /> : <ComputerDesktopIcon className="w-6 h-6" />}
            </div>
            <div className="ml-3">
                <div className="text-sm font-bold text-gray-900 truncate max-w-[120px]" title={data.label}>
                    {data.label}
                </div>
                <div className="text-xs text-gray-500 font-mono">{data.ip}</div>
                {data.vendor && <div className="text-[10px] text-gray-400 truncate max-w-[120px]">{data.vendor}</div>}
            </div>
        </div>

        {/* Status Badge */}
        <div className={`absolute -top-2 -right-2 w-4 h-4 rounded-full border-2 border-white ${data.status === 'UP' ? 'bg-emerald-500' : 'bg-red-500'
            }`}></div>

        <Handle type="source" position={Position.Bottom} className="!bg-gray-400" />
    </div>
);

export function TopologyPanel() {
    const [nodes, setNodes, onNodesChange] = useNodesState([]);
    const [edges, setEdges, onEdgesChange] = useEdgesState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);

    const nodeTypes = useMemo(() => ({
        input: GatewayNode,
        default: DeviceNode,
    }), []);

    const fetchTopology = useCallback(async () => {
        setLoading(true);
        try {
            const data = await api.getTopology();

            // Map backend nodes to use our custom types and data structure
            const mappedNodes = data.nodes.map(node => ({
                ...node,
                type: node.type === 'input' ? 'input' : 'default', // Map to our custom types
                data: {
                    ...node.data,
                    label: node.label // Pass label to data for custom node to read
                }
            }));

            setNodes(mappedNodes);
            setEdges(data.edges.map(edge => ({
                ...edge,
                type: 'smoothstep', // Professional edge style
                animated: true,
                style: { stroke: edge.style?.stroke || '#b1b1b7', strokeWidth: 2 },
            })));
            setError(null);
        } catch (err) {
            setError(err.message);
        } finally {
            setLoading(false);
        }
    }, [setNodes, setEdges]);

    useEffect(() => {
        fetchTopology();
    }, [fetchTopology]);

    return (
        <div className="h-[600px] w-full bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden">
            <div className="p-4 border-b border-gray-100 flex justify-between items-center bg-gray-50">
                <h2 className="text-lg font-semibold text-gray-800">Network Topology</h2>
                <button
                    onClick={fetchTopology}
                    className="btn btn-sm bg-white border border-gray-300 hover:bg-gray-50 text-gray-700"
                >
                    ↻ Refresh Map
                </button>
            </div>

            {loading && nodes.length === 0 ? (
                <div className="h-full flex items-center justify-center">
                    <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
                </div>
            ) : error ? (
                <div className="h-full flex items-center justify-center p-6 text-red-600">
                    <p>Error loading topology: {error}</p>
                </div>
            ) : (
                <div className="h-[540px]">
                    <ReactFlow
                        nodes={nodes}
                        edges={edges}
                        onNodesChange={onNodesChange}
                        onEdgesChange={onEdgesChange}
                        nodeTypes={nodeTypes}
                        fitView
                        attributionPosition="bottom-right"
                    >
                        <Background color="#f1f5f9" gap={16} />
                        <Controls />
                    </ReactFlow>
                </div>
            )}
        </div>
    );
}

export default TopologyPanel;
