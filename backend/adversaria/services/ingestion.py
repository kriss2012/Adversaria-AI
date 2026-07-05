"""
adversaria/services/ingestion.py — Brand asset ingestion pipeline.

Preprocessing LLM pass: parses brand guideline PDFs into semantic rule units
(color rules, typography rules, tone-of-voice, do's/don'ts) — NOT naive chunks.
"""
from __future__ import annotations

import io
import json
import tempfile
from pathlib import Path
from typing import Any

import boto3
from anthropic import AsyncAnthropic

from adversaria.config import get_settings
from adversaria.services.embeddings import get_embedding_service
from adversaria.services.vector_store import get_vector_store

_settings = get_settings()

RULE_EXTRACTION_SYSTEM = """You are a brand guidelines parser. Extract ALL brand rules from the text below.
For each rule, identify its type and extract the exact rule as a standalone statement.

Rule types: typography | color | logo_placement | spacing | tone_of_voice | dos_and_donts | imagery | grid

Respond ONLY with JSON array:
[
  {"rule_type": "typography", "rule_text": "Use Space Grotesk 700 as the primary typeface on all digital assets.", "source_file": "brand_book.pdf"},
  ...
]

Extract ALL rules. Be comprehensive — each rule should be independently retrievable."""


def _get_s3_client():
    return boto3.client(
        "s3",
        endpoint_url=_settings.s3_endpoint_url,
        aws_access_key_id=_settings.s3_access_key_id,
        aws_secret_access_key=_settings.s3_secret_access_key,
        region_name=_settings.s3_region,
    )


async def ingest_brand_assets(brand_id: str, s3_keys: list[str]) -> dict[str, Any]:
    """
    Main ingestion pipeline:
    1. Download assets from S3
    2. Extract text from PDFs / parse SVG/image metadata
    3. LLM pass: extract semantic rule units
    4. Embed rules and upsert into Qdrant brand_rules collection
    5. Embed images and upsert into Qdrant moodboards collection
    """
    s3 = _get_s3_client()
    emb = get_embedding_service()
    vs = get_vector_store()

    all_rules: list[dict[str, Any]] = []
    processed_keys = []
    errors = []

    for s3_key in s3_keys:
        try:
            # Download from S3
            obj = s3.get_object(Bucket=_settings.s3_bucket_name, Key=s3_key)
            content = obj["Body"].read()
            filename = Path(s3_key).name
            ext = Path(s3_key).suffix.lower()

            if ext == ".pdf":
                rules = await _extract_pdf_rules(content, filename)
                all_rules.extend(rules)
            elif ext in {".png", ".jpg", ".jpeg", ".webp"}:
                await _ingest_image_asset(brand_id, s3_key, content, filename, vs, emb)
            elif ext == ".svg":
                # SVGs are stored by reference; extract any embedded text
                svg_text = content.decode("utf-8", errors="ignore")
                rules = await _extract_text_rules(svg_text[:2000], filename)
                all_rules.extend(rules)
            elif ext == ".json":
                # Brand token files (design tokens, color systems)
                token_data = json.loads(content)
                rules = _parse_design_tokens(token_data, filename)
                all_rules.extend(rules)

            processed_keys.append(s3_key)

        except Exception as exc:
            errors.append({"key": s3_key, "error": str(exc)})

    # Batch embed all extracted rules
    if all_rules:
        rule_texts = [r["rule_text"] for r in all_rules]
        embeddings = await emb.embed_texts(rule_texts, input_type="document")
        upserted_ids = await vs.upsert_brand_rules(brand_id, all_rules, embeddings)

        return {
            "brand_id": brand_id,
            "rules_extracted": len(all_rules),
            "rules_upserted": len(upserted_ids),
            "processed_keys": processed_keys,
            "errors": errors,
        }

    return {
        "brand_id": brand_id,
        "rules_extracted": 0,
        "processed_keys": processed_keys,
        "errors": errors,
    }


async def _extract_pdf_rules(content: bytes, filename: str) -> list[dict[str, Any]]:
    """Extract text from PDF then run LLM rule extraction pass."""
    try:
        from pypdf import PdfReader  # noqa: PLC0415

        reader = PdfReader(io.BytesIO(content))
        full_text = "\n".join(
            page.extract_text() or "" for page in reader.pages
        )
    except Exception:
        full_text = ""

    if not full_text.strip():
        return []

    return await _extract_text_rules(full_text, filename)


async def _extract_text_rules(text: str, filename: str) -> list[dict[str, Any]]:
    """
    LLM pass: parse raw text into structured semantic rule units.
    This is the key insight — NOT naive chunking. Each rule is independently retrievable.
    """
    client = AsyncAnthropic(api_key=_settings.anthropic_api_key)

    # Process in chunks of 8k chars to stay within context limits
    chunks = [text[i:i+8000] for i in range(0, len(text), 8000)]
    all_rules: list[dict[str, Any]] = []

    for chunk in chunks[:5]:  # Max 5 chunks per file
        response = await client.messages.create(
            model=_settings.critic_model,  # cheapest model for extraction
            max_tokens=2000,
            system=RULE_EXTRACTION_SYSTEM,
            messages=[{
                "role": "user",
                "content": f"Source file: {filename}\n\nText to parse:\n{chunk}"
            }],
        )

        raw = response.content[0].text.strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]

        try:
            rules = json.loads(raw)
            if isinstance(rules, list):
                all_rules.extend(rules)
        except json.JSONDecodeError:
            pass

    return all_rules


async def _ingest_image_asset(
    brand_id: str,
    s3_key: str,
    content: bytes,
    filename: str,
    vs,
    emb,
) -> None:
    """Save image to temp file, generate CLIP embedding, upsert to moodboards."""
    import uuid  # noqa: PLC0415
    with tempfile.NamedTemporaryFile(suffix=Path(filename).suffix, delete=False) as tmp:
        tmp.write(content)
        tmp_path = Path(tmp.name)

    try:
        image_embedding = await emb.embed_image_file(tmp_path)
        asset_id = str(uuid.uuid4())
        await vs.upsert_moodboard(
            brand_id=brand_id,
            asset_id=asset_id,
            image_embedding=image_embedding,
            metadata={"s3_key": s3_key, "filename": filename},
        )
    finally:
        tmp_path.unlink(missing_ok=True)


def _parse_design_tokens(token_data: dict, filename: str) -> list[dict[str, Any]]:
    """
    Parse design token JSON files (W3C format or custom) into brand rules.
    Extracts color tokens, typography tokens, spacing scales.
    """
    rules = []
    if isinstance(token_data, dict):
        for category, values in token_data.items():
            if isinstance(values, dict):
                for token_name, token_value in values.items():
                    if isinstance(token_value, dict) and "$value" in token_value:
                        rules.append({
                            "rule_type": _categorize_token(category),
                            "rule_text": f"Token '{category}.{token_name}' = {token_value['$value']}",
                            "source_file": filename,
                        })
    return rules


def _categorize_token(category: str) -> str:
    category_lower = category.lower()
    if any(k in category_lower for k in ["color", "colour", "palette"]):
        return "color"
    if any(k in category_lower for k in ["font", "type", "text"]):
        return "typography"
    if any(k in category_lower for k in ["space", "gap", "margin", "padding"]):
        return "spacing"
    return "token"
