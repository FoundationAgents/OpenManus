# FreEco.ai MCP Server Guide

**Model Context Protocol (MCP) Integration for FreEco.ai Platform**

---

## 🌟 Overview

FreEco.ai now functions as a powerful **MCP server** that exposes its advanced AI tools to MCP-compatible clients like Claude Desktop, Cline, and other AI assistants.

With this integration, you can use FreEco.ai's capabilities directly from your favorite AI interface!

---

## 🛠️ Available Tools

### Standard Tools
1. **bash** - Execute shell commands
2. **browser** - Web browsing and automation
3. **editor** - File editing with str_replace
4. **terminate** - Task termination

### Enhancement #4 Tools (Multimodal & Integrations)
5. **youtube** - YouTube transcript extraction
6. **knowledge_base** - Vector database for RAG
7. **notion** - Notion workspace integration
8. **crm** - CRM management (Twenty, HubSpot, Salesforce, Pipedrive, KeyCRM)

---

## 📦 Installation

### 1. Install Dependencies

```bash
cd /path/to/FreEco-Platform
pip install -r requirements.txt
```

### 2. Configure Environment Variables

Create a `.env` file or export variables:

```bash
# Required for Knowledge Base
export OPENAI_API_KEY="sk-..."

# Optional: Notion Integration
export NOTION_API_KEY="secret_..."

# Optional: CRM Integration
export CRM_TYPE="keycrm"  # or "twenty", "hubspot", "salesforce", "pipedrive"
export KEYCRM_API_KEY="your-keycrm-api-key"

# Optional: Twenty CRM
export TWENTY_API_KEY="your-twenty-api-key"
export TWENTY_API_URL="http://localhost:3000/graphql"

# Optional: HubSpot
export HUBSPOT_API_KEY="your-hubspot-key"

# Optional: Salesforce
export SALESFORCE_ACCESS_TOKEN="your-salesforce-token"
export SALESFORCE_INSTANCE_URL="https://your-instance.salesforce.com"

# Optional: Pipedrive
export PIPEDRIVE_API_TOKEN="your-pipedrive-token"
```

### 3. Test the Server

```bash
python run_mcp_server.py
```

You should see:
```
INFO:app.logger:Registered tool: bash
INFO:app.logger:Registered tool: browser
INFO:app.logger:Registered tool: editor
INFO:app.logger:Registered tool: terminate
INFO:app.logger:Registered tool: youtube
INFO:app.logger:Registered tool: knowledge_base
INFO:app.logger:Registered tool: notion
INFO:app.logger:Registered tool: crm
```

---

## 🔧 Client Configuration

### Claude Desktop

**Location**: `~/Library/Application Support/Claude/claude_desktop_config.json` (macOS)

```json
{
  "mcpServers": {
    "freeco-ai": {
      "command": "python",
      "args": ["/absolute/path/to/FreEco-Platform/run_mcp_server.py"],
      "env": {
        "OPENAI_API_KEY": "sk-...",
        "KEYCRM_API_KEY": "your-keycrm-key",
        "NOTION_API_KEY": "secret_...",
        "CRM_TYPE": "keycrm"
      }
    }
  }
}
```

**After configuration:**
1. Restart Claude Desktop
2. Look for the 🔌 icon in the bottom-right
3. You should see "freeco-ai" listed with 8 tools

### Cline (VS Code Extension)

**Location**: VS Code Settings → Extensions → Cline → MCP Servers

```json
{
  "freeco-ai": {
    "command": "python",
    "args": ["/absolute/path/to/FreEco-Platform/run_mcp_server.py"],
    "env": {
      "OPENAI_API_KEY": "sk-...",
      "KEYCRM_API_KEY": "your-keycrm-key"
    }
  }
}
```

### Continue.dev

**Location**: `~/.continue/config.json`

```json
{
  "mcpServers": [
    {
      "name": "freeco-ai",
      "command": "python",
      "args": ["/absolute/path/to/FreEco-Platform/run_mcp_server.py"],
      "env": {
        "OPENAI_API_KEY": "sk-...",
        "KEYCRM_API_KEY": "your-keycrm-key"
      }
    }
  ]
}
```

---

## 💡 Usage Examples

### Example 1: YouTube → Knowledge Base

**In Claude Desktop:**

> "Use the youtube tool to get the transcript of video ID 'dQw4w9WgXcQ', then add it to the knowledge_base"

FreEco.ai will:
1. Extract the YouTube transcript
2. Store it in the vector database
3. Make it searchable for future queries

### Example 2: CRM Contact Management

**In Claude Desktop:**

> "Use the crm tool to create a contact named 'John Doe' with email 'john@example.com' in KeyCRM"

FreEco.ai will:
1. Connect to KeyCRM API
2. Create the contact
3. Return the contact ID

### Example 3: Notion Automation

**In Claude Desktop:**

> "Search my Notion workspace for 'project roadmap' and create a summary page"

FreEco.ai will:
1. Search Notion for relevant pages
2. Extract content
3. Create a new summary page

### Example 4: Knowledge Base RAG

**In Claude Desktop:**

> "Search the knowledge_base for information about 'AI agent frameworks'"

FreEco.ai will:
1. Perform semantic search
2. Return top 5 relevant results
3. Provide context for your question

---

## 🔍 Tool Details

### YouTube Tool

**Actions:**
- `get_transcript` - Extract transcript from video
- `get_metadata` - Get video metadata
- `add_to_knowledge_base` - Store transcript in knowledge base

**Example:**
```json
{
  "action": "get_transcript",
  "video_id": "dQw4w9WgXcQ",
  "include_metadata": true
}
```

### Knowledge Base Tool

**Actions:**
- `add` - Add content to knowledge base
- `search` - Semantic search
- `list` - List all entries
- `delete` - Remove entry
- `stats` - Get statistics

**Example:**
```json
{
  "action": "search",
  "query": "What is FreEco.ai?",
  "top_k": 5
}
```

### Notion Tool

**Actions:**
- `create_page` - Create new page
- `read_page` - Read page content
- `update_page` - Update existing page
- `search` - Search workspace
- `add_to_knowledge` - Add page to knowledge base

**Example:**
```json
{
  "action": "create_page",
  "database_id": "your-database-id",
  "title": "Meeting Notes",
  "content": "# Key Points\n- Discussed roadmap"
}
```

### CRM Tool

**Actions:**
- `create_contact` - Create new contact
- `update_contact` - Update contact
- `search_contacts` - Search contacts
- `create_deal` - Create new deal
- `get_pipeline` - View sales pipeline
- `get_insights` - AI-powered insights

**Example:**
```json
{
  "action": "create_contact",
  "name": "Jane Smith",
  "email": "jane@example.com",
  "company": "Acme Corp"
}
```

---

## 🚀 Advanced Configuration

### Custom Server Name

```python
# In run_mcp_server.py
server = MCPServer(name="my-custom-name")
```

### Adding Custom Tools

```python
# In app/mcp/server.py, __init__ method
from app.tool.my_custom_tool import MyCustomTool

self.tools["my_tool"] = MyCustomTool()
```

### Transport Options

**stdio** (default):
```bash
python run_mcp_server.py --transport stdio
```

**SSE** (Server-Sent Events):
```bash
python run_mcp_server.py --transport sse
```

---

## 🐛 Troubleshooting

### Tools Not Showing Up

1. Check logs for registration errors
2. Verify environment variables are set
3. Restart the MCP client (Claude Desktop, etc.)

### API Key Errors

```
CRM API key not configured. Set KEYCRM_API_KEY environment variable.
```

**Solution**: Add the API key to your MCP client configuration

### Import Errors

```
ModuleNotFoundError: No module named 'youtube_transcript_api'
```

**Solution**: Install missing dependencies
```bash
pip install youtube-transcript-api pytube langchain openai faiss-cpu notion-client aiohttp
```

### Knowledge Base Errors

```
OPENAI_API_KEY not set
```

**Solution**: The knowledge base tool requires OpenAI for embeddings. Add your API key.

---

## 📊 Monitoring

### View Tool Usage

Check the logs for tool execution:

```bash
tail -f /path/to/logs/mcp_server.log
```

### Debug Mode

```bash
export LOG_LEVEL=DEBUG
python run_mcp_server.py
```

---

## 🔐 Security Best Practices

1. **Never commit API keys** to version control
2. **Use environment variables** for all sensitive data
3. **Restrict file system access** in production
4. **Monitor tool usage** for unexpected behavior
5. **Keep dependencies updated** for security patches

---

## 📚 Additional Resources

- [MCP Specification](https://modelcontextprotocol.io/)
- [Claude Desktop MCP Guide](https://docs.anthropic.com/claude/docs/mcp)
- [FreEco.ai Documentation](https://github.com/FreEco-ai/FreEco-Platform)

---

## 🎉 What's Next?

With FreEco.ai as an MCP server, you can:

✅ Use YouTube transcripts in your AI conversations
✅ Build a personal knowledge base with RAG
✅ Automate Notion workflows
✅ Manage CRM from any MCP client
✅ Chain complex workflows across tools

**Welcome to the FreEco.ai ecosystem!** 🌱🤖

---

**Version**: 1.0.0
**Last Updated**: October 26, 2025
**Maintained by**: FreEco.ai Team
