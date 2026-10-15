from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse

from inventory.models import Godown, InventoryStock, StockTransaction, StockTransfer
from tiles.models import Tile


class InventorySeedDataTests(TestCase):
	def test_seeded_catalog_has_expected_counts(self):
		call_command('seed_sri_sun_data')

		self.assertEqual(Tile.objects.count(), 100)
		self.assertEqual(Godown.objects.count(), 3)
		self.assertEqual(InventoryStock.objects.count(), 300)


class StockOperationTests(TestCase):
	def setUp(self):
		call_command('seed_sri_sun_data', verbosity=0)
		self.tile = Tile.objects.get(model_id='T001')
		self.source, self.destination = Godown.objects.order_by('code')[:2]
		self.source_stock = InventoryStock.objects.get(tile=self.tile, godown=self.source)
		self.destination_stock = InventoryStock.objects.get(tile=self.tile, godown=self.destination)
		self.source_stock.quantity = 50
		self.source_stock.save()
		self.destination_stock.quantity = 20
		self.destination_stock.save()
		self.admin = get_user_model().objects.get(username='admin')
		self.client.force_login(self.admin)

	def test_add_and_remove_stock_record_transactions(self):
		self.client.post(reverse('add_stock'), {
			'tile': self.tile.pk,
			'godown': self.source.pk,
			'quantity': 5,
		})
		self.client.post(reverse('remove_stock'), {
			'tile': self.tile.pk,
			'godown': self.source.pk,
			'quantity': 3,
		})

		self.source_stock.refresh_from_db()
		self.assertEqual(self.source_stock.quantity, 52)
		self.assertTrue(StockTransaction.objects.filter(
			tile=self.tile,
			godown=self.source,
			transaction_type='ADD',
			quantity=5,
			created_by=self.admin,
		).exists())
		self.assertTrue(StockTransaction.objects.filter(
			tile=self.tile,
			godown=self.source,
			transaction_type='REMOVE',
			quantity=3,
			created_by=self.admin,
		).exists())

	def test_transfer_updates_both_godowns_and_audit_records(self):
		self.client.post(reverse('transfer_stock'), {
			'tile': self.tile.pk,
			'source_godown': self.source.pk,
			'destination_godown': self.destination.pk,
			'quantity': 7,
		})

		self.source_stock.refresh_from_db()
		self.destination_stock.refresh_from_db()
		self.assertEqual(self.source_stock.quantity, 43)
		self.assertEqual(self.destination_stock.quantity, 27)
		self.assertTrue(StockTransfer.objects.filter(
			tile=self.tile,
			source_godown=self.source,
			destination_godown=self.destination,
			quantity=7,
			created_by=self.admin,
		).exists())

	def test_customer_cannot_open_admin_dashboard(self):
		customer = get_user_model().objects.create_user(username='customer', password='test-pass-123')
		self.client.force_login(customer)

		response = self.client.get(reverse('dashboard'))

		self.assertEqual(response.status_code, 403)

	def test_unauthenticated_dashboard_and_reports_redirect_to_login(self):
		self.client.logout()
		for url_name in ('dashboard', 'admin_dashboard', 'inventory_report'):
			with self.subTest(url_name=url_name):
				response = self.client.get(reverse(url_name))
				self.assertEqual(response.status_code, 302)
				self.assertIn(reverse('admin_login'), response.url)

	def test_staff_admin_can_open_dashboard_and_reports(self):
		admin_user = get_user_model().objects.create_user(
			username='staff-admin',
			password='test-pass-123',
			is_staff=True,
		)
		self.client.force_login(admin_user)

		for url_name in ('dashboard', 'admin_dashboard', 'inventory_report'):
			with self.subTest(url_name=url_name):
				self.assertEqual(self.client.get(reverse(url_name)).status_code, 200)
