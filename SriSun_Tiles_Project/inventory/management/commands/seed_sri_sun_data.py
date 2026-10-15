import csv
import random
from decimal import Decimal
from pathlib import Path

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.management.base import BaseCommand

from inventory.models import Godown, InventoryStock, StockTransaction
from tiles.models import Tile


class Command(BaseCommand):
    help = 'Seed the SriSun Tiles system with 100 tile models and 3 godowns.'

    def handle(self, *args, **options):
        Group.objects.get_or_create(name='customer')

        User = get_user_model()
        admin_group, _ = Group.objects.get_or_create(name='admin')
        admin_user = User.objects.filter(username='admin').first()
        if admin_user is None:
            admin_user = User.objects.create_superuser('admin', 'admin@srisun.com', 'Admin@123')
            admin_user.groups.add(admin_group)

        godowns = [
            {'name': 'Godown 1', 'code': 'G1', 'location': 'Main Warehouse North'},
            {'name': 'Godown 2', 'code': 'G2', 'location': 'Main Warehouse South'},
            {'name': 'Godown 3', 'code': 'G3', 'location': 'Dispatch Yard'},
        ]

        seed_godowns = [
            Godown.objects.get_or_create(
                code=item['code'],
                defaults={'name': item['name'], 'location': item['location']},
            )[0]
            for item in godowns
        ]

        tile_rows = []
        categories = ['Ceramic', 'Vitrified', 'Porcelain', 'Bathroom', 'Floor', 'Wall']
        colors = ['White', 'Beige', 'Black', 'Grey', 'Brown', 'Blue', 'Green', 'Ivory', 'Red']
        finishes = ['Glossy', 'Matte', 'Polished', 'Wood', 'Marble']
        sizes = ['300x600', '600x600', '600x1200', '1200x1200', '2x4', '4x4']

        for i in range(1, 101):
            category = categories[(i - 1) % len(categories)]
            color = colors[(i - 1) % len(colors)]
            finish = finishes[(i - 1) % len(finishes)]
            size = sizes[(i - 1) % len(sizes)]
            model_id = f'T{i:03d}'
            name = f'{color} {finish} {size} Tile'
            price = Decimal(1000 + ((i * 137) % 4500))
            description = f'{category} tile in {color} with {finish.lower()} finish.'
            tile, _ = Tile.objects.get_or_create(
                model_id=model_id,
                defaults={
                    'name': name,
                    'category': category,
                    'size': size,
                    'color': color,
                    'finish': finish,
                    'price': price,
                    'description': description,
                },
            )
            tile_rows.append({
                'model_id': tile.model_id,
                'name': tile.name,
                'category': tile.category,
                'size': tile.size,
                'color': tile.color,
                'finish': tile.finish,
                'price': float(tile.price),
                'description': tile.description,
            })

            for godown in seed_godowns:
                qty = random.randint(18, 140)
                _, created = InventoryStock.objects.get_or_create(
                    tile=tile,
                    godown=godown,
                    defaults={'quantity': qty},
                )
                if created:
                    StockTransaction.objects.create(
                        tile=tile,
                        godown=godown,
                        quantity=qty,
                        transaction_type='ADD',
                        notes='Seed data initialization',
                        created_by=None,
                    )

        csv_path = Path(__file__).resolve().parents[3] / 'dataset' / 'sample_tile_data.csv'
        with csv_path.open('w', newline='', encoding='utf-8') as csvfile:
            fieldnames = ['model_id', 'name', 'category', 'size', 'color', 'finish', 'price', 'description']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(tile_rows)

        self.stdout.write(self.style.SUCCESS(f'Seeded {Tile.objects.count()} tiles and {Godown.objects.count()} godowns successfully.'))
