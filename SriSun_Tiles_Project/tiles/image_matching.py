from io import BytesIO
from functools import lru_cache
import math

import numpy as np
from PIL import Image, ImageOps

from .models import Tile


SAMPLE_MODEL_IDS = ('T001', 'T002', 'T003', 'T004', 'T005')
HASH_SIZE = 8
MINIMUM_SIMILARITY = 0.82
MINIMUM_WINNER_MARGIN = 0.08
MINIMUM_STRUCTURE_SIMILARITY = 0.25


def _dct_basis(size):
    positions = np.arange(size, dtype=np.float32)
    basis = np.cos((np.pi / size) * (positions[:, None] + 0.5) * positions[None, :])
    basis[0] *= 1 / math.sqrt(size)
    basis[1:] *= math.sqrt(2 / size)
    return basis


DCT_BASIS = _dct_basis(HASH_SIZE * 4)


def _image_features(image_data, reject_low_detail=True):
    try:
        with Image.open(BytesIO(image_data)) as source:
            if source.width * source.height > 25_000_000:
                return None
            image = ImageOps.exif_transpose(source).convert('RGB')
    except (OSError, ValueError):
        return None

    grayscale = image.convert('L')
    if reject_low_detail and np.asarray(grayscale, dtype=np.float32).std() < 0.05:
        return None

    hashes = []
    for angle in range(0, 360, 30):
        rotated = image.rotate(angle, resample=Image.Resampling.BICUBIC, expand=True)
        for crop_ratio in (1.0, 0.82):
            width = max(1, int(rotated.width * crop_ratio))
            height = max(1, int(rotated.height * crop_ratio))
            left = (rotated.width - width) // 2
            top = (rotated.height - height) // 2
            crop = rotated.crop((left, top, left + width, top + height))
            pixels = np.asarray(
                ImageOps.fit(crop.convert('L'), (HASH_SIZE * 4, HASH_SIZE * 4), method=Image.Resampling.LANCZOS),
                dtype=np.float32,
            )
            coefficients = DCT_BASIS @ pixels @ DCT_BASIS.T
            low_frequencies = coefficients[:HASH_SIZE, :HASH_SIZE]
            threshold = np.median(low_frequencies[1:, 1:])
            hashes.append((low_frequencies > threshold).reshape(-1)[1:])

    rgb = np.asarray(image.resize((96, 96)), dtype=np.float32) / 255
    maximum = rgb.max(axis=2)
    minimum = rgb.min(axis=2)
    saturation = (maximum - minimum) / np.maximum(maximum, 1e-4)
    chromaticity = rgb / np.maximum(rgb.sum(axis=2, keepdims=True), 1e-4)
    color_histogram = np.concatenate([
        np.histogram(chromaticity[:, :, channel], bins=12, range=(0, 1))[0] / chromaticity[:, :, channel].size
        for channel in range(3)
    ] + [np.histogram(saturation, bins=12, range=(0, 1))[0] / saturation.size])

    brightness = float(np.asarray(grayscale, dtype=np.float32).mean())
    structure_image = np.asarray(
        ImageOps.fit(grayscale, (96, 96), method=Image.Resampling.LANCZOS),
        dtype=np.float32,
    )
    horizontal = np.corrcoef(structure_image[:, :-1].ravel(), structure_image[:, 1:].ravel())[0, 1]
    vertical = np.corrcoef(structure_image[:-1, :].ravel(), structure_image[1:, :].ravel())[0, 1]
    structure = tuple(sorted((float(horizontal), float(vertical))))

    return np.asarray(hashes, dtype=np.bool_), color_histogram, brightness, structure


@lru_cache(maxsize=5)
def _reference_features(image_data):
    return _image_features(image_data, reject_low_detail=False)


def _similarity(first_features, second_features):
    first_hashes, first_colors, first_brightness, _ = first_features
    second_hashes, second_colors, second_brightness, _ = second_features
    distances = np.count_nonzero(
        first_hashes[:, None, :] != second_hashes[None, :, :],
        axis=2,
    )
    hash_similarity = 1 - int(distances.min()) / first_hashes.shape[-1]
    color_similarity = np.minimum(first_colors, second_colors).sum() / 4
    brightness_similarity = math.exp(
        -abs(math.log((first_brightness + 1) / (second_brightness + 1))) / 0.8
    )
    return 0.55 * hash_similarity + 0.2 * color_similarity + 0.25 * brightness_similarity


def _structure_similarity(first_features, second_features):
    first_structure = first_features[3]
    second_structure = second_features[3]
    difference = sum(abs(first - second) for first, second in zip(first_structure, second_structure))
    return math.exp(-difference / 0.18)


def find_exact_sample_match(image_data):
    query_features = _image_features(image_data)
    if query_features is None:
        return None

    candidates = list(
        Tile.objects.filter(model_id__in=SAMPLE_MODEL_IDS)
        .exclude(image='')
        .order_by('model_id')
    )
    if len(candidates) != len(SAMPLE_MODEL_IDS):
        return None

    ranked = []
    for tile in candidates:
        try:
            with tile.image.open('rb') as reference_file:
                reference_features = _reference_features(reference_file.read())
        except (OSError, ValueError):
            return None

        if reference_features is None:
            return None
        ranked.append((
            _similarity(query_features, reference_features),
            _structure_similarity(query_features, reference_features),
            tile,
        ))

    ranked.sort(key=lambda result: result[0], reverse=True)
    best_score, best_structure, best_tile = ranked[0]
    runner_up_score = ranked[1][0]
    if (
        best_score < MINIMUM_SIMILARITY
        or best_score - runner_up_score < MINIMUM_WINNER_MARGIN
        or best_structure < MINIMUM_STRUCTURE_SIMILARITY
    ):
        return None

    return best_tile