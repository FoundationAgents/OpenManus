# Agent with Daytona sandbox




## Prerequisites
- conda activate 'Your OpenManus python env'
- pip install daytona==0.21.8 structlog==25.4.0



## Setup & Running

1. daytona config :
   ```bash
   cd OpenManus
   cp config/config.example-daytona.toml config/config.toml
   ```
2. get daytona apikey :
   goto https://app.daytona.io/dashboard/keys and create your apikey

3. set your apikey in config.toml
   ```toml
   # daytona config
   [daytona]
   daytona_api_key = ""
   #daytona_server_url = "https://app.daytona.io/api"
   #daytona_target = "us"                                   #Daytona is currently available in the following regions:United States (us)、Europe (eu)
   #sandbox_image_name = "whitezxj/sandbox:0.1.0"                #If you don't use this default image,sandbox tools may be useless
   #sandbox_entrypoint = "/usr/bin/supervisord -n -c /etc/supervisor/conf.d/supervisord.conf"   #If you change this entrypoint,server in sandbox may be useless
   #VNC_password =                                          #The password you set to log in sandbox by VNC,it will be 123456 if you don't set
   ```
2. Run :

   ```bash
   cd OpenManus
   python sandbox_main.py
   ```

3. Send tasks to Agent
   You can sent tasks to Agent by terminate,agent will use sandbox tools to handle your tasks.

4. See results
   If agent use sb_browser_use tool, you can see the operations by VNC link, The VNC link will print in the termination,e.g.:https://6080-sandbox-123456.h7890.daytona.work.
   If agent use sb_shell tool, you can see the results by terminate of sandbox in https://app.daytona.io/dashboard/sandboxes.
   Agent can use sb_files tool to operate files to sandbox.


## Example

 You can send task e.g.:"帮我在https://hk.trip.com/travel-guide/guidebook/nanjing-9696/?ishideheader=true&isHideNavBar=YES&disableFontScaling=1&catalogId=514634&locale=zh-HK查询相关信息上制定一份南京旅游攻略，并在工作区保存为index.html"

 Then you can see the agent's browser action in VNC link(https://6080-sandbox-123456.h7890.proxy.daytona.work) and you can see the html made by agent in Website URL(https://8080-sandbox-123456.h7890.proxy.daytona.work).

## Learn More

- [Daytona Documentation](https://www.daytona.io/docs/)


## AgentBay Sandbox

### Prerequisites
- Activate your Python environment: `conda activate <your-env>`
- Install dependencies: `pip install wuying-agentbay-sdk==0.9.3 structlog==25.4.0`

### Setup & Running

1. Create an AgentBay API key by following the official guide: https://help.aliyun.com/zh/agentbay/user-guide/service-management. The service provides a limited trial quota after the key is created—make sure you finish the console steps before running the agent.
2. Update `config/config.toml` with the AgentBay settings:
   ```toml
   [sandbox]
   provider = "agentbay"
   use_sandbox = true

   [sandbox.agentbay]
   api_key = "<your-agentbay-api-key>"
   endpoint = "wuyingai.cn-shanghai.aliyuncs.com"
   timeout_ms = 60000
   desktop_image_id = "linux_latest"
   browser_image_id = "browser_latest"
   mobile_image_id = "mobile_latest"
   ```
3. Start the sandbox agent:
   ```bash
   cd OpenManus
   python sandbox_main.py
   ```
4. You can send task like 'python3 sandbox_main.py --prompt "打开手机沙箱截图，并理解图片上的内容，然后在computer沙箱内新建一个文档，把理解后的图片文字内容写在文档里，并用nano打开这个文档"', OpenManus will choose the proper environment (Mobile, Computer, or Browser) to execute your task.
5. Check the logs for AgentBay session resource URLs. These links open the remote desktop or browser view so you can monitor the automation results.

### Learn More
- [AgentBay Service Management Guide](https://help.aliyun.com/zh/agentbay/user-guide/service-management)
- Project notes: `docs/agentbay_integration.md`
