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
