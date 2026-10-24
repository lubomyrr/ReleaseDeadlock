"""Download a Deadlock Wiki update and save its article body as Markdown."""

import argparse
import re
from datetime import date
from pathlib import Path
from urllib.parse import quote, unquote, urlsplit, urlunsplit

import httpx
from bs4 import BeautifulSoup
from markdownify import markdownify


RAW_DIR = Path(__file__).resolve().parents[1] / "data" / "raw"
MONTHS = (
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December",
)


def normalize_url(url: str) -> str:
    parts = urlsplit(url.strip())
    path = unquote(parts.path)
    if (
        parts.scheme not in {"http", "https"}
        or parts.netloc.lower() not in {"deadlock.wiki", "www.deadlock.wiki"}
        or not path.startswith("/Update:")
        or parts.query
    ):
        raise ValueError("Expected a URL like https://deadlock.wiki/Update:October_20,_2026")
    return urlunsplit(("https", "deadlock.wiki", quote(path, safe="/:,_-"), "", ""))


def default_output_path(url: str) -> Path:
    title = unquote(urlsplit(url).path).removeprefix("/Update:").replace("_", " ")
    match = re.fullmatch(r"([A-Za-z]+) (\d{1,2}), (\d{4})", title)
    if not match or match[1] not in MONTHS:
        raise ValueError("Cannot determine the patch date from the URL; specify --output")
    patch_date = date(int(match[3]), MONTHS.index(match[1]) + 1, int(match[2]))
    return RAW_DIR / f"patch_{patch_date:%Y_%m_%d}.md"


def html_to_markdown(html: str, url: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    article = soup.select_one("#mw-content-text .mw-parser-output")
    if article is None:
        raise ValueError("Wiki article not found; the server may have returned an error or challenge page")
    content = article.select_one(".update-layout-container")
    if content is None:
        content = article

    heading = soup.select_one("#firstHeading .mw-page-title-main")
    title = (
        heading.get_text(" ", strip=True)
        if heading is not None
        else unquote(urlsplit(url).path).removeprefix("/").replace("_", " ")
    )

    # Remove only site UI, not all tables: some patches contain useful data tables.
    for selector in (
        "script", "style", "noscript", "nav", ".update-layout-nav",
        "#toc", ".toc", ".mw-editsection", ".navbox", ".catlinks",
        ".printfooter", ".noprint", ".mw-empty-elt", ".update-layout-source",
    ):
        for node in content.select(selector):
            node.decompose()

    # Hero/item icons normally have a text label next to them; keep that label once.
    for image in content.select("img"):
        image.decompose()
    for link in content.select("a"):
        if not link.get_text(strip=True):
            link.decompose()
        else:
            link.unwrap()

    if not content.get_text(strip=True):
        raise ValueError("The patch body is empty")

    body = markdownify(
        str(content),
        heading_style="ATX",
        bullets="-",
        newline_style="BACKSLASH",
        wrap=False,
    ).replace("\xa0", " ")
    # Keep indentation intact: nested lists depend on it.
    body = "\n".join(
        re.sub(r"(?<=\S)[ \t]{2,}(?=\S)", " ", line.rstrip())
        for line in body.splitlines()
    )
    body = re.sub(r"\n{3,}", "\n\n", body).strip()
    return f"# {title}\n\n{body}\n"


def fetch_patch(url: str, output: Path | None = None, *, overwrite: bool = False) -> Path:
    url = normalize_url(url)
    output = Path(output) if output is not None else default_output_path(url)
    if output.exists() and not overwrite:
        raise FileExistsError(f"File already exists: {output}. Use --overwrite to replace it")

    response = httpx.get(
        url,
        follow_redirects=True,
        timeout=30.0,
        headers={"User-Agent": "ReleaseDeadlock-PatchMarkdown/1.0", "Accept": "text/html"},
    )
    response.raise_for_status()
    markdown = html_to_markdown(response.text, url)

    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w" if overwrite else "x", encoding="utf-8", newline="\n") as file:
        file.write(markdown)
    return output


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("url", help="Deadlock Wiki Update page URL")
    parser.add_argument("-o", "--output", type=Path, help="Output .md path (default: data/raw/patch_YYYY_MM_DD.md)")
    parser.add_argument("--overwrite", action="store_true", help="Replace an existing output file")
    args = parser.parse_args()
    try:
        output = fetch_patch(args.url, args.output, overwrite=args.overwrite)
    except (httpx.HTTPError, ValueError, OSError) as exc:
        parser.exit(1, f"Error: {exc}\n")
    print(f"Saved: {output}")


if __name__ == "__main__":
    main()
