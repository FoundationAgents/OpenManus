import asyncio
import os
import re
import hashlib
from typing import ClassVar, Dict, Optional
from urllib.parse import urlparse

from pydantic import BaseModel, Field

from app.exceptions import ToolError
from app.logger import logger
from app.tool.base import BaseTool, ToolResult
from app.tool.browser_use_tool import BrowserUseTool


class WebpageExtractResult(BaseModel):
    """Model representing the result of a webpage content extraction"""
    url: str = Field(description="URL of the webpage that was processed")
    title: Optional[str] = Field(None, description="Title of the webpage")
    text_content: Optional[str] = Field(None, description="Extracted text content from the webpage")
    storage_path: Optional[str] = Field(None, description="Path to file where full content is stored")


class WebpageExtractResponse(ToolResult):
    """Structured response from the webpage extractor tool"""
    url: str = Field(description="URL of the webpage that was processed")
    result: Optional[WebpageExtractResult] = Field(
        None, description="Extraction result details"
    )

    def __init__(self, **data):
        super().__init__(**data)
        self._format_output()

    def _format_output(self):
        """Format extraction results as a readable string output"""
        if self.error:
            return

        if not self.result:
            self.output = f"Failed to extract content from {self.url}"
            return

        result_text = [f"Content extracted from: {self.url}"]

        if self.result.title:
            result_text.append(f"Title: {self.result.title}")

        # Add storage path information if content was saved to file
        if self.result.storage_path:
            result_text.append(f"\n内容已保存到文件: {self.result.storage_path}")
            result_text.append("您可以使用read_file工具查看文件内容，或者直接在后续处理中引用此文件。")
        elif self.result.text_content:
            # 只显示内容预览
            preview = self.result.text_content[:500]
            if len(self.result.text_content) > 500:
                preview += "..."
            result_text.append(f"\n内容预览:\n{preview}")

        self.output = "\n".join(result_text)


class WebpageExtractor(BaseTool):
    """Tool for extracting content from webpages"""

    name: str = "webpage_extractor"
    description: str = """
    轻量级的网页文本内容提取工具，使用浏览器来加载网页并提取纯文本内容。
    此工具使用Playwright直接提取网页文本，无需复杂的处理逻辑。
    对于长内容，工具会自动保存到文件，避免token溢出。
    """
    parameters: dict = {
        "type": "object",
        "properties": {
            "url": {
                "type": "string",
                "description": "(必填) 要提取内容的网页URL",
            },
            "wait_time": {
                "type": "integer",
                "description": "(可选) 页面加载后等待时间(秒)，用于确保动态内容加载完成（默认: 2）",
                "default": 2,
            },
            "save_to_file": {
                "type": "boolean",
                "description": "(可选) 是否将提取的内容保存到文件（默认: false，但对于超长内容会自动开启）",
                "default": False,
            },
        },
        "required": ["url"],
    }


    # Browser tool for JavaScript rendering
    browser_tool: BrowserUseTool = Field(default_factory=BrowserUseTool)

    # 临时文件保存的目录
    storage_dir: str = Field(default="./workspace/webpage_extracts")

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # 确保存储目录存在
        os.makedirs(self.storage_dir, exist_ok=True)

    def _get_storage_filename(self, url: str, title: Optional[str] = None) -> str:
        """根据URL和标题生成存储文件名"""
        # 使用URL生成唯一哈希
        url_hash = hashlib.md5(url.encode()).hexdigest()[:8]

        # 从URL提取域名部分
        parsed_url = urlparse(url)
        domain = parsed_url.netloc.replace("www.", "")

        # 避免文件名中出现中文字符
        # 如果标题存在且不为空，使用标题的英文字母和数字部分
        if title and title.strip():
            # 只保留英文字母、数字和部分标点符号，移除所有中文和其他字符
            english_title = re.sub(r'[^\x00-\x7F]+', '', title)  # 移除所有非ASCII字符
            clean_title = re.sub(r'[^\w\s-]', '', english_title)  # 进一步清理
            clean_title = re.sub(r'[\s-]+', '_', clean_title).strip('_')

            # 如果清理后的标题为空，则使用默认名称
            if clean_title:
                name_part = clean_title[:50]  # 限制长度
            else:
                name_part = f"webpage_{url_hash[:6]}"  # 使用默认名称加短哈希
        else:
            # 使用URL的路径部分或域名
            name_part = f"webpage_{url_hash[:6]}"

        # 确保文件名只包含安全字符
        name_part = re.sub(r'[^\w_-]', '', name_part)

        # 组合文件名
        filename = f"{domain}_{name_part}_{url_hash}.txt"
        return os.path.join(self.storage_dir, filename)

    def _save_content_to_file(self, content: str, filepath: str) -> bool:
        """将内容保存到文件"""
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)
            logger.info(f"内容已保存到文件: {filepath}")
            return True
        except Exception as e:
            logger.error(f"保存内容到文件失败: {str(e)}")
            return False

    async def execute(
        self,
        url: str,
        wait_time: int = 2,
        save_to_file: bool = False,
    ) -> WebpageExtractResponse:
        """
        执行网页内容提取。

        参数:
            url: 要提取内容的网页URL
            wait_time: 页面加载后等待时间（秒），用于确保动态内容加载完成
            save_to_file: 是否将提取的内容保存到文件

        返回:
            包含提取结果的结构化响应
        """
        # 定义内容长度阈值，超过此长度将自动保存到文件
        CONTENT_LENGTH_THRESHOLD = 5000

        try:
            # 验证URL
            parsed_url = urlparse(url)
            if not parsed_url.scheme:
                url = f"https://{url}"
                logger.info(f"添加HTTPS协议: {url}")

            # 检查是否可能是专利页面
            if "patent" in url.lower() or "专利" in url:
                logger.info("检测到专利页面，增加等待时间")
                wait_time = max(wait_time, 3)  # 确保专利页面有足够加载时间

            # 使用浏览器提取网页内容
            logger.info(f"提取网页内容: {url}")
            text_content, page_title = await self._extract_text_with_browser(url, wait_time)

            if not text_content or len(text_content.strip()) < 10:
                raise ToolError("获取的网页内容为空或过短")

            # 初始化结果
            result = WebpageExtractResult(url=url, title=page_title, text_content=text_content)

            # 保存内容到文件（如果需要）
            content_length = len(text_content)
            if save_to_file or content_length > CONTENT_LENGTH_THRESHOLD:
                storage_path = self._get_storage_filename(url, page_title)
                if self._save_content_to_file(text_content, storage_path):
                    result.storage_path = storage_path
                    logger.info(f"内容已保存到文件: {storage_path}")

            return WebpageExtractResponse(url=url, result=result)

        except ToolError as e:
            logger.error(f"网页提取错误: {str(e)}")
            return WebpageExtractResponse(url=url, error=str(e))
        except Exception as e:
            logger.error(f"提取网页内容时出现意外错误: {str(e)}")
            return WebpageExtractResponse(url=url, error=f"提取网页内容失败: {str(e)}")

    async def _extract_text_with_browser(self, url: str, wait_time: int = 2) -> tuple:
        """使用浏览器直接提取页面文本内容和标题"""
        try:
            # 初始化浏览器并导航到URL
            browser_result = await self.browser_tool.execute(action="go_to_url", url=url)
            if browser_result and browser_result.error:
                raise ToolError(f"导航到URL失败: {browser_result.error}")

            # 获取当前页面
            if not self.browser_tool.context:
                raise ToolError("浏览器上下文未初始化")

            page = await self.browser_tool.context.get_current_page()
            if not page:
                raise ToolError("获取当前页面失败")

            # 等待页面加载完成
            await page.wait_for_load_state("networkidle")
            logger.info(f"等待页面加载 {wait_time} 秒...")
            await asyncio.sleep(wait_time)

            # 获取页面标题
            page_title = await page.title()

            # 直接使用text_content()获取body文本内容
            body_element = await page.query_selector("body")
            if not body_element:
                raise ToolError("无法找到body元素")

            body_text = await body_element.text_content()

            # 清理文本内容：保留关键的换行，去除多余空行
            cleaned_text = "\n".join(line.strip() for line in body_text.splitlines() if line.strip())

            logger.info(f"成功提取页面文本，长度为{len(cleaned_text)}字符")
            return cleaned_text, page_title

        except Exception as e:
            raise ToolError(f"浏览器提取内容失败: {str(e)}")
