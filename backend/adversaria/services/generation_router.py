"""
adversaria/services/generation_router.py — Multi-backend image generation router.

Optimizes cost / quality / legal-safety tradeoffs at runtime.
Never hardcodes a single backend — every generation task is routed based on
task properties: brand typography needs, budget tier, licensing requirements.
"""
from __future__ import annotations

import asyncio
import hashlib
import json
from typing import Any

import httpx

from adversaria.config import get_settings
from adversaria.schemas import GenTask, GenerationBackend, Platform

_settings = get_settings()

# ─── Platform specs (NEVER hallucinate — hardcoded facts) ─────────────────────
PLATFORM_SPECS: dict[str, dict[str, Any]] = {
    Platform.INSTAGRAM_FEED.value:    {"width": 1080, "height": 1080, "aspect": "1:1"},
    Platform.INSTAGRAM_STORY.value:   {"width": 1080, "height": 1920, "aspect": "9:16"},
    Platform.LINKEDIN_SINGLE.value:   {"width": 1080, "height": 1350, "aspect": "4:5"},
    Platform.BANNER_16_9.value:       {"width": 1920, "height": 1080, "aspect": "16:9"},
    Platform.META_ADS.value:          {"width": 1080, "height": 1080, "aspect": "1:1"},
    Platform.TIKTOK.value:            {"width": 1080, "height": 1920, "aspect": "9:16"},
}


class GenerationRouter:
    """Routes GenTask to the optimal backend, calls the API, returns image URL."""

    # ── Routing logic ─────────────────────────────────────────────────────────

    @staticmethod
    def select_backend(task: GenTask) -> GenerationBackend:
        """
        Decision tree for backend selection.
        This is the meta-agent: it optimizes cost/quality/legal tradeoffs.
        Override via task.backend_override.
        """
        if task.backend_override:
            return task.backend_override

        # Priority 1: Brand typography LoRA (needs ComfyUI custom fine-tune)
        if task.needs_brand_typography:
            return GenerationBackend.COMFYUI_LORA

        # Priority 2: Licensing safety (Firefly is Adobe Stock trained)
        if task.requires_licensing_safety:
            return GenerationBackend.FIREFLY

        # Priority 3: Budget tier
        if task.budget_tier == "draft":
            return GenerationBackend.SDXL_TURBO

        # Default: best quality unrestricted
        return GenerationBackend.FLUX_PRO

    # ── Main generation entry point ───────────────────────────────────────────

    async def generate(self, task: GenTask) -> str:
        """
        Route and execute image generation.
        Returns the URL/path to the generated image.
        """
        backend = self.select_backend(task)
        platform_spec = PLATFORM_SPECS.get(task.platform.value, {"width": 1024, "height": 1024})

        # Build enriched prompt from layout spec
        enriched_prompt = self._build_prompt(task, platform_spec)

        match backend:
            case GenerationBackend.FLUX_PRO:
                return await self._generate_flux(enriched_prompt, platform_spec, model="flux-pro")
            case GenerationBackend.FLUX_SCHNELL | GenerationBackend.SDXL_TURBO:
                return await self._generate_flux(enriched_prompt, platform_spec, model="flux-schnell")
            case GenerationBackend.FIREFLY:
                return await self._generate_firefly(enriched_prompt, platform_spec)
            case GenerationBackend.COMFYUI_LORA:
                return await self._generate_comfyui(enriched_prompt, platform_spec, task)
            case _:
                return await self._generate_flux(enriched_prompt, platform_spec, model="flux-dev")

    # ── Prompt building ───────────────────────────────────────────────────────

    @staticmethod
    def _build_prompt(task: GenTask, platform_spec: dict[str, Any]) -> str:
        """
        Constructs a detailed generation prompt from the structured GenTask.
        Merges the creative prompt with layout constraints.
        """
        spec = task.layout_spec
        palette = spec.color_palette if spec else None

        parts = [task.prompt]

        if spec:
            parts.append(
                f"Layout: {spec.background_style} background. "
                f"Product hero at {spec.product_area_pct * 100:.0f}% canvas. "
                f"Headline {spec.headline_position}. CTA {spec.cta_position}. "
                f"Logo {spec.logo_position}."
            )

        if palette:
            parts.append(
                f"Color palette: primary {palette.primary}, "
                f"secondary {palette.secondary}, background {palette.background}."
            )

        parts.append(
            f"Aspect ratio {platform_spec['aspect']}, "
            f"{platform_spec['width']}x{platform_spec['height']}px. "
            "Professional advertising photography. 8k resolution. "
            "No watermarks. Clean composition."
        )

        return " ".join(parts)

    # ── Backend implementations ───────────────────────────────────────────────

    async def _generate_flux(
        self, prompt: str, platform_spec: dict[str, Any], model: str = "flux-pro"
    ) -> str:
        """
        Generate via Flux on Replicate (or fal.ai).
        Falls back to a placeholder URL if no token is configured.
        """
        if not _settings.replicate_api_token:
            return self._placeholder_url(prompt, platform_spec)

        import replicate  # noqa: PLC0415

        input_data = {
            "prompt": prompt,
            "width": platform_spec["width"],
            "height": platform_spec["height"],
            "num_inference_steps": 28 if model == "flux-pro" else 4,
            "guidance": 3.5,
            "output_format": "webp",
            "output_quality": 90,
        }

        model_id = (
            "black-forest-labs/flux-pro"
            if model == "flux-pro"
            else "black-forest-labs/flux-schnell"
        )

        output = await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: replicate.run(model_id, input=input_data),
        )

        if isinstance(output, list):
            return str(output[0])
        return str(output)

    async def _generate_firefly(
        self, prompt: str, platform_spec: dict[str, Any]
    ) -> str:
        """
        Generate via Adobe Firefly API (licensing-safe, trained on Adobe Stock).
        """
        if not _settings.firefly_client_id:
            return self._placeholder_url(prompt, platform_spec)

        # Get access token
        token = await self._get_firefly_token()

        async with httpx.AsyncClient(timeout=60) as client:
            response = await client.post(
                "https://firefly-api.adobe.io/v2/images/generate",
                headers={
                    "Authorization": f"Bearer {token}",
                    "x-api-key": _settings.firefly_client_id,
                    "Content-Type": "application/json",
                },
                json={
                    "numVariations": 1,
                    "prompt": prompt,
                    "size": {
                        "width": min(platform_spec["width"], 2048),
                        "height": min(platform_spec["height"], 2048),
                    },
                    "contentClass": "photo",
                },
            )
            response.raise_for_status()
            data = response.json()
            return data["outputs"][0]["image"]["url"]

    async def _get_firefly_token(self) -> str:
        """Exchange Firefly client credentials for bearer token."""
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                "https://ims-na1.adobelogin.com/ims/token/v3",
                data={
                    "grant_type": "client_credentials",
                    "client_id": _settings.firefly_client_id,
                    "client_secret": _settings.firefly_client_secret,
                    "scope": "openid,AdobeID,firefly_api",
                },
            )
            resp.raise_for_status()
            return resp.json()["access_token"]

    async def _generate_comfyui(
        self, prompt: str, platform_spec: dict[str, Any], task: GenTask
    ) -> str:
        """
        Queue a ComfyUI workflow for brand-typography LoRA generation.
        Returns the output image URL from the ComfyUI API.
        """
        if not _settings.comfyui_url:
            return self._placeholder_url(prompt, platform_spec)

        # Basic ComfyUI API workflow (simplified — in prod, load from .json template)
        workflow = {
            "prompt": {
                "3": {
                    "class_type": "KSampler",
                    "inputs": {
                        "seed": hash(task.concept_id) % (2**31),
                        "steps": 20,
                        "cfg": 7.0,
                        "sampler_name": "euler",
                        "scheduler": "normal",
                        "denoise": 1.0,
                        "model": ["4", 0],
                        "positive": ["6", 0],
                        "negative": ["7", 0],
                        "latent_image": ["5", 0],
                    },
                },
                # (full workflow definition would be here in production)
            }
        }

        async with httpx.AsyncClient(timeout=120) as client:
            resp = await client.post(
                f"{_settings.comfyui_url}/prompt",
                json=workflow,
            )
            resp.raise_for_status()
            prompt_id = resp.json()["prompt_id"]

            # Poll for completion
            for _ in range(60):
                await asyncio.sleep(2)
                status_resp = await client.get(f"{_settings.comfyui_url}/history/{prompt_id}")
                history = status_resp.json()
                if prompt_id in history:
                    outputs = history[prompt_id]["outputs"]
                    for node_output in outputs.values():
                        if "images" in node_output:
                            img = node_output["images"][0]
                            return f"{_settings.comfyui_url}/view?filename={img['filename']}&type=output"

        return self._placeholder_url(prompt, platform_spec)

    # ── Utility ───────────────────────────────────────────────────────────────

    @staticmethod
    def _placeholder_url(prompt: str, platform_spec: dict[str, Any]) -> str:
        """
        Returns a deterministic placeholder image URL for dev/demo.
        Uses picsum with a seed derived from the prompt hash.
        """
        seed = int(hashlib.md5(prompt.encode()).hexdigest()[:8], 16) % 1000
        w = min(platform_spec["width"], 1024)
        h = min(platform_spec["height"], 1024)
        return f"https://picsum.photos/seed/{seed}/{w}/{h}"


# ── Singleton ──────────────────────────────────────────────────────────────────

_router: GenerationRouter | None = None


def get_generation_router() -> GenerationRouter:
    global _router
    if _router is None:
        _router = GenerationRouter()
    return _router
