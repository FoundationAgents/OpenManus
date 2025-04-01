import aiohttp
from bs4 import BeautifulSoup
from typing import List

from app.tool.base import BaseTool


class BingSearch(BaseTool):
    name: str = "bing_search"
    description: str = """使用必应搜索返回相关链接列表。
    当需要查找网络信息、获取最新数据或研究特定主题时使用此工具。
    该工具返回与搜索查询匹配的URL列表。
    """
    parameters: dict = {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "(必填) 提交给必应的搜索查询。",
            },
            "num_results": {
                "type": "integer",
                "description": "(可选) 要返回的搜索结果数量。默认为10。",
                "default": 10,
            },
        },
        "required": ["query"],
    }

    async def execute(self, query: str, num_results: int = 10) -> List[str]:
        """
        执行必应搜索并返回URL列表。

        参数:
            query (str): 要提交给必应的搜索查询。
            num_results (int, optional): 要返回的搜索结果数量。默认为10。

        返回:
            List[str]: 与搜索查询匹配的URL列表。
        """
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        search_url = f"https://www.bing.com/search?q={query}"

        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(search_url, headers=headers) as response:
                    response.raise_for_status()
                    html = await response.text()
            except Exception as e:
                raise RuntimeError(f"必应搜索请求失败: {str(e)}")

        soup = BeautifulSoup(html, 'html.parser')
        links = []

        # 必应搜索结果链接通常在类名为"b_algo"的div内，具体选择器可能需要根据实际页面结构调整
        for result in soup.select('.b_algo'):
            a_tag = result.select_one('a')
            if a_tag and 'href' in a_tag.attrs:
                link = a_tag['href']
                links.append(link)
                if len(links) >= num_results:
                    break

        return links[:num_results]