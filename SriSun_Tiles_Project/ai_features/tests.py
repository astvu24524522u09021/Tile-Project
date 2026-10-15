from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse
from django.core.files.base import ContentFile
from io import BytesIO
from PIL import Image

from ai_features.services import search_tiles_for_ai_query
from tiles.models import Tile


class AIQueryTests(TestCase):
	def setUp(self):
		call_command('seed_sri_sun_data')

	def test_search_tiles_by_color(self):
		result = search_tiles_for_ai_query('white tiles')

		self.assertIn('results', result)
		self.assertTrue(result['results'])
		self.assertTrue(any(tile.color.lower() == 'white' for tile in result['results']))

	def test_assistant_results_render_existing_tile_images_and_fallbacks(self):
		tile = Tile.objects.get(model_id='T003')
		image_data = BytesIO()
		Image.new('RGB', (16, 16), (20, 20, 20)).save(image_data, format='JPEG')
		tile.image.save('assistant-t003.jpg', ContentFile(image_data.getvalue()), save=True)

		response = self.client.get(reverse('assistant'), {'q': 'black'})

		self.assertEqual(response.status_code, 200)
		self.assertContains(response, f'src="{tile.image.url}"')
		self.assertContains(response, 'class="tile-card-image"')
		self.assertContains(response, 'No Image')
		self.assertEqual(
			{result.model_id for result in response.context['results']},
			{f'T{number:03d}' for number in range(3, 100, 9)},
		)
