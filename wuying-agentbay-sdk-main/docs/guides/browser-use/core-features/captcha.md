# CAPTCHA Resolution

CAPTCHA challenges are common obstacles in web automation that can disrupt your workflow. AIBrowser includes an intelligent CAPTCHA resolution system that automatically handles these verification challenges, ensuring your automation tasks proceed smoothly.

> **Version Information:** CAPTCHA resolution is available starting from version 0.7.0. Currently, the system only supports automatic resolution of slider-type CAPTCHAs. Support for text-based CAPTCHAs will be added in future releases.

## Automatic CAPTCHA Resolution

The system works by:
- Detecting CAPTCHA challenges as they appear on web pages
- Processing the challenge using advanced recognition algorithms
- Completing the verification process transparently
- Resolution typically completes within 30 seconds for most CAPTCHA types
- Feature is opt-in and disabled by default for performance optimization

## Event Monitoring

Track CAPTCHA resolution progress through console events. This allows you to implement custom logic while the system handles the verification:

```python
def handle_console(msg):
    if msg.text == "wuying-captcha-solving-started":
        print("CAPTCHA solving started")
    elif msg.text == "wuying-captcha-solving-finished":
        print("CAPTCHA solving finished")

page.on("console", handle_console)
```

## Configuration

Enable CAPTCHA resolution by setting the appropriate flag during browser initialization:

```python
params = CreateSessionParams(
    image_id="browser_latest",  # Specify the image ID
)
session_result = agent_bay.create(params)

session = session_result.session
browser_option = BrowserOption(
    solve_captchas=True,
)
await session.browser.initialize_async(browser_option)
```

## Usage Tips

- Plan for up to 30 seconds processing time per CAPTCHA
- Implement event listeners to track resolution status
- Disable the feature if manual CAPTCHA handling is preferred for your use case

## 📚 Related Guides

- [Stealth Mode](stealth-mode.md) - Anti-detection techniques for web automation
- [Call For User](call-for-user.md) - Human intervention for unsolvable challenges
- [Browser Use Overview](../README.md) - Complete browser automation features
- [Session Management](../../common-features/basics/session-management.md) - Session lifecycle and configuration

## 🆘 Getting Help

- [GitHub Issues](https://github.com/aliyun/wuying-agentbay-sdk/issues)
- [Documentation Home](../../README.md)
