import logging
from pydantic import BaseModel, Field, HttpUrl
from typing import List, Dict, Any, Optional
from mcp_server.page_agent import PageAgent


class PaperLink(BaseModel):
    title: str = Field(..., description="The title of the paper.")
    link: Optional[HttpUrl] = Field(
        ..., description="The direct link (URL) to the paper's page."
    )


class PaperLinkList(BaseModel):
    papers: List[PaperLink] = Field(
        ..., description="A list of papers found on the search results page."
    )


class PaperDetails(BaseModel):
    category: str = Field(
        ...,
        description="The category of the paper, e.g., 'Benchmark', 'Model', 'Framework'.",
    )
    problem: Optional[str] = Field(
        ..., description="A one-sentence summary of the problem the paper addresses."
    )
    methodology: Optional[str] = Field(
        ..., description="A one-sentence summary of the paper's methodology."
    )
    results: Optional[str] = Field(
        ..., description="A one-sentence summary of the paper's results."
    )
    conclusion: Optional[str] = Field(
        ..., description="A one-sentence summary of the paper's conclusion."
    )
    # code: Optional[HttpUrl] = Field(
    #     None, description="The link to the code repository, if provided."
    # )


async def run(agent: PageAgent, logger: logging.Logger, config: Dict[str, Any]) -> dict:
    """
    Tests a complex workflow: search, extract links, loop through links,
    and perform detailed extraction on each sub-page.
    """
    await agent.goto("https://arxiv.org/search/")

    await agent.act("type 'web agents with multimodal models' in the search bar")
    await agent.act("hit enter")
    import asyncio
    await asyncio.sleep(1)

    extract_method = config.get("extract_method", "domExtract")
    use_text_extract = extract_method == "textExtract"

    link_results: PaperLinkList = await agent.extract(
        instruction="extract the titles and links for two papers",
        schema=PaperLinkList,
        use_text_extract=use_text_extract,
    )

    if not link_results or not link_results.papers:
        return {
            "_success": False,
            "error": "Step 2 Failed: Could not extract initial paper links.",
        }

    processed_papers = []
    for paper_link in link_results.papers:
        if not paper_link.link:
            logger.warning(f"Skipping paper '{paper_link.title}' due to missing link.")
            continue

        await agent.goto(url=str(paper_link.link))

        details: PaperDetails = await agent.extract(
            instruction="extract details of the paper from the abstract",
            schema=PaperDetails,
            use_text_extract=use_text_extract,
        )

        paper_link_dict = paper_link.model_dump(mode="json")
        details_dict = details.model_dump(mode="json")

        combined_data = {**paper_link_dict, **details_dict}
        processed_papers.append(combined_data)

    logger.info(
        f"Finished processing. Validating {len(processed_papers)} extracted papers."
    )

    if len(processed_papers) != 2:
        error_msg = f"Validation Failed: Expected to process 2 papers, but ended up with {len(processed_papers)}."
        logger.error(error_msg)
        return {"_success": False, "error": error_msg}

    for paper in processed_papers:
        if not paper.get("problem") or not paper.get("methodology"):
            error_msg = f"Validation Failed: Paper '{paper.get('title')}' is missing a 'problem' or 'methodology' summary."
            logger.error(error_msg)
            return {"_success": False, "error": error_msg}

    logger.info(
        "✅ Validation Passed: Successfully extracted and processed 2 papers with full details."
    )
    return {"_success": True, "data": processed_papers}
