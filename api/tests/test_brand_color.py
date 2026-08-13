"""Brand-colour extraction from a logo, and the per-template action-colour key it overrides.

A vivid logo yields its dominant colour; a black/white/grey logo yields None so the template keeps its DA.
"""

from PIL import Image

from services.brand_color_service import BrandColorService
from services.templates import registry


def _solid(rgba: tuple[int, int, int, int]) -> Image.Image:
    return Image.new("RGBA", (80, 80), rgba)


def test_vivid_logo_yields_its_colour() -> None:
    result = BrandColorService._dominant_vivid_hex(_solid((225, 29, 46, 255)))  # a vivid red
    assert result is not None
    red, green, blue = int(result[1:3], 16), int(result[3:5], 16), int(result[5:7], 16)
    assert red > green and red > blue


def test_near_black_logo_yields_none() -> None:
    assert BrandColorService._dominant_vivid_hex(_solid((25, 25, 25, 255))) is None


def test_near_white_logo_yields_none() -> None:
    assert BrandColorService._dominant_vivid_hex(_solid((245, 245, 245, 255))) is None


def test_grey_logo_yields_none() -> None:
    assert BrandColorService._dominant_vivid_hex(_solid((128, 130, 129, 255))) is None


def test_blank_url_yields_none() -> None:
    assert BrandColorService().extract_brand_color(None) is None
    assert BrandColorService().extract_brand_color("   ") is None


def test_brand_color_key_per_template() -> None:
    # Barber's action colour is the gold accent; the others drive actions from primary.
    assert registry.brand_color_key("barber") == "accent"
    assert registry.brand_color_key("mechanic-pitlane") == "primary"
    assert registry.brand_color_key("food") == "primary"
