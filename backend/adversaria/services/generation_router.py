"""
adversaria/services/generation_router.py — Multi-backend image generation router.

Optimizes cost / quality / legal-safety tradeoffs at runtime.
Never hardcodes a single backend — every generation task is routed based on
task properties: brand typography needs, budget tier, licensing requirements.

Backends supported:
  - Flux Pro / Schnell  (Replicate)
  - Flux Pro            (fal.ai — ultra-fast inference)
  - SDXL-Turbo          (ComfyUI self-hosted, draft tier)
  - Flux + LoRA         (ComfyUI self-hosted, brand-typography fine-tune)
  - Flux Inpainting     (ComfyUI self-hosted, localized regeneration)
  - Adobe Firefly       (licensing-safe, Adobe Stock trained)
"""
from __future__ import annotations

import asyncio
import hashlib
import json
import os
from pathlib import Path
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

# ComfyUI caps dimensions to avoid VRAM OOM
COMFYUI_MAX_DIM = 1280


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

        # Priority 3: Budget tier — draft previews via fal.ai (fastest) or SDXL
        if task.budget_tier == "draft":
            # If fal.ai key present, use it (much faster than Replicate for drafts)
            if _settings.fal_key:
                return GenerationBackend.FLUX_SCHNELL
            return GenerationBackend.SDXL_TURBO

        # Default: best quality via fal.ai Flux Pro (lower latency than Replicate)
        if _settings.fal_key:
            return GenerationBackend.FLUX_PRO

        # Fallback: Replicate
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
                # Prefer fal.ai for Flux Pro (lower latency)
                if _settings.fal_key:
                    return await self._generate_fal(
                        enriched_prompt, platform_spec, model="fal-ai/flux-pro"
                    )
                return await self._generate_replicate(enriched_prompt, platform_spec, model="flux-pro")

            case GenerationBackend.FLUX_SCHNELL:
                # Fast draft — fal.ai Flux Schnell is ~3x faster than Replicate
                if _settings.fal_key:
                    return await self._generate_fal(
                        enriched_prompt, platform_spec, model="fal-ai/flux/schnell"
                    )
                return await self._generate_replicate(enriched_prompt, platform_spec, model="flux-schnell")

            case GenerationBackend.SDXL_TURBO:
                return await self._generate_comfyui(
                    enriched_prompt, platform_spec, task, workflow="sdxl_turbo_draft"
                )

            case GenerationBackend.FIREFLY:
                return await self._generate_firefly(enriched_prompt, platform_spec)

            case GenerationBackend.COMFYUI_LORA:
                return await self._generate_comfyui(
                    enriched_prompt, platform_spec, task, workflow="flux_lora_standard"
                )

            case _:
                # Ultimate fallback — placeholder if no keys configured
                return self._placeholder_url(enriched_prompt, platform_spec)

    async def generate_inpaint(
        self,
        task: GenTask,
        image_path: str,
        mask_path: str,
    ) -> str:
        """
        Localized regeneration via inpainting — preserves the rest of the composition.
        This is the UX differentiator: human nudges one element, not a full reroll.
        """
        platform_spec = PLATFORM_SPECS.get(task.platform.value, {"width": 1024, "height": 1024})
        enriched_prompt = self._build_prompt(task, platform_spec)
        return await self._generate_comfyui(
            enriched_prompt,
            platform_spec,
            task,
            workflow="flux_inpaint",
            extra_slots={"__IMAGE_PATH__": image_path, "__MASK_PATH__": mask_path},
        )

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

    # ── Backend: fal.ai (Flux Pro / Schnell — ultra-fast) ────────────────────

    async def _generate_fal(
        self, prompt: str, platform_spec: dict[str, Any], model: str = "fal-ai/flux-pro"
    ) -> str:
        """
        Generate via fal.ai — significantly lower latency than Replicate for Flux.
        Supports both Flux Pro (quality) and Flux Schnell (speed).
        """
        if not _settings.fal_key:
            return self._placeholder_url(prompt, platform_spec)

        import fal_client  # noqa: PLC0415

        # fal_client reads FAL_KEY from env automatically, but we set it explicitly
        os.environ["FAL_KEY"] = _settings.fal_key

        w = min(platform_spec["width"], 1440)
        h = min(platform_spec["height"], 1440)

        # fal.ai uses image_size as preset or {width, height}
        arguments: dict[str, Any] = {
            "prompt": prompt,
            "image_size": {"width": w, "height": h},
            "num_inference_steps": 28 if "pro" in model else 4,
            "guidance_scale": 3.5,
            "num_images": 1,
            "output_format": "webp",
            "enable_safety_checker": False,
        }

        result = await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: fal_client.run(model, arguments=arguments),
        )

        images = result.get("images", [])
        if images:
            return images[0].get("url", self._placeholder_url(prompt, platform_spec))
        return self._placeholder_url(prompt, platform_spec)

    # ── Backend: Replicate (Flux Pro / Schnell fallback) ─────────────────────

    async def _generate_replicate(
        self, prompt: str, platform_spec: dict[str, Any], model: str = "flux-pro"
    ) -> str:
        """
        Generate via Flux on Replicate.
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

    # ── Backend: Adobe Firefly ─────────────────────────────────────────────────

    async def _generate_firefly(
        self, prompt: str, platform_spec: dict[str, Any]
    ) -> str:
        """
        Generate via Adobe Firefly API (licensing-safe, trained on Adobe Stock).
        """
        if not _settings.firefly_client_id:
            return self._placeholder_url(prompt, platform_spec)

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

    # ── Backend: ComfyUI (self-hosted — LoRA, inpainting, SDXL-Turbo) ─────────

    async def _generate_comfyui(
        self,
        prompt: str,
        platform_spec: dict[str, Any],
        task: GenTask,
        workflow: str = "flux_lora_standard",
        extra_slots: dict[str, str] | None = None,
    ) -> str:
        """
        Queue a ComfyUI workflow for generation.

        Loads the workflow template from disk (comfyui_workflows/<name>.json),
        substitutes slot values, then polls for completion via the ComfyUI
        /history API.

        Falls back to placeholder if ComfyUI is unreachable.
        """
        if not _settings.comfyui_url:
            return self._placeholder_url(prompt, platform_spec)

        # ── Load workflow template ────────────────────────────────────────────
        workflow_path = (
            Path(_settings.comfyui_workflow_dir) / f"{workflow}.json"
        )
        if not workflow_path.exists():
            # Fallback to package-relative path
            workflow_path = Path(__file__).parent.parent.parent / "comfyui_workflows" / f"{workflow}.json"

        if not workflow_path.exists():
            return self._placeholder_url(prompt, platform_spec)

        with workflow_path.open() as f:
            workflow_def = json.load(f)

        # Remove metadata comment keys (not valid ComfyUI fields)
        workflow_def.get("prompt", workflow_def).pop("_comment", None)

        # ── Slot substitution ─────────────────────────────────────────────────
        seed = abs(hash(task.concept_id)) % (2**31)
        w = min(platform_spec["width"], COMFYUI_MAX_DIM)
        h = min(platform_spec["height"], COMFYUI_MAX_DIM)

        # Make it JSON string for simple string replace across the whole payload
        wf_str = json.dumps(workflow_def)
        replacements = {
            "__PROMPT__": prompt,
            "__SEED__": str(seed),
            "__WIDTH__": str(w),
            "__HEIGHT__": str(h),
            "__LORA_NAME__": f"brand_{task.brand_id}.safetensors",
            **(extra_slots or {}),
        }
        for slot, value in replacements.items():
            wf_str = wf_str.replace(json.dumps(slot), json.dumps(value))
            # Also replace unquoted numeric slots (seed, width, height)
            wf_str = wf_str.replace(f'"{slot}"', value)

        final_workflow = json.loads(wf_str)

        # ── Queue prompt ──────────────────────────────────────────────────────
        comfyui_payload = {
            "prompt": final_workflow.get("prompt", final_workflow),
            "client_id": f"adversaria_{task.concept_id[:8]}",
        }

        try:
            async with httpx.AsyncClient(timeout=180) as client:
                resp = await client.post(
                    f"{_settings.comfyui_url}/prompt",
                    json=comfyui_payload,
                )
                resp.raise_for_status()
                prompt_id = resp.json()["prompt_id"]

                # ── Poll for completion (max 120s) ────────────────────────────
                for _ in range(60):
                    await asyncio.sleep(2)
                    status_resp = await client.get(
                        f"{_settings.comfyui_url}/history/{prompt_id}"
                    )
                    history = status_resp.json()
                    if prompt_id in history:
                        outputs = history[prompt_id].get("outputs", {})
                        for node_output in outputs.values():
                            if "images" in node_output:
                                img = node_output["images"][0]
                                img_url = (
                                    f"{_settings.comfyui_url}/view"
                                    f"?filename={img['filename']}"
                                    f"&subfolder={img.get('subfolder', '')}"
                                    f"&type={img.get('type', 'output')}"
                                )
                                return img_url
        except (httpx.ConnectError, httpx.TimeoutException):
            # ComfyUI not running — return placeholder for dev
            pass

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
