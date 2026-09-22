from __future__ import annotations

from .contracts import ContractError


def wan_temporal_groups(length: int) -> tuple[tuple[int, int], ...]:
    if type(length) is not int or length < 1:
        raise ContractError("WAN length must be a positive integer")
    latent_length = ((length - 1) // 4) + 1
    groups = [(0, 1)]
    for index in range(1, latent_length):
        start = 4 * index - 3
        end = min(length, 4 * index + 1)
        groups.append((start, end))
    return tuple(groups)


class ConceptGhostP10WanMaskedConditioning:
    """WAN I2V conditioning from P10 geometry control frames + white-hole mask.

    This is the ConceptGhost adaptation of the masked-video conditioning path:
    the full control video is VAE encoded, while the binary hole mask is packed
    into WAN's latent temporal layout. White mask pixels mean "generate here".
    """

    MASK_POLICY = "WHITE_IS_HOLE_GENERATE_BLACK_IS_KNOWN"

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "positive": ("CONDITIONING",),
                "negative": ("CONDITIONING",),
                "vae": ("VAE",),
                "control_video": ("IMAGE",),
                "hole_mask": ("MASK",),
                "width": ("INT", {"default": 832, "min": 16, "max": 4096, "step": 16}),
                "height": ("INT", {"default": 480, "min": 16, "max": 4096, "step": 16}),
                "length": ("INT", {"default": 33, "min": 1, "max": 257, "step": 4}),
            },
            "optional": {
                "clip_vision_output": ("CLIP_VISION_OUTPUT",),
                "hole_fill": (["black", "gray"], {"default": "black"}),
            },
        }

    RETURN_TYPES = ("CONDITIONING", "CONDITIONING", "LATENT")
    RETURN_NAMES = ("positive", "negative", "latent")
    FUNCTION = "encode"
    CATEGORY = "ConceptGhost/P10 Refined"

    def encode(
        self,
        positive,
        negative,
        vae,
        control_video,
        hole_mask,
        width,
        height,
        length,
        clip_vision_output=None,
        hole_fill="black",
    ):
        if width % 16 or height % 16:
            raise ContractError("WAN width/height must be multiples of 16")
        groups = wan_temporal_groups(int(length))

        try:
            import torch
            import comfy.utils
            import comfy.model_management
            import node_helpers
        except ImportError as error:
            raise ContractError(
                "WAN conditioning requires the active ComfyUI runtime"
            ) from error

        device = comfy.model_management.intermediate_device()
        fill_value = 0.0 if hole_fill == "black" else 0.5

        latent_length = len(groups)
        latent = torch.zeros(
            [1, 16, latent_length, height // 8, width // 8],
            device=device,
        )

        video = control_video[:length].movedim(-1, 1)
        video = comfy.utils.common_upscale(
            video,
            width,
            height,
            "bilinear",
            "center",
        ).movedim(1, -1)

        image = torch.ones(
            (length, height, width, 3),
            device=video.device,
            dtype=video.dtype,
        ) * fill_value
        image[: video.shape[0]] = video[..., :3]

        mask = hole_mask[:length]
        if mask.ndim == 4:
            mask = mask[..., 0]
        mask = comfy.utils.common_upscale(
            mask.unsqueeze(1).float(),
            width,
            height,
            "bilinear",
            "center",
        ).squeeze(1)
        mask = (mask > 0.5).float()

        hole = torch.zeros(
            (length, height, width),
            device=mask.device,
            dtype=torch.float32,
        )
        hole[: mask.shape[0]] = mask
        image[hole > 0.5] = fill_value

        concat_latent_image = vae.encode(image[:, :, :, :3])
        latent_height, latent_width = concat_latent_image.shape[-2:]

        spatial_hole = torch.nn.functional.interpolate(
            hole.unsqueeze(1),
            size=(latent_height, latent_width),
            mode="area",
        ).squeeze(1)

        packed = []
        for start, end in groups:
            packed.append(
                spatial_hole[start:end].mean(dim=0, keepdim=True)
            )
        packed_hole = torch.cat(packed, dim=0)
        concat_mask = (
            (packed_hole > 0.5)
            .float()
            .view(1, 1, latent_length, latent_height, latent_width)
        )

        values = {
            "concat_latent_image": concat_latent_image,
            "concat_mask": concat_mask,
        }
        positive = node_helpers.conditioning_set_values(positive, values)
        negative = node_helpers.conditioning_set_values(negative, values)

        if clip_vision_output is not None:
            positive = node_helpers.conditioning_set_values(
                positive,
                {"clip_vision_output": clip_vision_output},
            )
            negative = node_helpers.conditioning_set_values(
                negative,
                {"clip_vision_output": clip_vision_output},
            )

        return positive, negative, {"samples": latent}
