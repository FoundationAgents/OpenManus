# Manus Agent with A2A Protocol

这是一个将A2A协议(https://google.github.io/A2A/#/documentation)与OpenManus结合的一个尝试,当前仅支持非流式

## Prerequisites
- conda activate 'Your OpenManus python env'
- cd OpenManus/A2A
- pip install -r requirements.txt

## Setup & Running

1. 运行A2A Server:

   ```bash
   cd OpenManus
   python -m A2A.Manus.main
   ```

2. 拉取A2A官方库并运行A2A Client 详情参考（https://github.com/google/A2A）:

   ```bash
   git clone https://github.com/google/A2A.git
   cd A2A
   echo "GOOGLE_API_KEY=your_api_key_here" > .env
   cd samples/python/hosts/cli
   uv run .
   ```

3. 通过A2A Client的命令行向OpenManus 发送任务


## Examples

**获得Agent Card**

Request:

```
curl http://localhost:10000/.well-known/agent.json

```


```
Response:

{
    "name": "Manus Agent",
    "description": "A versatile agent that can solve various tasks using multiple tools including MCP-based tools",
    "url": "http://localhost:10000/",
    "version": "1.0.0",
    "capabilities": {
        "streaming": false,
        "pushNotifications": true,
        "stateTransitionHistory": false
    },
    "defaultInputModes": [
        "text",
        "text/plain"
    ],
    "defaultOutputModes": [
        "text",
        "text/plain"
    ],
    "skills": [
        {
            "id": "Python Execute",
            "name": "Python Execute Tool",
            "description": "Executes Python code string. Note: Only print outputs are visible, function return values are not captured. Use print statements to see results.",
            "tags": [
                "Execute Python Code"
            ],
            "examples": [
                "Execute Python code:'''python \n Print('Hello World') \n '''"
            ]
        },
        {
            "id": "Browser use",
            "name": "Browser use Tool",
            "description": "A powerful browser automation tool that allows interaction with web pages through various actions.\n* This tool provides commands for controlling a browser session, navigating web pages, and extracting information\n* It maintains state across calls, keeping the browser session alive until explicitly closed\n* Use this when you need to browse websites, fill forms, click buttons, extract content, or perform web searches\n* Each action requires specific parameters as defined in the tool's dependencies\n\nKey capabilities include:\n* Navigation: Go to specific URLs, go back, search the web, or refresh pages\n* Interaction: Click elements, input text, select from dropdowns, send keyboard commands\n* Scrolling: Scroll up/down by pixel amount or scroll to specific text\n* Content extraction: Extract and analyze content from web pages based on specific goals\n* Tab management: Switch between tabs, open new tabs, or close tabs\n\nNote: When using element indices, refer to the numbered elements shown in the current browser state.\n",
            "tags": [
                "Use Browser"
            ],
            "examples": [
                "go_to 'https://www.google.com'"
            ]
        },
        {
            "id": "Replace String",
            "name": "Str_replace Tool",
            "description": "Custom editing tool for viewing, creating and editing files\n* State is persistent across command calls and discussions with the user\n* If `path` is a file, `view` displays the result of applying `cat -n`. If `path` is a directory, `view` lists non-hidden files and directories up to 2 levels deep\n* The `create` command cannot be used if the specified `path` already exists as a file\n* If a `command` generates a long output, it will be truncated and marked with `<response clipped>`\n* The `undo_edit` command will revert the last edit made to the file at `path`\n\nNotes for using the `str_replace` command:\n* The `old_str` parameter should match EXACTLY one or more consecutive lines from the original file. Be mindful of whitespaces!\n* If the `old_str` parameter is not unique in the file, the replacement will not be performed. Make sure to include enough context in `old_str` to make it unique\n* The `new_str` parameter should contain the edited lines that should replace the `old_str`\n",
            "tags": [
                "Operate Files"
            ],
            "examples": [
                "Replace 'old' with 'new' in 'file.txt'"
            ]
        },
        {
            "id": "Ask human",
            "name": "Ask human Tool",
            "description": "Use this tool to ask human for help.",
            "tags": [
                "Ask human for help"
            ],
            "examples": [
                "Ask human: 'What time is it?'"
            ]
        },
        {
            "id": "terminate",
            "name": "terminate Tool",
            "description": "Terminate the interaction when the request is met OR if the assistant cannot proceed further with the task.\nWhen you have finished all the tasks, call this tool to end the work.",
            "tags": [
                "terminate task"
            ],
            "examples": [
                "terminate"
            ]
        }
    ]
}
```

**发送任务**

Request:

```
curl --location 'http://localhost:10000' \
--header 'Content-Type:  application/json' \
--data '{
  "jsonrpc": "2.0",
  "id": 10,
  "method": "tasks/send",
  "params": {
    "id": "130",
    "sessionId": "94dbdab49b2e44a9aac361cfaffbafd1",
    "acceptedOutputModes": [
      "text"
    ],
    "message": {
      "role": "user",
      "parts": [
        {
          "type": "text",
          "text": "什么是快乐星球"
        }
      ]
    }
  }
}'
```

Response:

```
{
    "jsonrpc": "2.0",
    "id": 10,
    "result": {
        "id": "130",
        "sessionId": "94dbdab49b2e44a9aac361cfaffbafd1",
        "status": {
            "state": "completed",
            "timestamp": "2025-04-24T22:34:06.219036"
        },
        "artifacts": [
            {
                "parts": [
                    {
                        "type": "text",
                        "text": "Step 1: “快乐星球”是一个源自中国儿童电视剧《快乐星球》的概念。这部剧讲述了一群来自外星球的孩子在地球上的冒险故事，他们通过科技和智慧帮助地球上的孩子们解决问题，传递了友情、勇气和快乐的主题。\n\n“快乐星球”后来也成为了网络流行语，通常用来调侃或表达对某种理想化、无忧无虑状态的向往。比如，有人可能会问：“什么是快乐星球？”然后回答：“快乐星球就是没有烦恼的地方！”\n\n如果您是想了解这部剧的具体内容，或者想找相关的资源，我可以帮您进一步搜索或提供更多信息！\nTerminated: Reached max steps (1)"
                    }
                ],
                "index": 0
            }
        ],
        "history": []
    }
}
```


## Learn More

- [A2A Protocol Documentation](https://google.github.io/A2A/#/documentation)

