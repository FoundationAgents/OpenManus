import os
import asyncio
import json
from pydantic import BaseModel, Field
from datetime import datetime
from typing import List, Optional, Dict, Any
from urllib.parse import urlparse, urljoin
import base64
import logging


from agentbay.browser.browser_agent import ActOptions
from agentbay.browser.eval.page_agent import PageAgent

logger = logging.getLogger(__name__)


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
    logger.info(f"Acting: {instruction}")
    ret = await agent.act(ActOptions(action=instruction))
    return bool(getattr(ret, "success", False))


async def take_and_save_screenshot(agent, base_url: str, out_dir: str):
    base64_screenshot = await agent.screenshot()
    if not base64_screenshot.startswith("screenshot failed:"):
        host = domain_of(base_url)
        os.makedirs(out_dir, exist_ok=True)
        screenshot_path = os.path.join(out_dir, f"screenshot_{host}.png")
        with open(screenshot_path, "wb") as f:
            f.write(base64.b64decode(base64_screenshot))

        logger.info(f"{base_url} -> Screenshot saved via agent: {screenshot_path}")


async def extract_products(
    agent, page, base_url: str, out_dir: str
) -> List[ProductInfo]:
    data = await agent.extract(
        instruction=(
            "请提取本页所有商品。价格可为范围（例如 $199–$299）或“from $199”。"
            "对于商品链接(link)，请仅返回相对路径（例如 /path/to/product），不要包含域名。"
        ),
        schema=InspectionResult,
        use_text_extract=True,
    )
    if not isinstance(data, InspectionResult) or not data.products:
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
        products_found = await extract_products(agent, page, base_url, out_dir)
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

    logger.info(f"All {max_steps} extraction attempts failed for {base_url}.")
    return []


async def process_site(agent, url: str, out_dir: str = "/tmp") -> None:
    host = domain_of(url)

    page = None
    if url in CAPTURE_DETECT_URL:
        print(f"CAPTCHA detected on {host}, skipping.")
        context = browser.contexts[0]
        page = await context.new_page()
        await page.goto(url, timeout=60000, wait_until="domcontentloaded")
        await asyncio.sleep(40)
    else:
        await agent.navigate(url)

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
            logger.info(
                f"{host} -> {len(products)} items (with price: {priced_cnt}) saved: {out_path}"
            )
        except Exception as e:
            logger.info(f"{host} -> save failed: {e}")
    else:
        logger.info(f"{host} -> no products found (name+link/price)")


SITES = [
    "https://milatech.shop/",
    "https://waydoo.com/",
    "https://aspirebuildingmaterials.com/",
    "https://mgolightingtech.com/",
    "https://www.emootoom.com/",
    "https://censlighting.com/",
    "https://welomall.com/",
    "https://www.szcxi.com/",
    "https://tegner.shop/",
]

CAPTURE_DETECT_URL = [
    "https://censlighting.com/",
]


async def run(agent: PageAgent, logger: logging.Logger, config: Dict[str, Any]) -> dict:
    """
    Performs a paginated e-commerce site inspection.
    """

    date_str = datetime.now().strftime("%Y-%m-%d")
    for url in SITES:
        try:
            await process_site(agent, url, out_dir=f"./results_{date_str}")
        except Exception as e:
            logger.info(f"[ERR] {domain_of(url)} -> {e}")

    return {"_success": True}
