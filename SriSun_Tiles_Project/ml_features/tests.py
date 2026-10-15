from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
import pandas as pd

from . import services


class PredictionAccessTests(TestCase):
	def test_customer_cannot_open_prediction_pages(self):
		customer = get_user_model().objects.create_user(username='customer', password='test-pass-123')
		self.client.force_login(customer)

		for url_name in ('prediction', 'prediction_results'):
			with self.subTest(url_name=url_name):
				self.assertEqual(self.client.get(reverse(url_name)).status_code, 403)

	@patch('ml_features.views.get_model_status', return_value={'status': 'ready', 'message': 'Model ready', 'metrics': {'mse': None, 'r2': None}})
	@patch('ml_features.views.get_prediction_summary', return_value={'predictions': []})
	def test_staff_can_open_prediction_pages(self, summary_mock, status_mock):
		staff = get_user_model().objects.create_user(
			username='staff',
			password='test-pass-123',
			is_staff=True,
		)
		self.client.force_login(staff)

		for url_name in ('prediction', 'prediction_results'):
			with self.subTest(url_name=url_name):
				self.assertEqual(self.client.get(reverse(url_name)).status_code, 200)

	@patch('ml_features.services._build_dataset')
	@patch('ml_features.services.load_saved_model')
	@patch('ml_features.services.train_and_save_model')
	def test_results_reuse_saved_model_without_retraining(self, train_mock, model_mock, dataset_mock):
		class SavedModel:
			def predict(self, features):
				return [12.5] * len(features)

		dataset_mock.return_value = pd.DataFrame([{
			'model_id': 'T001',
			'name': 'White Tile',
			'current_stock': 20,
			'price': 1000.0,
			'incoming_qty': 5,
			'outgoing_qty': 2,
		}])
		model_mock.return_value = SavedModel()

		result = services.get_prediction_summary()

		train_mock.assert_not_called()
		self.assertEqual(result['status'], 'ready')
		self.assertEqual(result['predictions'], [{
			'model_id': 'T001',
			'tile_name': 'White Tile',
			'current_stock': 20,
			'predicted_demand': 12.5,
		}])
