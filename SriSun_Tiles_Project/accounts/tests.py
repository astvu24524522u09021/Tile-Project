from urllib.parse import parse_qs, urlsplit

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse

from accounts.models import CustomerProfile
from tiles.models import Tile


class AdminAccessTests(TestCase):
	def setUp(self):
		call_command('seed_sri_sun_data', verbosity=0)

	def test_django_admin_login_keeps_admin_authenticated_for_admin_and_reports(self):
		response = self.client.post(reverse('admin:login'), {
			'username': 'admin',
			'password': 'Admin@123',
		})

		self.assertRedirects(response, reverse('admin:index'))
		for url_name in ('admin:index', 'dashboard', 'inventory_report'):
			with self.subTest(url_name=url_name):
				self.assertEqual(self.client.get(reverse(url_name)).status_code, 200)

		nav_response = self.client.get(reverse('assistant'))
		for url_name in ('admin_dashboard', 'admin_product_list', 'inventory_report', 'prediction', 'admin:index'):
			with self.subTest(url_name=url_name):
				self.assertContains(nav_response, reverse(url_name))
		self.assertContains(nav_response, 'Admin Dashboard')

	def test_admin_login_alias_uses_django_admin_and_returns_to_dashboard(self):
		admin_login_response = self.client.get(reverse('admin_login'))
		self.assertEqual(urlsplit(admin_login_response.url).path, reverse('admin:login'))
		next_url = parse_qs(urlsplit(admin_login_response.url).query)['next'][0]
		self.assertEqual(next_url, reverse('admin_dashboard'))

		response = self.client.post(admin_login_response.url, {
			'username': 'admin',
			'password': 'Admin@123',
			'next': next_url,
		})
		self.assertRedirects(response, reverse('admin_dashboard'))
		self.assertEqual(self.client.get(reverse('admin_dashboard')).status_code, 200)

	def test_django_admin_can_create_edit_and_delete_tiles(self):
		admin_user = get_user_model().objects.get(username='admin')
		self.client.force_login(admin_user)

		create_response = self.client.post(reverse('admin:tiles_tile_add'), {
			'model_id': 'ADMIN-001',
			'name': 'Admin Tile',
			'category': 'Ceramic',
			'size': '600x600',
			'color': 'White',
			'finish': 'Matte',
			'price': '1200.00',
			'description': 'Created in Django Admin',
			'_save': 'Save',
		})
		self.assertEqual(create_response.status_code, 302)
		tile = Tile.objects.get(model_id='ADMIN-001')

		edit_response = self.client.post(reverse('admin:tiles_tile_change', args=[tile.pk]), {
			'model_id': tile.model_id,
			'name': 'Updated Admin Tile',
			'category': 'Ceramic',
			'size': '600x600',
			'color': 'White',
			'finish': 'Matte',
			'price': '1250.00',
			'description': 'Updated in Django Admin',
			'_save': 'Save',
		})
		self.assertEqual(edit_response.status_code, 302)
		tile.refresh_from_db()
		self.assertEqual(tile.name, 'Updated Admin Tile')

		delete_response = self.client.post(
			reverse('admin:tiles_tile_delete', args=[tile.pk]),
			{'post': 'yes'},
		)
		self.assertEqual(delete_response.status_code, 302)
		self.assertFalse(Tile.objects.filter(pk=tile.pk).exists())

	def test_profile_role_does_not_grant_admin_access(self):
		profile_admin = get_user_model().objects.create_user(
			username='profile-admin',
			password='test-pass-123',
		)
		CustomerProfile.objects.create(user=profile_admin, role='admin')
		self.client.force_login(profile_admin)

		for url_name in ('dashboard', 'inventory_report'):
			with self.subTest(url_name=url_name):
				self.assertEqual(self.client.get(reverse(url_name)).status_code, 403)

		self.assertNotEqual(self.client.get(reverse('admin:index')).status_code, 200)

	def test_unauthenticated_users_are_redirected_to_login(self):
		for url_name in ('dashboard', 'inventory_report'):
			with self.subTest(url_name=url_name):
				response = self.client.get(reverse(url_name))
				self.assertEqual(response.status_code, 302)
				self.assertIn(reverse('admin_login'), response.url)

	def test_authenticated_customer_sees_the_shared_application_navbar(self):
		customer = get_user_model().objects.create_user(
			username='navbar-customer',
			password='test-pass-123',
		)
		CustomerProfile.objects.create(user=customer, role='customer')
		self.client.force_login(customer)

		response = self.client.get(reverse('assistant'))

		self.assertEqual(response.status_code, 200)
		for url_name in ('home', 'tile_list', 'assistant', 'customer_dashboard', 'tile_scan', 'profile'):
			with self.subTest(url_name=url_name):
				self.assertContains(response, reverse(url_name))
		for url_name in ('dashboard', 'inventory_report', 'admin_product_list', 'prediction', 'admin:index'):
			with self.subTest(url_name=url_name):
				self.assertNotContains(response, reverse(url_name))
		self.assertContains(response, 'Profile')
		self.assertNotContains(response, 'navbar-customer')
		self.assertContains(response, reverse('logout'))

	def test_registration_creates_hashed_user_and_redirects_to_login(self):
		password = 'Srisun-customer-739!'
		response = self.client.post(reverse('register'), {
			'full_name': 'New Customer',
			'username': 'new-customer',
			'email': 'new.customer@example.com',
			'password1': password,
			'password2': password,
		})

		user = get_user_model().objects.get(username='new-customer')
		self.assertRedirects(response, reverse('login'))
		self.assertNotEqual(user.password, password)
		self.assertTrue(user.check_password(password))
		self.assertFalse(user.is_staff)
		self.assertFalse(user.is_superuser)
		self.assertEqual(user.get_full_name(), 'New Customer')

	def test_registration_rejects_duplicate_username_and_mismatched_passwords(self):
		response = self.client.post(reverse('register'), {
			'full_name': 'Duplicate User',
			'username': 'admin',
			'email': 'new@example.com',
			'password1': 'Srisun-customer-739!',
			'password2': 'Srisun-customer-739!',
		})
		self.assertContains(response, 'An account with this username already exists.')

		response = self.client.post(reverse('register'), {
			'full_name': 'Another User',
			'username': 'another-user',
			'email': 'another@example.com',
			'password1': 'Srisun-customer-739!',
			'password2': 'Srisun-customer-740!',
		})
		self.assertContains(response, 'The two password fields didn’t match.')

	def test_customer_login_dashboard_admin_denial_and_post_logout(self):
		customer = get_user_model().objects.create_user(
			username='flow-customer',
			password='Srisun-customer-739!',
			first_name='Flow',
			last_name='Customer',
		)
		response = self.client.post(reverse('login'), {
			'username': 'flow-customer',
			'password': 'Srisun-customer-739!',
		})
		self.assertRedirects(response, reverse('customer_dashboard'))
		self.assertContains(self.client.get(reverse('customer_dashboard')), 'Flow Customer')

		admin_response = self.client.get(reverse('admin:index'))
		self.assertEqual(admin_response.status_code, 302)
		self.assertIn(reverse('admin:login'), admin_response.url)

		self.assertEqual(self.client.get(reverse('logout')).status_code, 405)
		self.assertRedirects(self.client.post(reverse('logout')), reverse('home'))
		dashboard_response = self.client.get(reverse('customer_dashboard'))
		self.assertEqual(dashboard_response.status_code, 302)
		self.assertIn(reverse('login'), dashboard_response.url)
