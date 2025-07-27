# Manus Agent with A2A Protocol

这是一个将A2A协议(https://google.github.io/A2A/#/documentation)与OpenManus结合的一个尝试,当前仅支持非流式

## Prerequisites
- conda activate 'Your OpenManus python env'
- pip install a2a-sdk==0.2.5



## Setup & Running

1. 运行A2A Server:

   ```bash
   cd OpenManus
   python -m protocol.a2a.app.main
   ```

2. 拉取A2A官方库并运行A2A Client，有两种使用A2A客户端的方式——CLI以及在前端页面注册Agent服务。（详情参考https://github.com/google/A2A）:

   ```bash
   git clone https://github.com/google-a2a/a2a-samples.git
   cd a2a-samples
   echo "GOOGLE_API_KEY=your_api_key_here" > .env
   cd samples/python/hosts/cli
   uv run .
   ```

3. 通过A2A Client的命令行向OpenManus发送任务或者在A2A前端页面上将其注册


## Examples

**获得Agent Card**

Request:

```
curl http://localhost:10000/.well-known/agent.json

```


```
Response:

{
    "capabilities": {
        "pushNotifications": true,
        "streaming": false
    },
    "defaultInputModes": [
        "text",
        "text/plain"
    ],
    "defaultOutputModes": [
        "text",
        "text/plain"
    ],
    "description": "A versatile agent that can solve various tasks using multiple tools including MCP-based tools",
    "name": "Manus Agent",
    "skills": [
        {
            "description": "Executes Python code string. Note: Only print outputs are visible, function return values are not captured. Use print statements to see results.",
            "examples": [
                "Execute Python code:'''python \n Print('Hello World') \n '''"
            ],
            "id": "Python Execute",
            "name": "Python Execute Tool",
            "tags": [
                "Execute Python Code"
            ]
        },
        {
            "description": "A powerful browser automation tool that allows interaction with web pages through various actions.\n* This tool provides commands for controlling a browser session, navigating web pages, and extracting information\n* It maintains state across calls, keeping the browser session alive until explicitly closed\n* Use this when you need to browse websites, fill forms, click buttons, extract content, or perform web searches\n* Each action requires specific parameters as defined in the tool's dependencies\n\nKey capabilities include:\n* Navigation: Go to specific URLs, go back, search the web, or refresh pages\n* Interaction: Click elements, input text, select from dropdowns, send keyboard commands\n* Scrolling: Scroll up/down by pixel amount or scroll to specific text\n* Content extraction: Extract and analyze content from web pages based on specific goals\n* Tab management: Switch between tabs, open new tabs, or close tabs\n\nNote: When using element indices, refer to the numbered elements shown in the current browser state.\n",
            "examples": [
                "go_to 'https://www.google.com'"
            ],
            "id": "Browser use",
            "name": "Browser use Tool",
            "tags": [
                "Use Browser"
            ]
        },
        {
            "description": "Custom editing tool for viewing, creating and editing files\n* State is persistent across command calls and discussions with the user\n* If `path` is a file, `view` displays the result of applying `cat -n`. If `path` is a directory, `view` lists non-hidden files and directories up to 2 levels deep\n* The `create` command cannot be used if the specified `path` already exists as a file\n* If a `command` generates a long output, it will be truncated and marked with `<response clipped>`\n* The `undo_edit` command will revert the last edit made to the file at `path`\n\nNotes for using the `str_replace` command:\n* The `old_str` parameter should match EXACTLY one or more consecutive lines from the original file. Be mindful of whitespaces!\n* If the `old_str` parameter is not unique in the file, the replacement will not be performed. Make sure to include enough context in `old_str` to make it unique\n* The `new_str` parameter should contain the edited lines that should replace the `old_str`\n",
            "examples": [
                "Replace 'old' with 'new' in 'file.txt'"
            ],
            "id": "Replace String",
            "name": "Str_replace Tool",
            "tags": [
                "Operate Files"
            ]
        },
        {
            "description": "Use this tool to ask human for help.",
            "examples": [
                "Ask human: 'What time is it?'"
            ],
            "id": "Ask human",
            "name": "Ask human Tool",
            "tags": [
                "Ask human for help"
            ]
        },
        {
            "description": "Terminate the interaction when the request is met OR if the assistant cannot proceed further with the task.\nWhen you have finished all the tasks, call this tool to end the work.",
            "examples": [
                "terminate"
            ],
            "id": "terminate",
            "name": "terminate Tool",
            "tags": [
                "terminate task"
            ]
        }
    ],
    "url": "http://localhost:10000/",
    "version": "1.0.0"
}
```

**发送任务**

Request:

```
curl --location 'http://localhost:10000' \
--header 'Content-Type: application/json' \
--data '{
    "id":130,
    "jsonrpc":"2.0",
    "method": "message/send",
    "params": {
        "message": {
            "messageId": "",
            "role": "user",
            "parts": [{"text":"什么是快乐星球"}]
        }
    }
}'
```

Response:

```
{
    "id": 130,
    "jsonrpc": "2.0",
    "result": {
        "artifacts": [
            {
                "artifactId": "2f9d0af8-c7da-4f88-9c8c-3033836322b8",
                "description": "",
                "name": "task_cf64d3c9-1e08-4948-a620-76900aa204cf",
                "parts": [
                    {
                        "kind": "text",
                        "text": "Step 1: “快乐星球”是一个流行的网络用语，源自中国儿童科幻电视剧《快乐星球》。这部剧讲述了一群孩子在一个虚构的“快乐星球”上经历的冒险故事，主题围绕着友谊、成长和科学幻想。后来，“快乐星球”逐渐成为一种网络梗，用来形容一种无忧无虑、充满快乐的理想状态。\n\n如果你对这个词的具体含义、出处或者相关的文化背景有更多兴趣，可以告诉我，我可以为你提供更详细的信息！\nStep 2: Observed output of cmd `terminate` executed:\nThe interaction has been completed with status: success"
                    }
                ]
            }
        ],
        "contextId": "44d16c16-9ccf-49c2-9a99-5c9513969b5f",
        "history": [
            {
                "contextId": "44d16c16-9ccf-49c2-9a99-5c9513969b5f",
                "kind": "message",
                "messageId": "",
                "parts": [
                    {
                        "kind": "text",
                        "text": "什么是快乐星球"
                    }
                ],
                "role": "user",
                "taskId": "cf64d3c9-1e08-4948-a620-76900aa204cf"
            }
        ],
        "id": "cf64d3c9-1e08-4948-a620-76900aa204cf",
        "kind": "task",
        "status": {
            "state": "completed"
        }
    }
}
```


## Learn More

- [A2A Protocol Documentation](https://google.github.io/A2A/#/documentation)

