import csv
from pathlib import Path

from django.contrib.auth.models import Group, User
from django.core.management.base import BaseCommand

from inventory.models import Godown, InventoryStock, StockTransaction
from tiles.models import Tile


class Command(BaseCommand):
    help = 'Seed SriSun Tiles sample data'

    def handle(self, *args, **options):
        admin_group, _ = Group.objects.get_or_create(name='admin')
        customer_group, _ = Group.objects.get_or_create(name='customer')

        admin_user = User.objects.filter(username='admin').first()
        if admin_user is None:
            admin_user = User.objects.create_superuser('admin', 'admin@srisun.com', 'admin123')
        admin_user.is_staff = True
        admin_user.is_superuser = True
        admin_user.save()
        admin_user.groups.add(admin_group)
        customer_group.user_set.add(admin_user)

        godown_configs = [
            ('Godown 1', 'G1', 'North Warehouse'),
            ('Godown 2', 'G2', 'Central Storage'),
            ('Godown 3', 'G3', 'South Yard'),
        ]

        godowns = []
        for name, code, location in godown_configs:
            godown, _ = Godown.objects.get_or_create(code=code, defaults={'name': name, 'location': location})
            if godown.name != name or godown.location != location:
                godown.name = name
                godown.location = location
                godown.save()
            godowns.append(godown)

        categories = ['Ceramic', 'Porcelain', 'Vitrified', 'Wood Look', 'Marble Look', 'Bathroom', 'Flooring']
        colors = ['White', 'Beige', 'Black', 'Brown', 'Grey', 'Ivory', 'Blue', 'Red', 'Green']
        sizes = ['300x600', '600x600', '600x1200', '2x4', '12x12', '16x16']
        finishes = ['Glossy', 'Matte', 'Polished', 'Wood', 'Marble']

        sample_rows = []
        for idx in range(1, 101):
            model_id = f'T{idx:03d}'
            category = categories[(idx - 1) % len(categories)]
            color = colors[(idx - 1) % len(colors)]
            size = sizes[(idx - 1) % len(sizes)]
            finish = finishes[(idx - 1) % len(finishes)]
            name = f"{color} {category} Tile {idx}"
            price = 120 + ((idx * 37) % 500)
            description = f"High-quality {category.lower()} tile in {color.lower()} finish, ideal for floor and wall applications."

            tile, created = Tile.objects.get_or_create(
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

            if not created:
                tile.name = name
                tile.category = category
                tile.size = size
                tile.color = color
                tile.finish = finish
                tile.price = price
                tile.description = description
                tile.save()

            for godown in godowns:
                quantity = 25 + ((idx * 11 + godown.id * 17) % 180)
                InventoryStock.objects.update_or_create(
                    tile=tile,
                    godown=godown,
                    defaults={'quantity': quantity},
                )

                StockTransaction.objects.create(
                    tile=tile,
                    godown=godown,
                    quantity=quantity,
                    transaction_type='ADD',
                    notes='Initial stock seeding',
                    created_by=admin_user,
                )

            sample_rows.append({
                'model_id': model_id,
                'name': name,
                'category': category,
                'size': size,
                'color': color,
                'finish': finish,
                'price': price,
                'description': description,
            })

        dataset_dir = Path(__file__).resolve().parent.parent.parent / 'dataset'
        dataset_dir.mkdir(parents=True, exist_ok=True)
        csv_path = dataset_dir / 'sample_tile_data.csv'
        fieldnames = ['model_id', 'name', 'category', 'size', 'color', 'finish', 'price', 'description']

        with csv_path.open('w', newline='', encoding='utf-8') as csv_file:
            writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(sample_rows)

        self.stdout.write(self.style.SUCCESS(f'Seeded 100 tile models, 3 godowns, and stock data into {csv_path}.'))
