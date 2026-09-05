"""serial reader tests"""

import pytest

from custom_components.linkytic.serial_reader import (
    HistoricDataset,
    InvalidChecksumException,
    LinkQualityIndicator,
    LinkyTICReader,
    MalformatedDatasetException,
    StandardDataset,
)


def test_standard_dataset_decode():
    """Test the decoding of a standard dataset."""

    data = b"EAST\t003519702\t*"
    dataset = StandardDataset.from_raw(data)

    assert dataset.tag == "EAST"
    assert dataset.value == "003519702"


def test_standard_dataset_invalid_checksum():
    """Test that an invalid checksum raises an exception."""

    data = b"EAST\t0035197E2\t*"
    with pytest.raises(InvalidChecksumException):
        StandardDataset.from_raw(data)


def test_standard_dataset_malformed():
    """Test that a malformed dataset raises an exception."""

    data = b"EAST003519702*"
    with pytest.raises(MalformatedDatasetException):
        StandardDataset.from_raw(data)


def test_historic_dataset_decode():
    """Test the decoding of a historic dataset."""

    data = b"BASE 123456789 8"
    dataset = HistoricDataset.from_raw(data)

    assert dataset.tag == "BASE"
    assert dataset.value == "123456789"


def test_historic_dataset_invalid_checksum():
    """Test that an invalid checksum raises an exception."""

    data = b"BASE 123456789 9"
    with pytest.raises(InvalidChecksumException):
        HistoricDataset.from_raw(data)


def test_historic_dataset_malformed():
    """Test that a malformed dataset raises an exception."""

    data = b"BASE 123456789x8"
    with pytest.raises(MalformatedDatasetException):
        HistoricDataset.from_raw(data)


def test_link_quality_indicator():
    """Test the link quality indicator filter."""

    lqi = LinkQualityIndicator()

    for _ in range(100):
        lqi.update(False)

    assert lqi.get_value() == 0