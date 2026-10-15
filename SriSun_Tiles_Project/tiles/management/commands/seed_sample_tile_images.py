from io import BytesIO
import hashlib
import math
import random
import re

from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand, CommandError
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageOps

from tiles.models import Tile


SAMPLE_STYLES = {
    'T001': {'dark': (218, 216, 209), 'light': (249, 248, 244), 'accent': (150, 148, 141), 'pattern': 'marble'},
    'T002': {'dark': (183, 166, 139), 'light': (218, 202, 177), 'accent': (160, 144, 119), 'pattern': 'matte'},
    'T003': {'dark': (25, 27, 30), 'light': (57, 59, 62), 'accent': (177, 179, 181), 'pattern': 'marble'},
    'T004': {'dark': (105, 108, 106), 'light': (150, 151, 146), 'accent': (74, 77, 76), 'pattern': 'wood'},
    'T005': {'dark': (123, 86, 61), 'light': (172, 133, 101), 'accent': (217, 185, 151), 'pattern': 'marble'},
}

COLOR_PALETTES = {
    'beige': ((151, 130, 99), (232, 217, 190), (190, 165, 128)),
    'black': ((15, 17, 19), (70, 72, 74), (154, 155, 155)),
    'blue': ((37, 72, 111), (156, 192, 218), (89, 127, 163)),
    'brown': ((76, 48, 33), (183, 139, 99), (139, 91, 58)),
    'green': ((49, 75, 55), (176, 192, 159), (112, 137, 91)),
    'grey': ((74, 78, 79), (194, 195, 191), (129, 133, 132)),
    'ivory': ((178, 162, 130), (249, 242, 221), (216, 201, 172)),
    'red': ((94, 34, 31), (204, 123, 97), (154, 70, 54)),
    'white': ((188, 188, 183), (253, 252, 247), (221, 219, 210)),
}

MODEL_IDS = tuple(f'T{number:03d}' for number in range(1, 101))
IMAGE_SIZE = (960, 720)


def build_sample_image(model_id, style):
    """Keep the original sample builder available to existing matcher tests."""
    width, height = IMAGE_SIZE
    noise = Image.effect_noise((width, height), 18).convert('L')
    noise = noise.point(lambda value: 96 + int(value * 0.2))
    surface = ImageOps.colorize(noise, black=style['dark'], white=style['light']).convert('RGB')
    surface = surface.filter(ImageFilter.GaussianBlur(1.2))
    overlay = Image.new('RGBA', (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    generator = random.Random(model_id)
    if style['pattern'] == 'marble':
        for _ in range(10):
            start_y = generator.randint(-height // 3, height + height // 3)
            amplitude = generator.randint(10, 36)
            period = generator.randint(130, 300)
            points = [
                (x, start_y + math.sin((x / period) + generator.random()) * amplitude)
                for x in range(-40, width + 41, 40)
            ]
            draw.line(points, fill=(*style['accent'], generator.randint(14, 34)), width=generator.choice((1, 2, 3)))
    elif style['pattern'] == 'wood':
        for _ in range(95):
            y = generator.randrange(height)
            draw.line(
                [(0, y), (width, y + generator.randint(-5, 5))],
                fill=(*style['accent'], generator.randint(7, 22)),
                width=generator.choice((1, 1, 2)),
            )
    else:
        for _ in range(700):
            draw.point((generator.randrange(width), generator.randrange(height)), fill=(*style['accent'], generator.randint(4, 12)))
    if model_id == 'T003':
        draw.polygon([(0, 0), (width // 3, 0), (0, height // 5)], fill=(255, 255, 255, 9))
    image = Image.alpha_composite(surface.convert('RGBA'), overlay).convert('RGB')
    output = BytesIO()
    image.save(output, format='JPEG', quality=88, optimize=True)
    return output.getvalue()


def _tile_style(tile):
    text = ' '.join((tile.model_id, tile.name, tile.category, tile.size, tile.color, tile.finish, tile.description)).casefold()
    palette = next((key for key in COLOR_PALETTES if key in tile.color.casefold()), 'grey')
    if any(word in text for word in ('granite', 'quartzite')):
        material = 'granite'
    elif any(word in text for word in ('wood', 'timber', 'oak', 'walnut')):
        material = 'wood'
    elif any(word in text for word in ('cement', 'concrete')):
        material = 'cement'
    elif any(word in text for word in ('geometric', 'pattern', 'mosaic', 'decorative', 'decor')):
        material = 'pattern'
    elif 'marble' in text:
        material = 'marble'
    elif any(word in text for word in ('stone', 'slate', 'travertine')):
        material = 'stone'
    elif tile.category.casefold() == 'porcelain' and tile.color.casefold() == 'black' and tile.finish.casefold() == 'polished':
        material = 'marble'
    elif tile.category.casefold() in {'bathroom', 'floor', 'porcelain', 'vitrified'}:
        material = 'stone'
    else:
        material = 'ceramic'
    dark, light, accent = COLOR_PALETTES[palette]
    return {
        'dark': dark,
        'light': light,
        'accent': accent,
        'material': material,
        'finish': tile.finish.casefold(),
        'size': tile.size,
        'variant': int(tile.model_id[1:]) % 13,
    }


def _noise_field(width, height, cell_size, generator):
    small_width = max(2, math.ceil(width / cell_size))
    small_height = max(2, math.ceil(height / cell_size))
    samples = generator.random((small_height, small_width), dtype=np.float32)
    small_image = Image.fromarray(np.uint8(samples * 255))
    return np.asarray(small_image.resize((width, height), Image.Resampling.BICUBIC), dtype=np.float32) / 255


def _draw_marble(draw, generator, width, height, accent, variant):
    mode = variant % 4
    for _ in range(generator.randint(10, 15) + mode * 2):
        start_x = generator.randint(-width // 4, width)
        start_y = generator.randint(-height // 4, height + height // 4)
        drift = generator.uniform(-0.8, 0.8)
        period = generator.randint(110, 320)
        phase = generator.random() * math.tau
        if mode == 1:
            points = [
                (x, int(start_y + drift * (x - start_x) + math.sin((x / period) + phase) * generator.randint(8, 25)))
                for x in range(-30, width + 31, 18)
            ]
        elif mode == 2:
            points = []
            x = start_x
            for y in range(-30, height + 31, 18):
                x += generator.randint(-15, 15)
                x += int(math.sin((y / period) + phase) * 10)
                points.append((x, y))
        else:
            points = []
            for y in range(-30, height + 31, 18):
                x = start_x + drift * (y - start_y) + math.sin((y / period) + phase) * generator.randint(8, 26)
                points.append((int(x + generator.uniform(-8, 8)), y))
        vein_width = generator.choice((1, 2, 3, 4))
        alpha = generator.randint(72, 150)
        draw.line(points, fill=(*accent, alpha), width=vein_width + 3, joint='curve')
        draw.line(points, fill=(247, 243, 232, min(190, alpha + 28)), width=vein_width, joint='curve')
        if generator.random() < 0.72:
            branch = points[generator.randint(3, len(points) - 4)]
            draw.line(
                [branch, (branch[0] + generator.randint(20, 55), branch[1] + generator.randint(20, 45)),
                 (branch[0] + generator.randint(45, 100), branch[1] + generator.randint(50, 105))],
                fill=(*accent, alpha),
                width=1,
                joint='curve',
            )


def _draw_wood(draw, generator, width, height, accent, dark, detail_scale, variant):
    grain_angle = (variant % 5 - 2) * 0.045
    for _ in range(int((105 + variant % 6 * 12) * detail_scale)):
        y = generator.randrange(height)
        amplitude = generator.randint(2, 12)
        period = generator.randint(90, 260)
        phase = generator.random() * math.tau
        points = [
            (x, int(y + (x - width / 2) * grain_angle + math.sin((x / period) + phase) * amplitude + generator.uniform(-2, 2)))
            for x in range(-20, width + 21, 20)
        ]
        draw.line(points, fill=(*accent, generator.randint(45, 120)), width=generator.choice((1, 2, 3)))
    for _ in range(generator.randint(1 + variant % 3, 4 + variant % 4)):
        knot_x, knot_y = generator.randint(40, width - 40), generator.randint(30, height - 30)
        radius = generator.randint(9, 22)
        draw.ellipse((knot_x - radius * 2, knot_y - radius, knot_x + radius * 2, knot_y + radius), outline=(*accent, 135), width=2)
        draw.ellipse((knot_x - radius, knot_y - radius // 2, knot_x + radius, knot_y + radius // 2), outline=(*dark, 160), width=2)


def _draw_stone(draw, generator, width, height, accent, dark, detail_scale):
    for _ in range(int(16 * detail_scale)):
        x, y = generator.randint(-width // 4, width), generator.randint(0, height)
        reach = generator.randint(width // 8, width // 2)
        points = [
            (x, y),
            (x + reach // 3, y + generator.randint(-24, 24)),
            (x + reach * 2 // 3, y + generator.randint(-38, 38)),
            (x + reach, y + generator.randint(-20, 20)),
        ]
        draw.line(points, fill=(*accent, generator.randint(45, 125)), width=generator.randint(1, 3))
    for _ in range(1600):
        x, y = generator.randrange(width), generator.randrange(height)
        radius = generator.choice((1, 1, 2, 3))
        draw.ellipse((x, y, x + radius, y + radius), fill=(*dark, generator.randint(22, 75)))


def _draw_granite(draw, generator, width, height, style):
    minerals = (style['dark'], style['light'], style['accent'], (238, 232, 218))
    for _ in range(18000):
        x, y = generator.randrange(width), generator.randrange(height)
        radius = generator.choices((1, 2, 3, 4), weights=(54, 30, 12, 4), k=1)[0]
        draw.ellipse((x, y, x + radius, y + radius), fill=(*generator.choice(minerals), generator.randint(100, 210)))


def _draw_cement(draw, generator, width, height, style):
    for _ in range(5500):
        x, y = generator.randrange(width), generator.randrange(height)
        radius = generator.choices((1, 2, 3, 5), weights=(55, 28, 13, 4), k=1)[0]
        draw.ellipse((x, y, x + radius, y + radius), fill=(*style['dark'], generator.randint(24, 82)))
    for _ in range(40):
        y = generator.randint(0, height)
        draw.line([(0, y), (width, y + generator.randint(-16, 16))], fill=(*style['light'], generator.randint(12, 28)), width=generator.choice((1, 2)))


def _draw_ceramic(draw, generator, width, height, style):
    variant = style['variant'] % 6
    accent = style['accent']
    for _ in range(3600 if variant in (0, 3) else 1800):
        x, y = generator.randrange(width), generator.randrange(height)
        radius = generator.choices((1, 2, 3, 4), weights=(58, 26, 12, 4), k=1)[0]
        alpha = generator.randint(32, 100)
        draw.ellipse((x, y, x + radius, y + radius), fill=(*accent, alpha))

    if variant == 0:
        for _ in range(7):
            center_x, center_y = generator.randrange(width), generator.randrange(height)
            radius = generator.randint(24, 65)
            draw.ellipse((center_x - radius, center_y - radius, center_x + radius, center_y + radius), outline=(*style['light'], 80), width=2)
    elif variant == 1:
        for offset in range(-height, width, generator.randint(38, 62)):
            points = [(x, int(x * 0.55 + offset + math.sin(x / 95) * 7)) for x in range(0, width + 1, 24)]
            draw.line(points, fill=(*accent, 70), width=generator.choice((1, 2)))
    elif variant == 2:
        for _ in range(10):
            center_x, center_y = generator.randrange(width), generator.randrange(height)
            radius = generator.randint(18, 52)
            draw.arc(
                (center_x - radius, center_y - radius, center_x + radius, center_y + radius),
                start=generator.randint(0, 160),
                end=generator.randint(200, 360),
                fill=(*style['light'], 100),
                width=2,
            )
    elif variant == 3:
        for _ in range(2200):
            x, y = generator.randrange(width), generator.randrange(height)
            radius = generator.choice((1, 1, 2))
            draw.rectangle((x, y, x + radius, y + radius), fill=(*style['dark'], generator.randint(18, 55)))
    elif variant == 4:
        for _ in range(180):
            start_x, start_y = generator.randrange(width), generator.randrange(height)
            length = generator.randint(22, 115)
            draw.line(
                [(start_x, start_y), (start_x + length, start_y + generator.randint(-14, 14))],
                fill=(*style['light'], generator.randint(32, 82)),
                width=generator.choice((1, 2)),
            )
    else:
        spacing = generator.choice((36, 48, 60))
        for y in range(spacing // 2, height, spacing):
            for x in range(spacing // 2, width, spacing):
                radius = generator.randint(3, 7)
                draw.ellipse((x - radius, y - radius, x + radius, y + radius), outline=(*accent, 92), width=1)


def _draw_pattern(draw, generator, width, height, style):
    cell = generator.choice((72, 90, 108, 120))
    motif = generator.choice(('diamond', 'hexagon', 'rosette'))
    for row, top in enumerate(range(-cell, height + cell, cell)):
        for column, left in enumerate(range(-cell, width + cell, cell)):
            center_x, center_y = left + cell // 2, top + cell // 2
            color = style['accent'] if (row + column) % 2 else style['dark']
            if motif == 'diamond':
                points = [(center_x, top + 7), (left + cell - 7, center_y), (center_x, top + cell - 7), (left + 7, center_y)]
                draw.polygon(points, outline=(*color, 165), width=3)
                draw.ellipse((center_x - 10, center_y - 10, center_x + 10, center_y + 10), fill=(*style['light'], 120))
            elif motif == 'hexagon':
                points = [
                    (left + cell // 4, top + 5), (left + cell * 3 // 4, top + 5),
                    (left + cell - 5, center_y), (left + cell * 3 // 4, top + cell - 5),
                    (left + cell // 4, top + cell - 5), (left + 5, center_y),
                ]
                draw.polygon(points, outline=(*color, 165), width=3)
            else:
                draw.ellipse((left + 8, top + 8, left + cell - 8, top + cell - 8), outline=(*color, 155), width=3)
                draw.ellipse((center_x - cell // 5, center_y - cell // 5, center_x + cell // 5, center_y + cell // 5), outline=(*style['light'], 140), width=2)


def build_tile_image(tile):
    width, height = IMAGE_SIZE
    style = _tile_style(tile)
    fields = (tile.model_id, tile.name, tile.category, tile.size, tile.color, tile.finish, tile.description)
    seed = int.from_bytes(hashlib.sha256('|'.join(fields).encode('utf-8')).digest()[:8], 'big')
    generator = random.Random(seed)
    numpy_generator = np.random.default_rng(seed)
    size_numbers = [int(value) for value in re.findall(r'\d+', tile.size)[:2]]
    area_scale = math.sqrt(size_numbers[0] * size_numbers[1]) if len(size_numbers) == 2 else 600
    detail_scale = min(1.5, max(0.7, area_scale / 600))

    broad = _noise_field(width, height, max(36, int(128 / detail_scale)), numpy_generator)
    medium = _noise_field(width, height, max(10, int(38 / detail_scale)), numpy_generator)
    fine = _noise_field(width, height, max(3, int(10 / detail_scale)), numpy_generator)
    grain = _noise_field(width, height, 2, numpy_generator)
    tone = np.clip(0.5 + (broad - 0.5) * 0.92 + (medium - 0.5) * 0.54 + (fine - 0.5) * 0.30 + (grain - 0.5) * 0.12, 0, 1)
    dark = np.asarray(style['dark'], dtype=np.float32)
    light = np.asarray(style['light'], dtype=np.float32)
    rgb = dark[None, None, :] + tone[:, :, None] * (light - dark)[None, None, :]
    surface = Image.fromarray(np.uint8(np.clip(rgb, 0, 255)))

    overlay = Image.new('RGBA', (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    material = style['material']
    if material == 'marble':
        _draw_marble(draw, generator, width, height, style['accent'], style['variant'])
    elif material == 'wood':
        _draw_wood(draw, generator, width, height, style['accent'], style['dark'], detail_scale, style['variant'])
    elif material == 'stone':
        _draw_stone(draw, generator, width, height, style['accent'], style['dark'], detail_scale)
    elif material == 'granite':
        _draw_granite(draw, generator, width, height, style)
    elif material == 'cement':
        _draw_cement(draw, generator, width, height, style)
    elif material == 'pattern':
        _draw_pattern(draw, generator, width, height, style)
    else:
        _draw_ceramic(draw, generator, width, height, style)

    if style['finish'] in {'glossy', 'polished'}:
        reflection = Image.new('RGBA', (width, height), (0, 0, 0, 0))
        reflection_draw = ImageDraw.Draw(reflection)
        reflection_draw.polygon(
            [(width // 2, 0), (width // 2 + 82, 0), (width // 4 + 130, height), (width // 4 + 45, height)],
            fill=(255, 255, 255, 42 if style['finish'] == 'glossy' else 30),
        )
        overlay = Image.alpha_composite(overlay, reflection.filter(ImageFilter.GaussianBlur(52)))

    image = Image.alpha_composite(surface.convert('RGBA'), overlay).convert('RGB')
    output = BytesIO()
    image.save(output, format='JPEG', quality=94, optimize=True)
    return output.getvalue()


def _has_valid_image(tile):
    if not tile.image or not tile.image.storage.exists(tile.image.name):
        return False
    try:
        with tile.image.open('rb') as image_file:
            with Image.open(image_file) as image:
                image.verify()
    except (OSError, ValueError, Image.DecompressionBombError):
        return False
    return True


class Command(BaseCommand):
    help = 'Generate distinct material-based catalog images for T001 through T100.'

    def add_arguments(self, parser):
        parser.add_argument('--refresh', action='store_true', help='Replace existing images with freshly generated material images.')

    def handle(self, *args, **options):
        assigned = 0
        skipped = 0
        retained_image_names = set()
        tiles_by_id = {
            tile.model_id: tile
            for tile in Tile.objects.filter(model_id__in=MODEL_IDS).order_by('model_id')
        }
        if not tiles_by_id:
            raise CommandError('No tile models T001-T100 were found. Seed the tile catalog first.')

        for model_id in MODEL_IDS:
            tile = tiles_by_id.get(model_id)
            if tile is None:
                continue
            if not options['refresh'] and _has_valid_image(tile) and tile.image.name not in retained_image_names:
                skipped += 1
                retained_image_names.add(tile.image.name)
                continue

            if options['refresh'] and tile.image:
                tile.image.delete(save=False)

            prefix = 'sample' if model_id in SAMPLE_STYLES else 'catalog'
            tile.image.save(f'{prefix}_{model_id.lower()}.jpg', ContentFile(build_tile_image(tile)), save=False)
            tile.save(update_fields=('image', 'updated_at'))
            assigned += 1

        missing = [model_id for model_id in MODEL_IDS if model_id not in tiles_by_id]
        if missing:
            self.stderr.write(self.style.WARNING(f'Missing tile models: {", ".join(missing)}'))
        self.stdout.write(self.style.SUCCESS(f'Assigned {assigned} images; preserved {skipped} valid images.'))