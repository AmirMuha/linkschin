"""Structured extraction pipeline using LangChain (MOCKED FOR USER IMPLEMENTATION).

========================================================================================
GUIDE FOR USER IMPLEMENTATION:
========================================================================================
To implement real LangChain extraction:
1. Initialize your LLM model:
   ```python
   from langchain_openai import ChatOpenAI
   import os
   llm = ChatOpenAI(
       api_key=os.environ.get("LLM_API_KEY"),
       model=os.environ.get("LLM_MODEL", "gpt-4o-mini"),
       base_url=os.environ.get("LLM_BASE_URL", "https://api.openai.com/v1"),
       temperature=0.0
   )
   ```
2. Bind the Pydantic schemas using with_structured_output:
   ```python
   movie_extractor = llm.with_structured_output(MovieExtractionResult)
   game_extractor = llm.with_structured_output(GameReleaseExtractionResult)
   music_extractor = llm.with_structured_output(MusicTrackExtractionResult)
   ```
3. Use `prune_html(html)` to strip scripts, styles, SVGs, and navigation chrome
   to minimize prompt tokens before passing into your prompt template.
========================================================================================
"""

from __future__ import annotations

import logging
import re
from selectolax.parser import HTMLParser

from models import (
    ExtractedDownloadVariant,
    ExtractedGamePart,
    GameReleaseExtractionResult,
    MovieExtractionResult,
    MusicTrackExtractionResult,
)

logger = logging.getLogger("extraction.chains")


def prune_html(raw_html: str, max_chars: int = 15000) -> str:
    """Strip script, style, SVG, and navigation noise to minimize LLM tokens."""
    if not raw_html:
        return ""
    try:
        tree = HTMLParser(raw_html)
        for tag in tree.css("script, style, svg, noscript, header, footer, nav"):
            tag.decompose()
        body = tree.body
        text = body.text(separator=" ", strip=True) if body else tree.text(separator=" ", strip=True)
        return text[:max_chars]
    except Exception as e:
        logger.warning("HTML pruning failed: %s; using slice", e)
        return raw_html[:max_chars]


# ============================================================================
# MOCK IMPLEMENTATIONS (Ready for User to Replace with LangChain)
# ============================================================================

async def extract_movie_metadata(html: str, url: str) -> MovieExtractionResult:
    """Extract movie title, year, IMDb score, and download links.

    # TODO: User implementation with LangChain:
    # prompt = ChatPromptTemplate.from_messages([
    #     ("system", "You are an expert Iranian movie portal scraper..."),
    #     ("user", "Extract movie download matrix from: {clean_html}")
    # ])
    # chain = prompt | movie_extractor
    # return await chain.ainvoke({"clean_html": prune_html(html)})
    """
    logger.info("Mocking LangChain movie extraction for URL: %s", url)

    # Clean heuristic fallback to keep pipeline running end-to-end
    tree = HTMLParser(html) if html else None
    title = ""
    if tree:
        h1 = tree.css_first("h1, .entry-title, .post-title")
        if h1:
            title = h1.text(strip=True)

    if not title:
        title = url.rstrip("/").split("/")[-1].replace("-", " ").capitalize()

    # Look for download links
    variants: list[ExtractedDownloadVariant] = []
    if tree:
        for a in tree.css("a[href]"):
            href = a.attributes.get("href", "")
            if re.search(r"\.(mp4|mkv|avi)$", href, re.I):
                text = a.text(strip=True)
                quality = "1080p" if "1080" in text or "1080" in href else ("720p" if "720" in text or "720" in href else "480p")
                codec = "x265" if "x265" in text or "x265" in href else "x264"
                is_dub = "دوبله" in text or "dub" in text.lower()
                audio = "FA-DUB" if is_dub else "ORIGINAL"
                variants.append(
                    ExtractedDownloadVariant(
                        quality=quality,
                        codec=codec,
                        audio_track=audio,
                        download_url=href,
                        file_size_text="1.5 GB",
                        is_censored=False,
                        is_premium=False,
                    )
                )

    return MovieExtractionResult(
        title=title,
        release_year=2024,
        description=f"Extracted metadata for {title}",
        poster_url=None,
        imdb_rating=7.5,
        variants=variants[:10],
    )


async def extract_game_release(html: str, url: str) -> GameReleaseExtractionResult:
    """Extract game title, release group, password, and multi-part links.

    # TODO: User implementation with LangChain:
    # chain = game_prompt | game_extractor
    # return await chain.ainvoke({"clean_html": prune_html(html)})
    """
    logger.info("Mocking LangChain game extraction for URL: %s", url)

    tree = HTMLParser(html) if html else None
    title = ""
    password = ""
    if tree:
        h1 = tree.css_first("h1, .entry-title")
        if h1:
            title = h1.text(strip=True)
        # Search for password
        pass_match = re.search(r"(?:رمز|پسورد|password)\s*[:：]\s*([a-zA-Z0-9\.\-\_]+)", html, re.I)
        if pass_match:
            password = pass_match.group(1).strip()

    if not title:
        title = url.rstrip("/").split("/")[-1].replace("-", " ").capitalize()

    parts: list[ExtractedGamePart] = []
    if tree:
        part_idx = 1
        for a in tree.css("a[href]"):
            href = a.attributes.get("href", "")
            if re.search(r"\.(rar|zip|iso|bin|part\d+\.rar)$", href, re.I):
                parts.append(
                    ExtractedGamePart(
                        part_number=part_idx,
                        part_label=f"Part {part_idx}",
                        file_size="2.0 GB",
                        download_url=href,
                    )
                )
                part_idx += 1

    return GameReleaseExtractionResult(
        title=title,
        release_group="FitGirl",
        version="v1.0",
        total_size="15 GB",
        archive_password=password or "www.downloadha.com",
        parts=parts,
    )


async def extract_music_track(html: str, url: str) -> MusicTrackExtractionResult:
    """Extract music title, artist, audio stream preview, and bitrate links.

    # TODO: User implementation with LangChain:
    # chain = music_prompt | music_extractor
    # return await chain.ainvoke({"clean_html": prune_html(html)})
    """
    logger.info("Mocking LangChain music extraction for URL: %s", url)

    tree = HTMLParser(html) if html else None
    title = ""
    artist = ""
    stream_url = None
    downloads: list[ExtractedDownloadVariant] = []

    if tree:
        h1 = tree.css_first("h1, .song-title, .post-title")
        if h1:
            raw_title = h1.text(strip=True)
            if " - " in raw_title:
                artist, title = raw_title.split(" - ", 1)
            else:
                title = raw_title

        # Look for audio stream
        audio_tag = tree.css_first("audio[src], source[src]")
        if audio_tag:
            stream_url = audio_tag.attributes.get("src")

        # Look for mp3 downloads
        for a in tree.css("a[href]"):
            href = a.attributes.get("href", "")
            if href.endswith(".mp3"):
                text = a.text(strip=True)
                bitrate = "320" if "320" in text or "320" in href else "128"
                downloads.append(
                    ExtractedDownloadVariant(
                        quality=f"{bitrate} kbps",
                        codec="mp3",
                        audio_track="ORIGINAL",
                        download_url=href,
                        file_size_text="8.5 MB" if bitrate == "320" else "3.5 MB",
                    )
                )

    if not title:
        title = url.rstrip("/").split("/")[-1].replace("-", " ").capitalize()

    return MusicTrackExtractionResult(
        title=title,
        artist=artist or "Unknown Artist",
        poster_url=None,
        stream_url=stream_url,
        downloads=downloads[:5],
    )
