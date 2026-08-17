"""SEO Analysis Tool for analyzing website SEO metrics and recommendations."""
import re
from typing import Any, Dict, List
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

from app.tool.base import BaseTool, ToolResult


class SEOAnalyzer(BaseTool):
    """A tool for performing comprehensive SEO analysis on websites."""

    name: str = "seo_analyzer"
    description: str = (
        "Performs comprehensive SEO analysis on websites including meta tags, "
        "headers, links, content quality, and provides actionable recommendations."
    )
    parameters: dict = {
        "type": "object",
        "properties": {
            "url": {
                "type": "string",
                "description": "The URL of the website to analyze for SEO.",
            },
            "detailed": {
                "type": "boolean",
                "description": "Whether to perform detailed analysis including content metrics.",
                "default": True,
            },
        },
        "required": ["url"],
    }

    async def execute(
        self,
        url: str,
        detailed: bool = True,
        timeout: int = 10,
    ) -> ToolResult:
        """
        Performs SEO analysis on the given URL.

        Args:
            url (str): The URL to analyze.
            detailed (bool): Whether to perform detailed analysis.
            timeout (int): Request timeout in seconds.

        Returns:
            ToolResult: Contains analysis results and recommendations.
        """
        try:
            # Validate URL
            if not url.startswith(("http://", "https://")):
                url = f"https://{url}"

            # Fetch the webpage
            headers = {
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
                )
            }
            response = requests.get(url, headers=headers, timeout=timeout)
            response.raise_for_status()

            # Parse HTML
            soup = BeautifulSoup(response.text, "html.parser")

            # Perform analysis
            analysis = {
                "url": url,
                "status_code": response.status_code,
                "meta_tags": self._analyze_meta_tags(soup),
                "headers": self._analyze_headers(soup),
                "links": self._analyze_links(soup, url),
                "images": self._analyze_images(soup),
                "performance": self._analyze_performance_metrics(
                    soup, response, detailed
                ),
                "accessibility": self._analyze_accessibility(soup),
                "recommendations": [],
            }

            # Generate recommendations
            analysis["recommendations"] = self._generate_recommendations(analysis)

            # Calculate overall SEO score
            analysis["seo_score"] = self._calculate_seo_score(analysis)

            return ToolResult(output=analysis)

        except requests.RequestException as e:
            return ToolResult(
                error=f"Failed to fetch URL: {str(e)}", output={"url": url}
            )
        except Exception as e:
            return ToolResult(error=f"SEO analysis error: {str(e)}")

    def _analyze_meta_tags(self, soup: BeautifulSoup) -> Dict[str, Any]:
        """Analyze meta tags for SEO optimization."""
        meta_data = {
            "title": None,
            "description": None,
            "keywords": None,
            "author": None,
            "viewport": None,
            "charset": None,
            "og_tags": {},
            "twitter_tags": {},
            "issues": [],
        }

        # Title tag
        title_tag = soup.find("title")
        if title_tag:
            meta_data["title"] = title_tag.string
            title_length = len(title_tag.string) if title_tag.string else 0
            if title_length < 30:
                meta_data["issues"].append(
                    f"Title too short ({title_length} chars, recommended 50-60)"
                )
            elif title_length > 60:
                meta_data["issues"].append(
                    f"Title too long ({title_length} chars, recommended 50-60)"
                )
        else:
            meta_data["issues"].append("Missing title tag")

        # Meta description
        desc_tag = soup.find("meta", attrs={"name": "description"})
        if desc_tag:
            meta_data["description"] = desc_tag.get("content", "")
            desc_length = len(meta_data["description"])
            if desc_length < 120:
                meta_data["issues"].append(
                    f"Description too short ({desc_length} chars, recommended 120-160)"
                )
            elif desc_length > 160:
                meta_data["issues"].append(
                    f"Description too long ({desc_length} chars, recommended 120-160)"
                )
        else:
            meta_data["issues"].append("Missing meta description")

        # Keywords
        keywords_tag = soup.find("meta", attrs={"name": "keywords"})
        if keywords_tag:
            meta_data["keywords"] = keywords_tag.get("content", "")

        # Charset
        charset_tag = soup.find("meta", attrs={"charset": True})
        if charset_tag:
            meta_data["charset"] = charset_tag.get("charset", "")
        else:
            meta_data["issues"].append("Missing charset meta tag")

        # Viewport
        viewport_tag = soup.find("meta", attrs={"name": "viewport"})
        if viewport_tag:
            meta_data["viewport"] = viewport_tag.get("content", "")
        else:
            meta_data["issues"].append(
                "Missing viewport meta tag (mobile responsiveness)"
            )

        # Open Graph tags
        og_tags = soup.find_all("meta", attrs={"property": re.compile(r"^og:")})
        for tag in og_tags:
            property_name = tag.get("property", "").replace("og:", "")
            meta_data["og_tags"][property_name] = tag.get("content", "")

        # Twitter tags
        twitter_tags = soup.find_all("meta", attrs={"name": re.compile(r"^twitter:")})
        for tag in twitter_tags:
            name = tag.get("name", "").replace("twitter:", "")
            meta_data["twitter_tags"][name] = tag.get("content", "")

        return meta_data

    def _analyze_headers(self, soup: BeautifulSoup) -> Dict[str, Any]:
        """Analyze header structure for SEO."""
        headers = {
            "h1": [],
            "h2": [],
            "h3": [],
            "structure": [],
            "issues": [],
        }

        h1_tags = soup.find_all("h1")
        h2_tags = soup.find_all("h2")
        h3_tags = soup.find_all("h3")

        headers["h1"] = [tag.get_text().strip() for tag in h1_tags]
        headers["h2"] = [tag.get_text().strip() for tag in h2_tags]
        headers["h3"] = [tag.get_text().strip() for tag in h3_tags]

        # Check header hierarchy
        if len(h1_tags) == 0:
            headers["issues"].append("Missing H1 tag")
        elif len(h1_tags) > 1:
            headers["issues"].append(f"Multiple H1 tags found ({len(h1_tags)})")

        headers["structure"] = {
            "h1_count": len(h1_tags),
            "h2_count": len(h2_tags),
            "h3_count": len(h3_tags),
        }

        return headers

    def _analyze_links(self, soup: BeautifulSoup, base_url: str) -> Dict[str, Any]:
        """Analyze internal and external links."""
        links = {
            "internal": [],
            "external": [],
            "broken_anchor_text": [],
            "total_links": 0,
            "issues": [],
        }

        parsed_base = urlparse(base_url)
        base_domain = parsed_base.netloc

        for link in soup.find_all("a", href=True):
            href = link.get("href", "")
            text = link.get_text().strip()

            if not href:
                links["broken_anchor_text"].append({"href": href, "text": text})
                continue

            # Skip anchors and javascript
            if href.startswith("#") or href.startswith("javascript:"):
                continue

            if href.startswith("http"):
                parsed_href = urlparse(href)
                if parsed_href.netloc == base_domain:
                    links["internal"].append({"url": href, "text": text})
                else:
                    links["external"].append({"url": href, "text": text})
            else:
                full_url = urljoin(base_url, href)
                links["internal"].append({"url": full_url, "text": text})

            # Check for empty anchor text
            if not text:
                links["issues"].append(f"Empty anchor text for link: {href}")

        links["total_links"] = len(links["internal"]) + len(links["external"])

        return links

    def _analyze_images(self, soup: BeautifulSoup) -> Dict[str, Any]:
        """Analyze images for SEO optimization."""
        images = {
            "total": 0,
            "with_alt": 0,
            "without_alt": [],
            "issues": [],
        }

        img_tags = soup.find_all("img")
        images["total"] = len(img_tags)

        for img in img_tags:
            if img.get("alt"):
                images["with_alt"] += 1
            else:
                src = img.get("src", "unknown")
                images["without_alt"].append(src)
                images["issues"].append(f"Image missing alt text: {src}")

        return images

    def _analyze_performance_metrics(
        self, soup: BeautifulSoup, response: requests.Response, detailed: bool
    ) -> Dict[str, Any]:
        """Analyze performance-related metrics."""
        metrics = {
            "page_size_kb": len(response.content) / 1024,
            "content_length": len(response.text),
            "word_count": len(response.text.split()),
            "paragraphs": len(soup.find_all("p")),
            "has_css": len(soup.find_all("link", attrs={"rel": "stylesheet"})) > 0,
            "has_js": len(soup.find_all("script")) > 0,
            "mobile_optimized": soup.find("meta", attrs={"name": "viewport"})
            is not None,
            "issues": [],
        }

        if metrics["page_size_kb"] > 5000:
            metrics["issues"].append(
                f"Large page size: {metrics['page_size_kb']:.1f} KB (recommended < 5 MB)"
            )

        if metrics["word_count"] < 300:
            metrics["issues"].append(
                f"Low word count: {metrics['word_count']} words (recommended 300+)"
            )

        return metrics

    def _analyze_accessibility(self, soup: BeautifulSoup) -> Dict[str, Any]:
        """Analyze accessibility features."""
        accessibility = {
            "has_lang_attribute": False,
            "has_skip_link": False,
            "issues": [],
        }

        # Check for lang attribute
        html_tag = soup.find("html")
        if html_tag and html_tag.get("lang"):
            accessibility["has_lang_attribute"] = True
        else:
            accessibility["issues"].append("Missing lang attribute on HTML tag")

        # Check for skip links
        skip_links = soup.find_all("a", string=re.compile(r"skip", re.I))
        if skip_links:
            accessibility["has_skip_link"] = True

        return accessibility

    def _generate_recommendations(self, analysis: Dict[str, Any]) -> List[str]:
        """Generate SEO recommendations based on analysis."""
        recommendations = []

        # Meta tag recommendations
        if analysis["meta_tags"]["issues"]:
            recommendations.extend(analysis["meta_tags"]["issues"])

        # Header recommendations
        if analysis["headers"]["issues"]:
            recommendations.extend(analysis["headers"]["issues"])

        # Link recommendations
        if len(analysis["links"]["internal"]) < 3:
            recommendations.append("Add more internal links (recommended 3+)")

        # Image recommendations
        if analysis["images"]["issues"]:
            recommendations.extend(analysis["images"]["issues"])

        # Performance recommendations
        if analysis["performance"]["issues"]:
            recommendations.extend(analysis["performance"]["issues"])

        # Accessibility recommendations
        if analysis["accessibility"]["issues"]:
            recommendations.extend(analysis["accessibility"]["issues"])

        if not recommendations:
            recommendations.append("Great! Your SEO looks good.")

        return recommendations[:10]  # Return top 10 recommendations

    def _calculate_seo_score(self, analysis: Dict[str, Any]) -> int:
        """Calculate overall SEO score (0-100)."""
        score = 100
        issue_count = (
            len(analysis["meta_tags"].get("issues", []))
            + len(analysis["headers"].get("issues", []))
            + len(analysis["links"].get("issues", []))
            + len(analysis["images"].get("issues", []))
            + len(analysis["performance"].get("issues", []))
            + len(analysis["accessibility"].get("issues", []))
        )

        # Deduct points for issues
        score -= min(issue_count * 5, 50)

        # Bonus for good practices
        if analysis["meta_tags"].get("og_tags"):
            score += 5
        if analysis["meta_tags"].get("twitter_tags"):
            score += 5
        if analysis["performance"]["mobile_optimized"]:
            score += 10

        return max(score, 0)
