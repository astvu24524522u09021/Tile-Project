from io import BytesIO
import tempfile

from django.core.files.base import ContentFile
from django.core.files.uploadedfile import SimpleUploadedFile
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TestCase, override_settings
from django.urls import reverse
from PIL import Image, ImageEnhance, ImageStat

from inventory.models import Godown, InventoryStock
from tiles.management.commands.seed_sample_tile_images import (
	SAMPLE_STYLES,
	build_sample_image,
	build_tile_image,
)
from tiles.models import Tile


class TileSearchTests(TestCase):
	def setUp(self):
		self.matching_tile = Tile.objects.create(
			model_id='T003',
			name='Black Polished 600x1200 Tile',
			category='Porcelain',
			size='600x1200',
			color='Black',
			finish='Polished',
			price='1411.00',
		)
		Tile.objects.create(
			model_id='T006',
			name='White Matte 300x600 Tile',
			category='Ceramic',
			size='300x600',
			color='White',
			finish='Matte',
			price='999.00',
		)
		godown = Godown.objects.create(name='Test Godown', code='TEST')
		InventoryStock.objects.create(tile=self.matching_tile, godown=godown, quantity=37)

	def test_multi_term_search_matches_across_tile_fields_and_shows_stock(self):
		for query in ('black polished', '600x1200', 'black 600x1200 polished', 'porcelain black'):
			with self.subTest(query=query):
				response = self.client.get(reverse('tile_search'), {'q': query})

				self.assertEqual(response.status_code, 200)
				self.assertEqual(
					[item['tile'].pk for item in response.context['tiles']],
					[self.matching_tile.pk],
				)
				self.assertContains(response, '37')

	def test_detail_page_uses_the_stored_image_url(self):
		with tempfile.TemporaryDirectory() as media_root:
			with override_settings(MEDIA_ROOT=media_root):
				self.matching_tile.image.save('t003.jpg', ContentFile(b'sample image'), save=True)
				response = self.client.get(reverse('tile_detail', args=[self.matching_tile.pk]))

				self.assertContains(response, self.matching_tile.image.url)
				self.assertContains(response, 'tile-detail-image')
				self.assertNotContains(response, 'No Image')

	def test_catalog_filters_category_color_and_finish(self):
		response = self.client.get(reverse('tile_list'), {
			'category': 'Porcelain',
			'color': 'Black',
			'finish': 'Polished',
		})

		self.assertEqual(response.status_code, 200)
		self.assertEqual([item['tile'] for item in response.context['tiles']], [self.matching_tile])

	def test_custom_product_crud_is_staff_only_and_supports_full_crud(self):
		customer = get_user_model().objects.create_user(username='catalog-customer', password='test-pass-123')
		self.client.force_login(customer)
		for url_name, args in (
			('tile_create', ()),
			('tile_update', (self.matching_tile.pk,)),
			('tile_delete', (self.matching_tile.pk,)),
		):
			with self.subTest(url_name=url_name):
				self.assertEqual(self.client.get(reverse(url_name, args=args)).status_code, 403)

		admin = get_user_model().objects.create_superuser(
			username='catalog-admin',
			email='catalog-admin@example.com',
			password='test-pass-123',
		)
		self.client.force_login(admin)
		create_response = self.client.post(reverse('tile_create'), {
			'model_id': 'NEW-001',
			'name': 'New Tile',
			'category': 'Ceramic',
			'size': '600x600',
			'color': 'White',
			'finish': 'Matte',
			'price': '1200.00',
			'description': 'Admin-created tile',
		})
		self.assertRedirects(create_response, reverse('admin_product_list'))
		created_tile = Tile.objects.get(model_id='NEW-001')

		self.client.post(reverse('tile_update', args=[created_tile.pk]), {
			'name': 'Updated Tile',
			'category': 'Ceramic',
			'size': '600x600',
			'color': 'White',
			'finish': 'Matte',
			'price': '1250.00',
			'description': 'Updated description',
		})
		created_tile.refresh_from_db()
		self.assertEqual(created_tile.name, 'Updated Tile')

		delete_response = self.client.post(reverse('tile_delete', args=[created_tile.pk]))
		self.assertRedirects(delete_response, reverse('admin_product_list'))
		self.assertFalse(Tile.objects.filter(pk=created_tile.pk).exists())


class SampleTileImageCommandTests(TestCase):
	def setUp(self):
		for index in range(1, 6):
			Tile.objects.create(
				model_id=f'T{index:03d}',
				name=f'Sample Tile {index}',
				category='Porcelain',
				size='600x600',
				color='Grey',
				finish='Matte',
				price='1000.00',
			)

	def test_command_assigns_valid_images_to_only_the_first_five_tiles(self):
		with tempfile.TemporaryDirectory() as media_root:
			with override_settings(MEDIA_ROOT=media_root):
				call_command('seed_sample_tile_images', verbosity=0)

				tiles = Tile.objects.order_by('model_id')
				self.assertEqual(tiles.count(), 5)
				for tile in tiles:
					self.assertTrue(tile.image.storage.exists(tile.image.name))
					with Image.open(tile.image.path) as image:
						self.assertEqual(image.format, 'JPEG')

				response = self.client.get(reverse('tile_detail', args=[tiles.get(model_id='T003').pk]))
				self.assertContains(response, '/media/tiles/sample_t003.jpg')

	def test_refresh_replaces_flat_samples_with_textured_images(self):
		with tempfile.TemporaryDirectory() as media_root:
			with override_settings(MEDIA_ROOT=media_root):
				originals = {}
				for model_id, style in SAMPLE_STYLES.items():
					tile = Tile.objects.get(model_id=model_id)
					image_data = build_sample_image(model_id, style)
					tile.image.save(f'sample_{model_id.lower()}.jpg', ContentFile(image_data), save=True)
					originals[model_id] = image_data

				call_command('seed_sample_tile_images', refresh=True, verbosity=0)

				new_hashes = set()
				for model_id in SAMPLE_STYLES:
					tile = Tile.objects.get(model_id=model_id)
					with tile.image.open('rb') as image_file:
						image_data = image_file.read()
					self.assertEqual(tile.image.name, f'tiles/sample_{model_id.lower()}.jpg')
					self.assertNotEqual(image_data, originals[model_id])
					new_hashes.add(hash(image_data))
					with Image.open(BytesIO(image_data)) as image:
						self.assertEqual(image.size, (960, 720))
						self.assertGreater(ImageStat.Stat(image.convert('L')).stddev[0], 5)
				self.assertEqual(len(new_hashes), len(SAMPLE_STYLES))

	def test_command_fills_all_one_hundred_tiles_and_preserves_existing_samples(self):
		colors = ('Blue', 'Green', 'Ivory', 'Red', 'White', 'Beige', 'Black', 'Brown', 'Grey')
		finishes = ('Glossy', 'Matte', 'Polished', 'Wood', 'Marble')
		categories = ('Wall', 'Ceramic', 'Vitrified', 'Porcelain', 'Bathroom', 'Floor')
		sizes = ('4x4', '300x600', '600x600', '600x1200', '1200x1200', '2x4')

		for number in range(6, 101):
			color = colors[(number - 1) % len(colors)]
			finish = finishes[(number - 1) % len(finishes)]
			Tile.objects.create(
				model_id=f'T{number:03d}',
				name=f'{color} {finish} {sizes[(number - 1) % len(sizes)]} Tile',
				category=categories[(number - 1) % len(categories)],
				size=sizes[(number - 1) % len(sizes)],
				color=color,
				finish=finish,
				price='1000.00',
			)

		with tempfile.TemporaryDirectory() as media_root:
			with override_settings(MEDIA_ROOT=media_root):
				original_sample_images = {}
				for model_id, style in SAMPLE_STYLES.items():
					tile = Tile.objects.get(model_id=model_id)
					image_data = build_sample_image(model_id, style)
					tile.image.save(
						f'sample_{model_id.lower()}.jpg',
						ContentFile(image_data),
						save=True,
					)
					self.assertEqual(tile.image.name, f'tiles/sample_{model_id.lower()}.jpg')
					original_sample_images[model_id] = image_data

				duplicate_tile = Tile.objects.get(model_id='T006')
				duplicate_tile.image = Tile.objects.get(model_id='T005').image.name
				duplicate_tile.save(update_fields=('image',))

				call_command('seed_sample_tile_images', verbosity=0)

				tiles = list(Tile.objects.order_by('model_id'))
				self.assertEqual(len(tiles), 100)
				self.assertEqual(len({tile.image.name for tile in tiles}), 100)
				image_hashes = set()
				for tile in tiles:
					self.assertTrue(tile.image.storage.exists(tile.image.name), tile.model_id)
					with tile.image.open('rb') as image_file:
						image_data = image_file.read()
						self.assertRegex(tile.image.name, rf'{tile.model_id.lower()}\.jpg$')
						self.assertGreater(len(image_data), 1000)
						image_hashes.add(hash(image_data))
						with Image.open(BytesIO(image_data)) as image:
							self.assertEqual(image.format, 'JPEG')
							image.verify()
						if tile.model_id in original_sample_images:
							self.assertEqual(image_data, original_sample_images[tile.model_id])

				self.assertEqual(len(image_hashes), 100)
				for model_id in SAMPLE_STYLES:
					tile = Tile.objects.get(model_id=model_id)
					self.assertEqual(tile.image.name, f'tiles/sample_{model_id.lower()}.jpg')


class TileScanTests(TestCase):
	def setUp(self):
		self.media_directory = tempfile.TemporaryDirectory()
		media_settings = override_settings(MEDIA_ROOT=self.media_directory.name)
		media_settings.enable()
		self.addCleanup(media_settings.disable)
		self.addCleanup(self.media_directory.cleanup)

		sample_tiles = {
			'T001': ('White Glossy 300x600 Tile', 'Ceramic', '300x600', 'White', 'Glossy', 'Ceramic tile in White with glossy finish.'),
			'T002': ('Beige Matte 600x600 Tile', 'Vitrified', '600x600', 'Beige', 'Matte', 'Vitrified tile in Beige with matte finish.'),
			'T003': ('Black Polished 600x1200 Tile', 'Porcelain', '600x1200', 'Black', 'Polished', 'Porcelain tile in Black with polished finish.'),
			'T004': ('Grey Wood 1200x1200 Tile', 'Bathroom', '1200x1200', 'Grey', 'Wood', 'Bathroom tile in Grey with wood finish.'),
			'T005': ('Brown Marble 2x4 Tile', 'Floor', '2x4', 'Brown', 'Marble', 'Floor tile in Brown with marble finish.'),
		}
		for model_id in SAMPLE_STYLES:
			name, category, size, color, finish, description = sample_tiles[model_id]
			tile = Tile.objects.create(
				model_id=model_id,
				name=name,
				category=category,
				size=size,
				color=color,
				finish=finish,
				price='1411.00',
				description=description,
			)
			tile.image.save(
				f'sample_{model_id.lower()}.jpg',
				ContentFile(build_tile_image(tile)),
				save=True,
			)
			if model_id == 'T003':
				self.matching_tile = tile

	def _post_image(self, image_data, filename='scan.jpg'):
		return self.client.post(
			reverse('tile_scan'),
			{'image': SimpleUploadedFile(filename, image_data, content_type='image/jpeg')},
		)

	def _reference_image(self):
		with self.matching_tile.image.open('rb') as image_file:
			return image_file.read()

	def test_scan_page_exposes_camera_capture_and_upload_controls(self):
		response = self.client.get(reverse('tile_scan'))

		self.assertContains(response, 'Open Camera')
		self.assertContains(response, 'Capture')
		self.assertContains(response, 'Upload Image')
		self.assertContains(response, 'Analyze Tile')
		self.assertContains(response, 'js/tile_scan.js')

	def test_exact_reference_images_return_their_matching_model_ids(self):
		for model_id in SAMPLE_STYLES:
			tile = Tile.objects.get(model_id=model_id)
			with tile.image.open('rb') as image_file:
				response = self._post_image(image_file.read())
			with self.subTest(model_id=model_id):
				self.assertEqual(response.context.get('tile'), tile)
				self.assertContains(response, model_id)

		self.assertContains(response, 'Verified Tile Match')
		self.assertContains(response, 'Total stock:')

	def test_cropped_and_lit_reference_still_matches(self):
		with Image.open(BytesIO(self._reference_image())) as reference:
			image = reference.crop((48, 36, 912, 684))
			image = ImageEnhance.Brightness(image).enhance(1.1)
			image = ImageEnhance.Contrast(image).enhance(0.95)
			output = BytesIO()
			image.save(output, format='JPEG', quality=90)

		response = self._post_image(output.getvalue(), 'captured-tile.jpg')

		self.assertEqual(response.context.get('tile'), self.matching_tile)

	def test_low_detail_image_is_rejected_instead_of_guessing(self):
		output = BytesIO()
		Image.new('RGB', (320, 240), (128, 128, 128)).save(output, format='JPEG')

		response = self._post_image(output.getvalue(), 'plain.jpg')

		self.assertIsNone(response.context.get('tile'))
		self.assertContains(response, 'No exact match found. Please scan the tile again.')

	def test_unrelated_high_texture_image_is_not_guessed(self):
		output = BytesIO()
		Image.effect_noise((320, 240), 80).convert('RGB').save(output, format='JPEG')

		response = self._post_image(output.getvalue(), 'unrelated-texture.jpg')

		self.assertIsNone(response.context.get('tile'))
		self.assertContains(response, 'No exact match found. Please scan the tile again.')

	def test_tiles_page_keeps_black_search_and_shows_scan_button(self):
		response = self.client.get(reverse('tile_list'), {'q': 'black'})

		self.assertEqual(
			[item['tile'].model_id for item in response.context['tiles']],
			['T003'],
		)
		self.assertContains(response, 'value="black"')
		self.assertContains(response, '📷 Scan Tile')
		self.assertContains(response, reverse('tile_scan'))
