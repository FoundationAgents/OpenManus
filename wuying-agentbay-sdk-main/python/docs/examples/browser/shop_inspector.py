"""
示例：多站点商品巡检与抽取
批量访问站点，抽取商品名称/价格/相对链接，并归一化
保存 JSON 结果与截图
重点：ExtractOptions + Pydantic schema
"""
import os, asyncio, json
from datetime import datetime
from typing import List, Optional
from urllib.parse import urlparse, urljoin
import base64
from pydantic import BaseModel, Field

from agentbay import AgentBay
from agentbay.session_params import CreateSessionParams
from agentbay.browser.browser import (
    BrowserOption,
    BrowserScreen,
    BrowserProxy,
)
from agentbay.browser.browser_agent import ActOptions, ExtractOptions
from agentbay.model import SessionResult
from playwright.async_api import async_playwright

class ProductInfo(BaseModel):
    name: str = Field(..., description="商品名")
    price: Optional[str] = Field(None, description="价格文本；可为空")
    link: str = Field(..., description="商品页的相对路径 (如 /products/item1)")


class InspectionResult(BaseModel):
    products: List[ProductInfo] = Field(..., description="页面上的全部商品")


def domain_of(url: str) -> str:
    return urlparse(url).netloc


def normalize_abs_link(base_url: str, link: str) -> Optional[str]:
    link = (link or "").strip()
    if not link or link.startswith("#"):
        return None
    if link.startswith("/"):
        return urljoin(base_url, link)
    return link


def normalize_links(base_url: str, products: List[ProductInfo]) -> List[ProductInfo]:
    out: List[ProductInfo] = []
    for p in products:
        abs_link = normalize_abs_link(base_url, p.link)
        if not abs_link:
            continue
        out.append(
            ProductInfo(
                name=p.name.strip(), price=(p.price or "").strip(), link=abs_link
            )
        )
    return out


def is_valid_product(p: ProductInfo) -> bool:
    has_name = bool(p.name and p.name.strip())
    has_valid_link = bool(p.link and p.link.strip())
    has_price = bool(p.price and p.price.strip())

    return has_name and (has_valid_link or has_price)


def has_valid_products(products: List[ProductInfo], min_items: int = 2) -> bool:
    goods = [p for p in products if is_valid_product(p)]
    return len(goods) >= min_items


async def act(agent, page, instruction: str) -> bool:
    print(f"Acting: {instruction}")
    ret = await agent.act_async(action_input=ActOptions(action=instruction), page=page)
    return bool(getattr(ret, "success", False))


async def take_and_save_screenshot(agent, base_url: str, out_dir: str) -> Optional[str]:
    try:
        base64_data = await agent.screenshot_async()
        image_data = None
        if isinstance(base64_data, str):
            if base64_data.startswith("data:image/"):
                try:
                    header, encoded = base64_data.split(",", 1)
                    image_data = base64.b64decode(encoded)
                except (ValueError, TypeError, base64.binascii.Error) as e:
                    print(f"Failed to decode data URL screenshot from {base_url}: {e}")
            else:
                try:
                    image_data = base64.b64decode(base64_data)
                except (TypeError, base64.binascii.Error) as e:
                    print(
                        f"Failed to decode raw base64 screenshot from {base_url}: {e}"
                    )
        if image_data:
            host = urlparse(base_url).netloc
            os.makedirs(out_dir, exist_ok=True)
            screenshot_path = os.path.join(out_dir, f"screenshot_{host}.png")
            with open(screenshot_path, "wb") as f:
                f.write(image_data)
            print(f"Screenshot for {base_url} saved to: {screenshot_path}")
            return screenshot_path
        else:
            print(
                f"Received invalid or no screenshot data from {base_url}: {str(base64_data)[:100]}..."
            )
            return None

    except Exception as e:
        print(f"Failed to take screenshot for {base_url} due to an exception: {e}")
        return None


async def extract_products(
    agent, page, base_url: str
) -> List[ProductInfo]:
    opts = ExtractOptions(
        instruction=(
            "请提取本页所有商品。价格可为范围（例如 $199–$299）或“from $199”。"
            "对于商品链接(link)，请仅返回相对路径（例如 /path/to/product），不要包含域名。"
        ),
        schema=InspectionResult,
        use_text_extract=True,
    )
    ok, data = await agent.extract_async(options=opts, page=page)
    if not ok or not isinstance(data, InspectionResult) or not data.products:
        return []

    products = normalize_links(base_url, data.products)
    if not has_valid_products(products):
        print(
            f"Extracted products from {base_url} but none were valid after normalization."
        )
        return None
    
    
    return products


async def ensure_listing_page(
    agent, page, base_url: str, out_dir: str, max_steps: int = 3
) -> List[ProductInfo]:
    common_action = "前往商品列表页，例如 'Shop'、'Store'、'All products'、'Catalog' 或 'Collections' 等页面。如果当前不是商品列表页，请转到商品列表或目录页面（列表或网格视图）。如果页面存在弹窗、Cookie 横幅或遮罩，请先关闭。"
    await act(agent, page, common_action)
    await asyncio.sleep(0.6)
    for i in range(max_steps):
        print(f"Extraction attempt {i+1}/{max_steps} for {base_url}...")
        products_found = await extract_products(agent, page, base_url)
        if products_found is not None:
            valid_count = len([p for p in products_found if is_valid_product(p)])
            print(
                f"Extraction successful on attempt {i+1}. Found {valid_count} valid products."
            )

            await take_and_save_screenshot(agent, base_url, out_dir)
            return products_found

        if i < max_steps - 1:
            print("Extraction failed, attempting to navigate to a listing page...")
            await act(agent, page, common_action)
            await asyncio.sleep(0.6)

    print(f"All {max_steps} extraction attempts failed for {base_url}.")
    return []


async def process_site(session, browser, url: str, out_dir: str = "/tmp") -> None:
    host = domain_of(url)
    agent = session.browser.agent
    page = None
    if url in CAPTURE_DETECT_URL:
        print(f"CAPTCHA detected on {host}, skipping.")
        context = browser.contexts[0]
        page = await context.new_page()
        await page.goto(url, timeout=60000, wait_until="domcontentloaded")
        await asyncio.sleep(40)
    else:
        await agent.navigate_async(url)

    products_from_page = await ensure_listing_page(
        agent, page, url, out_dir, max_steps=3
    )
    products = [p for p in products_from_page if is_valid_product(p)]

    out_path = os.path.join(out_dir, f"inspection_{host}.json")
    os.makedirs(out_dir, exist_ok=True)

    if products:
        try:
            with open(out_path, "w", encoding="utf-8") as f:
                json.dump(
                    [p.model_dump(mode="json") for p in products],
                    f,
                    ensure_ascii=False,
                    indent=2,
                )
            priced_cnt = sum(1 for p in products if p.price)
            print(
                f"{host} -> {len(products)} items (with price: {priced_cnt}) saved: {out_path}"
            )
        except Exception as e:
            print(f"{host} -> save failed: {e}")
    else:
        print(f"{host} -> no products found (name+link/price)")

    await agent.close_async()


SITES = [
    "https://waydoo.com/",
]

CAPTURE_DETECT_URL = [
    "https://www.shop.com/",
]


async def main():
    api_key = os.getenv("AGENTBAY_API_KEY")
    if not api_key:
        print("Error: AGENTBAY_API_KEY is not set")
        return

    session_result = SessionResult(success=False)

    date_str = datetime.now().strftime("%Y-%m-%d")
    agent_bay = AgentBay(api_key=api_key)
    params = CreateSessionParams(image_id="browser_latest")
    session_result = agent_bay.create(params)
    if not session_result.success:
        print(f"Failed to create session: {session_result.error_message}")
        return

    session = session_result.session
    try:
        screen_option = BrowserScreen(width=1920, height=1080)
        browser_init_options = BrowserOption(
            screen=screen_option,
            solve_captchas=True,
        )
        ok = await session.browser.initialize_async(browser_init_options)
        if not ok:
            print("Failed to initialize browser")
            return
        endpoint = session.browser.get_endpoint_url()
        date_str = datetime.now().strftime("%Y-%m-%d")
        async with async_playwright() as p:
            print(f"Connecting to browser at {endpoint}")
            browser = await p.chromium.connect_over_cdp(endpoint)
            for url in SITES:
                try:
                    await process_site(
                        session, browser, url, out_dir=f"./results_{date_str}"
                    )
                except Exception as e:
                    print(f"[ERR] {domain_of(url)} -> {e}")

    finally:
        try:
            session.delete()
        except Exception:
            pass


if __name__ == "__main__":
    asyncio.run(main())
