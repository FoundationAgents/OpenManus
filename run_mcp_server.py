# coding: utf-8
# A shortcut to launch OpenManus MCP server, where its introduction also solves other import issues.
from app.mcp.server import MCPServer, parse_args


if __name__ == "__main__":
    args = parse_args()

    # Create and run server with all transport options
    server = MCPServer()
    server.run(transport=args.transport, host=args.host, port=args.port)
