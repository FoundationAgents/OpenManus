import json
import os
import random
import sys
import time
import unittest
from agentbay.browser import Browser, BrowserOption, BrowserFingerprint, BrowserProxy
from agentbay.browser.browser_agent import ActOptions, ExtractOptions, ObserveOptions, ActResult, ObserveResult
from playwright.sync_api import sync_playwright
from pydantic import BaseModel
from agentbay.model.response import SessionResult

# Add the parent directory to the path so we can import the agentbay package
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agentbay import AgentBay
from agentbay.exceptions import AgentBayError
from agentbay.session_params import CreateSessionParams


class DummySchema(BaseModel):
    title: str


def get_test_api_key():
    """Get API key for testing"""
    api_key = os.environ.get("AGENTBAY_API_KEY")
    if not api_key:
        api_key = "akm-xxx"  # Replace with your test API key
        print(
            "Warning: Using default API key. Set AGENTBAY_API_KEY environment variable for testing."
        )
    return api_key


def _mask_secret(secret: str, visible: int = 4) -> str:
    """Mask a secret value, keeping only the last `visible` characters."""
    if not secret:
        return ""
    if len(secret) <= visible:
        return "*" * len(secret)
    return ("*" * (len(secret) - visible)) + secret[-visible:]


def is_windows_user_agent(user_agent: str) -> bool:
    if not user_agent:
        return False
    user_agent_lower = user_agent.lower()
    windows_indicators = [
        'windows nt',
        'win32',
        'win64',
        'windows',
        'wow64'
    ]
    return any(indicator in user_agent_lower for indicator in windows_indicators)


class TestBrowserAgentIntegration(unittest.TestCase):
    def setUp(self):
        """Set up test fixtures."""
        api_key = get_test_api_key()
        print("api_key =", _mask_secret(api_key))
        self.agent_bay = AgentBay(api_key=api_key)
        print("Creating a new session for browser agent testing...")
        self.create_session()
    
    def create_session(self):
        # Create a session
        session_param = CreateSessionParams()
        session_param.image_id = "browser_latest"
        result = self.agent_bay.create(session_param)
        self.assertTrue(result.success)
        self.session = result.session
        print(f"Session created with ID: {self.session.session_id}")

    def tearDown(self):
        """Tear down test fixtures."""
        print("Cleaning up: Deleting the session...")
        try:
            self.agent_bay.delete(self.session)
        except Exception as e:
            print(f"Warning: Error deleting session: {e}")

    def test_initialize_browser(self):
        browser = self.session.browser
        self.assertIsNotNone(browser)
        self.assertIsInstance(browser, Browser)

        self.assertTrue(browser.initialize(BrowserOption()))

        endpoint_url = browser.get_endpoint_url()
        print("endpoint_url =", endpoint_url)
        self.assertTrue(endpoint_url is not None)

        time.sleep(10)

        from playwright.sync_api import sync_playwright
        p = sync_playwright().start()
        playwright_browser = p.chromium.connect_over_cdp(endpoint_url)
        self.assertTrue(playwright_browser is not None)

        page = playwright_browser.new_page()
        page.goto("http://www.baidu.com")
        print("page.title() =", page.title())

        self.assertTrue(page.title() is not None)
        page.close()

    def test_initialize_browser_with_fingerprint(self):
        browser = self.session.browser
        self.assertIsNotNone(browser)
        self.assertIsInstance(browser, Browser)
        option = BrowserOption(
            use_stealth=True,
            fingerprint=BrowserFingerprint(
                devices=["desktop"],
                operating_systems=["windows"],
                locales=["zh-CN"],
            )
        )
        self.assertTrue(browser.initialize(option))

        endpoint_url = browser.get_endpoint_url()
        print("endpoint_url =", endpoint_url)
        self.assertTrue(endpoint_url is not None)

        time.sleep(10)

        from playwright.sync_api import sync_playwright
        p = sync_playwright().start()
        playwright_browser = p.chromium.connect_over_cdp(endpoint_url)
        self.assertTrue(playwright_browser is not None)
        default_context = playwright_browser.contexts[0]
        self.assertTrue(default_context is not None)

        page = default_context.new_page()
        page.goto("https://httpbin.org/user-agent", timeout=60000)
        response = page.evaluate("() => JSON.parse(document.body.textContent)")
        user_agent = response["user-agent"]
        print("user_agent =", user_agent)
        self.assertTrue(user_agent is not None)
        is_windows = is_windows_user_agent(user_agent)
        self.assertTrue(is_windows)

        page.close()

    def test_initialize_browser_with_captchas(self):
        print("solve captchas begin")
        browser = self.session.browser
        self.assertIsNotNone(browser)
        self.assertIsInstance(browser, Browser)

        option = BrowserOption(
            use_stealth=True,
            solve_captchas=True,
            fingerprint=BrowserFingerprint(
                devices=["desktop"],
                operating_systems=["windows"],
                locales=["zh-CN"],
            )
        )
        self.assertTrue(browser.initialize(option))

        endpoint_url = browser.get_endpoint_url()
        print("endpoint_url =", endpoint_url)
        self.assertTrue(endpoint_url is not None)

        time.sleep(10)

        p = sync_playwright().start()
        playwright_browser = p.chromium.connect_over_cdp(endpoint_url)
        self.assertTrue(playwright_browser is not None)
        default_context = playwright_browser.contexts[0]
        self.assertTrue(default_context is not None)

        page = default_context.new_page()
        # Tongcheng password recovery page with captcha
        captcha_url = "https://passport.ly.com/Passport/GetPassword"
        page.goto(captcha_url, timeout=10000, wait_until="domcontentloaded")

        # Wait for phone input and interact
        input_selector = "#name_in"
        page.wait_for_selector(input_selector, timeout=10000)
        page.fill(input_selector, "15011556760")
        page.click("#next_step1")

        # Wait for potential captcha handling and navigation
        time.sleep(30)
        # href changed indicates captcha solved
        current_url_location = page.evaluate("() => window.location && window.location.href")
        print("current_url(window.location.href) =", current_url_location)
        self.assertNotEqual(current_url_location, captcha_url)

        page.close()
        print("solve captchas end")

    def test_act_success(self):
        browser = self.session.browser
        self.assertIsNotNone(browser)
        self.assertIsInstance(browser, Browser)

        self.assertTrue(browser.initialize(BrowserOption()))

        endpoint_url = browser.get_endpoint_url()
        print("endpoint_url =", endpoint_url)
        self.assertTrue(endpoint_url is not None)

        from playwright.sync_api import sync_playwright
        p = sync_playwright().start()
        playwright_browser = p.chromium.connect_over_cdp(endpoint_url)
        self.assertTrue(playwright_browser is not None)

        page = playwright_browser.new_page()
        page.goto("http://www.baidu.com")
        self.assertTrue(page.title() is not None)

        result = browser.agent.act(ActOptions(action="Click search button"), page)
        print("result =", result)

        self.assertTrue(result.success)
        self.assertIsInstance(result, ActResult)

        page.close()

    def test_observe_success(self):
        browser = self.session.browser
        self.assertIsNotNone(browser)
        self.assertIsInstance(browser, Browser)

        self.assertTrue(browser.initialize(BrowserOption()))

        endpoint_url = browser.get_endpoint_url()
        print("endpoint_url =", endpoint_url)
        self.assertTrue(endpoint_url is not None)

        from playwright.sync_api import sync_playwright
        p = sync_playwright().start()
        playwright_browser = p.chromium.connect_over_cdp(endpoint_url)
        self.assertTrue(playwright_browser is not None)

        page = playwright_browser.new_page()
        page.goto("http://www.baidu.com")
        self.assertTrue(page.title() is not None)

        result, observe_results = browser.agent.observe(ObserveOptions(instruction="Find the search button"), page)
        print("result =", result)
        print("observe_results =", observe_results)

        self.assertTrue(result)
        self.assertIsInstance(observe_results[0], ObserveResult)

        page.close()

    def test_extract_success(self):
        browser = self.session.browser
        self.assertIsNotNone(browser)
        self.assertIsInstance(browser, Browser)

        self.assertTrue(browser.initialize(BrowserOption()))

        endpoint_url = browser.get_endpoint_url()
        print("endpoint_url =", endpoint_url)
        self.assertTrue(endpoint_url is not None)

        from playwright.sync_api import sync_playwright
        p = sync_playwright().start()
        playwrigt_browser = p.chromium.connect_over_cdp(endpoint_url)
        self.assertTrue(playwrigt_browser is not None)

        page = playwrigt_browser.new_page()
        page.goto("http://www.baidu.com")
        self.assertTrue(page.title() is not None)

        result, obj = browser.agent.extract(ExtractOptions(instruction="Extract the title", schema=DummySchema), page)
        print("result =", result)
        print("obj =", obj)
        self.assertTrue(result)
        self.assertIsInstance(obj, DummySchema)

        page.close()

    def test_restricted_proxy_ip_comparison(self):
        """Test restricted proxy by comparing IP addresses before and after proxy setup."""
        browser = self.session.browser
        self.assertIsNotNone(browser)
        self.assertIsInstance(browser, Browser)
        
        print("=== test restricted proxy IP comparison ===")
        
        # Phase 1: Initialize browser without proxy and get original IP
        print("phase 1: initialize browser without proxy...")
        no_proxy_option = BrowserOption()
        self.assertTrue(browser.initialize(no_proxy_option))
        
        endpoint_url = browser.get_endpoint_url()
        print(f"endpoint_url = {endpoint_url}")
        self.assertTrue(endpoint_url is not None)
        
        time.sleep(5)
        
        # Get original IP
        from playwright.sync_api import sync_playwright
        p = sync_playwright().start()
        playwright_browser = p.chromium.connect_over_cdp(endpoint_url)
        self.assertTrue(playwright_browser is not None)
        
        context = playwright_browser.contexts[0]
        page = context.new_page()
        page.goto("https://httpbin.org/ip")
        
        try:
            response = await page.evaluate("() => JSON.parse(document.body.textContent)")
            original_ip = response.get("origin", "").strip()
            print(f"original IP: {original_ip}")
        except Exception as e:
            print(f"get original IP failed: {e}")
            original_ip = None
        
        page.close()
        playwright_browser.close()
        p.stop()

        # Delete current session
        self.agent_bay.delete(self.session)
        
        time.sleep(3)
        
        # Phase 2: Create new session with restricted proxy
        print("phase 2: create new session with restricted proxy...")
        restricted_proxy = BrowserProxy(
            proxy_type="wuying",
            strategy="restricted"
        )
        
        proxy_option = BrowserOption(proxies=[restricted_proxy])
        self.create_session()
        browser = self.session.browser
        self.assertTrue(browser.initialize(proxy_option))
        
        # Verify proxy configuration
        saved_option = browser.get_option()
        self.assertIsNotNone(saved_option.proxies)
        self.assertEqual(len(saved_option.proxies), 1)
        self.assertEqual(saved_option.proxies[0].type, "wuying")
        self.assertEqual(saved_option.proxies[0].strategy, "restricted")
        print("✓ proxy config validation success")
        
        endpoint_url = browser.get_endpoint_url()
        print(f"proxy mode endpoint_url = {endpoint_url}")
        
        time.sleep(5)
        
        # Get proxy IP
        p2 = sync_playwright().start()
        playwright_browser2 = p2.chromium.connect_over_cdp(endpoint_url)
        self.assertTrue(playwright_browser2 is not None)
        
        context2 = playwright_browser2.contexts[0]
        page2 = context2.new_page()
        page2.goto("https://httpbin.org/ip")
        
        try:
            response2 = await page2.evaluate("() => JSON.parse(document.body.textContent)")
            proxy_ip = response2.get("origin", "").strip()
            print(f"proxy IP: {proxy_ip}")
        except Exception as e:
            print(f"get proxy IP failed: {e}")
            proxy_ip = None
        
        page2.close()
        playwright_browser2.close()
        p2.stop()
        
        # Compare IPs
        if original_ip and proxy_ip:
            if original_ip != proxy_ip:
                print(f"✅ static proxy test success! IP changed: {original_ip} -> {proxy_ip}")
            else:
                print(f"⚠️  warning: proxy IP is the same, maybe proxy not working: {original_ip}")
                self.fail("proxy IP is the same, maybe proxy not working")
        else:
            print("⚠️  failed to compare IP, but proxy config applied")

    def test_polling_proxy_multiple_ips(self):
        """Test polling proxy with multiple pages to observe different IPs."""
        browser = self.session.browser
        self.assertIsNotNone(browser)
        self.assertIsInstance(browser, Browser)
        
        print("=== test polling proxy with multiple IPs ===")
        
        # Initialize browser with polling proxy
        polling_proxy = BrowserProxy(
            proxy_type = "wuying",
            strategy = "polling",
            pollsize = 10
        )
        
        option = BrowserOption(proxies=[polling_proxy])
        self.assertTrue(browser.initialize(option))
        
        # Verify proxy configuration
        saved_option = browser.get_option()
        self.assertIsNotNone(saved_option.proxies)
        self.assertEqual(len(saved_option.proxies), 1)
        self.assertEqual(saved_option.proxies[0].type, "wuying")
        self.assertEqual(saved_option.proxies[0].strategy, "polling")
        self.assertEqual(saved_option.proxies[0].pollsize, 10)
        print("✓ polling proxy config validation success (pollsize=10)")
        
        endpoint_url = browser.get_endpoint_url()
        print(f"endpoint_url = {endpoint_url}")
        
        time.sleep(5)
        
        # Create multiple pages and collect IPs
        from playwright.sync_api import sync_playwright
        p = sync_playwright().start()
        playwright_browser = p.chromium.connect_over_cdp(endpoint_url)
        self.assertTrue(playwright_browser is not None)
        
        context = playwright_browser.contexts[0]
        ips_collected = []
        
        print("create multiple pages and collect IPs...")
        
        try:
            context.clear_cookies()
            context.clear_permissions()
        except Exception as e:
            print(f"clear context failed: {e}")
        
        for i in range(5):
            page = context.new_page()
            try:
                try:
                    context.clear_cookies()
                    context.clear_permissions()
                except Exception:
                    pass
                
                #  to avoid cache
                import random
                cache_buster = random.randint(1000000, 9999999)
                timestamp = int(time.time() * 1000)
                random_str = ''.join(random.choices('abcdefghijklmnopqrstuvwxyz', k=8))
                url = f"https://ifconfig.me?_cb={cache_buster}&_t={timestamp}&_r={i}&_rand={random_str}"
                # set headers to avoid cache
                page.set_extra_http_headers({
                    "Cache-Control": "no-cache, no-store, must-revalidate, max-age=0",
                    "Pragma": "no-cache",
                    "Expires": "0",
                    "User-Agent": f"ProxyTest-{i}-{random.randint(1000, 9999)}",
                    "X-Request-ID": f"req-{timestamp}-{i}"
                })
                
                print(f"page {i+1} requesting with cache-busting: ifconfig.me?_cb={cache_buster}&_t={timestamp}...")
                
                # use reload to force reload
                page.goto(url, timeout=30000, wait_until="networkidle")
                
                # wait for page to load
                time.sleep(1)
                
                # extract IP from ifconfig.me
                ip = page.evaluate("""
                    () => {
                        // method 1: get IP by ID
                        const ipElement = document.getElementById('ip_address');
                        if (ipElement) {
                            return ipElement.textContent.trim();
                        }
                        
                        return null;
                    }
                """)
                
                if not ip:
                    # if javascript parsing failed, try to get page content and extract IP with regex
                    page_content = page.content()
                    import re
                    ip_match = re.search(r'<strong id="ip_address">\s*([0-9.]+)\s*</strong>', page_content)
                    if ip_match:
                        ip = ip_match.group(1).strip()
                    else:
                        print(f"Failed to extract IP from page content for page {i+1}")
                        ip = None
                ips_collected.append(ip)
                print(f"page {i+1} IP: {ip}")
                time.sleep(2)  # wait for proxy to change
            except Exception as e:
                print(f"page {i+1} get IP failed: {e}")
                ips_collected.append(None)
            finally:
                page.close()
        
        playwright_browser.close()
        p.stop()
        
        # Analyze results
        valid_ips = [ip for ip in ips_collected if ip]
        unique_ips = list(set(valid_ips))
        
        print(f"\nresult analysis:")
        print(f"  collected valid IP count: {len(valid_ips)}")
        print(f"  unique IP count: {len(unique_ips)}")
        print(f"  unique IP list: {unique_ips}")
        
        if len(unique_ips) > 1:
            print(f"✅ polling proxy test success! detected {len(unique_ips)} different IPs")
        else:
            print("❌ failed to get valid IP")
        
        # At least verify we got some valid responses
        self.assertGreater(len(unique_ips), 1, "at least two valid ip")

if __name__ == "__main__":
    unittest.main() 