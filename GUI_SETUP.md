# FreEco.AI GUI - Setup and Usage Guide

## 🌿 Overview

FreEco.AI now includes a complete web-based GUI matching the Manus.im design. The interface provides:

- **Chat Interface** - Talk to the FreEco.AI agent powered by Minimax M2
- **Tasks Management** - Create, track, and manage tasks
- **Knowledge Base** - Store, search, and organize documents
- **Settings** - Configure Minimax M2 Pro API and model parameters

## 📋 Requirements

- Python 3.8+
- FastAPI & Uvicorn
- Minimax M2 Pro API key

## 🚀 Quick Start

### 1. Install Dependencies

```bash
cd /home/ubuntu/freeco-openmanus
pip3 install fastapi uvicorn pydantic aiohttp
```

### 2. Configure Minimax API Key

The Minimax API key is stored in `.freeco/settings.json`. You can update it through the GUI Settings tab or manually:

```json
{
  "minimax": {
    "api_key": "your_minimax_api_key_here",
    "model": "minimax-01",
    "temperature": 0.7,
    "max_tokens": 4096
  }
}
```

### 3. Start the Server

```bash
./run_gui.sh
```

Or manually:

```bash
python3 -m uvicorn app.gui_server:app --host 0.0.0.0 --port 8000 --reload
```

### 4. Access the GUI

Open your browser and navigate to:
- **GUI:** http://localhost:8000
- **API Docs:** http://localhost:8000/docs

## 🎨 Features

### Chat Tab
- Real-time chat with FreEco.AI agent
- Powered by Minimax M2 Pro with function calling
- Supports tasks, knowledge base, and statistics queries

### Tasks Tab
- Create new tasks with title, description, and priority
- Track task status (pending, in_progress, completed, cancelled)
- View task statistics
- Update and delete tasks

### Knowledge Base Tab
- Add documents with title, content, and category
- Full-text search across all documents
- Filter by category
- View document statistics
- Delete documents

### Settings Tab
- Configure Minimax M2 Pro API key
- Select model (minimax-01 or minimax-01-vision)
- Adjust temperature (0.0 - 1.0)
- Set max tokens (1 - 200,000)
- Test connection to Minimax API

## 🌙 Theme

The GUI supports both light and dark themes:
- Click the theme toggle button (☀️/🌙) in the header
- Theme preference is saved in browser localStorage

## 📡 API Endpoints

### Health Check
```
GET /api/health
```

### Tasks
```
GET    /api/tasks                    # List all tasks
POST   /api/tasks                    # Create new task
PUT    /api/tasks/{task_id}          # Update task status
DELETE /api/tasks/{task_id}          # Delete task
GET    /api/tasks/stats              # Get task statistics
```

### Knowledge Base
```
GET    /api/documents                # List all documents
POST   /api/documents                # Add new document
DELETE /api/documents/{doc_id}       # Delete document
GET    /api/documents/search?q=...   # Search documents
GET    /api/documents/stats          # Get KB statistics
```

### Settings
```
GET    /api/settings                 # Get current settings
PUT    /api/settings                 # Update settings
POST   /api/settings/test-minimax    # Test Minimax connection
```

### Chat
```
POST   /api/chat                     # Send message to agent
WS     /ws/chat                      # WebSocket chat (streaming)
```

## 📁 File Structure

```
app/
├── gui/
│   ├── index.html          # GUI HTML interface
│   ├── style.css           # GUI styling (black & white theme)
│   └── app.js              # GUI JavaScript logic
├── gui_server.py           # FastAPI backend server
├── features/
│   ├── tasks.py            # Task management
│   ├── knowledge_base.py   # Knowledge base
│   ├── settings.py         # Settings management
│   ├── minimax_client.py   # Minimax M2 API client
│   ├── function_calling.py # Function calling framework
│   └── agent.py            # FreEco agent with tools
└── ...

.freeco/
├── tasks.json              # Tasks storage
├── settings.json           # Settings storage
└── knowledge_base.json     # Knowledge base storage
```

## 🔧 Troubleshooting

### Port Already in Use
```bash
# Use a different port
python3 -m uvicorn app.gui_server:app --host 0.0.0.0 --port 8001
```

### Minimax Connection Failed
1. Verify API key in Settings tab
2. Check internet connection
3. Test connection using the "Test Connection" button

### Tasks/Documents Not Persisting
- Check `.freeco/` directory exists
- Verify file permissions
- Check disk space

## 📚 Integration with FreEco.AI Backend

The GUI is fully integrated with:
- **Task Manager** - Full CRUD operations
- **Knowledge Base** - Search and document management
- **Minimax M2 Pro** - Function calling and interleaved thinking
- **FreEco Agent** - Agentic reasoning with tool use

## 🚀 Deployment

For production deployment:

1. **Use Gunicorn:**
   ```bash
   pip3 install gunicorn
   gunicorn -w 4 -b 0.0.0.0:8000 app.gui_server:app
   ```

2. **Use Docker:**
   ```dockerfile
   FROM python:3.11
   WORKDIR /app
   COPY requirements.txt .
   RUN pip install -r requirements.txt
   COPY . .
   CMD ["python3", "-m", "uvicorn", "app.gui_server:app", "--host", "0.0.0.0", "--port", "8000"]
   ```

3. **Use Nginx as reverse proxy:**
   ```nginx
   server {
       listen 80;
       server_name your-domain.com;

       location / {
           proxy_pass http://localhost:8000;
           proxy_set_header Host $host;
           proxy_set_header X-Real-IP $remote_addr;
       }
   }
   ```

## 📝 Notes

- All data is stored locally in `.freeco/` directory
- API key is stored in plaintext - use environment variables in production
- GUI supports modern browsers (Chrome, Firefox, Safari, Edge)
- Mobile responsive design included

## 🤝 Support

For issues or questions, please refer to the main FreEco.AI documentation or GitHub repository.

---

**FreEco.AI GUI v1.0.0** - Powered by Minimax M2 Pro
