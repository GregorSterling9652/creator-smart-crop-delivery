import pytest

from crop_delivery.crop_service import plan_aspects


def test_creator_aspects_keep_delivery_order() -> None:
    assert plan_aspects(["16:9", "1:1", "4:5"]) == ["16:9", "1:1", "4:5"]


def test_duplicate_delivery_is_rejected_before_processing() -> None:
    with pytest.raises(ValueError, match="Duplicate aspect: 1:1"):
        plan_aspects(["1:1", "1:1"])
