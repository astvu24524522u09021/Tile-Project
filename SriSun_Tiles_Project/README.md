# SriSun Tiles Management System

A Django-based inventory and tile management platform for SriSun Tiles, built to manage tile models, godown stock, transfer operations, AI-powered search, and ML-based demand forecasting.

## Features

- User registration and login
- Admin and customer access control
- Tile catalog management with 100 sample models
- Three godown stock tracking
- Add, remove, and transfer stock operations
- Low-stock detection
- AI assistant for natural-language tile search
- Demand prediction using machine learning
- Reports for inventory, transfers, and forecasts
- Responsive Bootstrap UI

## Tech Stack

- Python
- Django
- SQLite
- HTML
- CSS
- JavaScript
- Bootstrap
- Pandas
- NumPy
- Scikit-learn
- Matplotlib
- Joblib

## Project Structure

- `config/` - Django project settings and URL routing
- `accounts/` - authentication and profile logic
- `tiles/` - tile model CRUD
- `inventory/` - stock management and godown logic
- `ai_features/` - natural-language assistant
- `ml_features/` - machine learning forecasting
- `reports/` - reporting pages
- `templates/` - HTML templates
- `static/` - CSS and JS files
- `dataset/` - sample CSV dataset
- `ml_models/` - saved model output

## Local Setup

1. Open a terminal in the project folder.
2. Ensure the existing Python environment is active.
3. Install dependencies:

   ```bash
   python -m pip install -r requirements.txt
   ```

4. Apply migrations:

   ```bash
   python manage.py makemigrations
   python manage.py migrate
   ```

5. Apply the existing admin-account permissions migration. It promotes the existing `Kanagu@22` account without changing its password or any other user or inventory data:

   ```bash
   python manage.py migrate
   ```

6. Seed sample data:

   ```bash
   python manage.py seed_data
   ```

7. Generate and assign example tile images for T001-T005:

   ```bash
   python manage.py seed_sample_tile_images
   ```

   This command only fills blank image fields for those five existing tile models. Tile images are stored under `media/tiles/` and served at `MEDIA_URL` while `DEBUG` is enabled. The tile catalog search accepts multiple words across model ID, name, category, size, color, finish, and description; for example, search for `black 600x1200 polished`.

8. Run the server:

   ```bash
   python manage.py runserver
   ```

## Authentication and Access

- Admins sign in through Django's built-in admin at `http://127.0.0.1:8000/admin/` using the existing admin account credentials. The migration does not reset passwords.
- Users register at `/register/`, sign in at `/login/`, and use `/dashboard/` for their protected dashboard.
- Tile browsing and search are available at `/tiles/`; customer sessions cannot access product, stock, or godown management.
- Logout is a CSRF-protected POST action in the site navigation.

## Access URLs

- Home: `http://127.0.0.1:8000/`
- Login: `http://127.0.0.1:8000/login/`
- Register: `http://127.0.0.1:8000/register/`
- User dashboard: `http://127.0.0.1:8000/dashboard/`
- Admin inventory dashboard: `http://127.0.0.1:8000/admin/dashboard/`
- Django Admin: `http://127.0.0.1:8000/admin/`
- Tile catalog: `http://127.0.0.1:8000/tiles/`
- AI assistant: `http://127.0.0.1:8000/ai/`
- ML forecast: `http://127.0.0.1:8000/ml/`
- Reports: `http://127.0.0.1:8000/reports/inventory/`

## AI Feature

The AI helper uses a keyword-based natural-language matching system to interpret user requests such as:

- "Show white tiles"
- "Show 2x4 tiles"
- "Which godown has Model T101?"
- "Show low stock tiles"
- "Find bathroom tiles"

## ML Feature

The machine learning module builds a small demand-forecasting model from tile inventory and stock transaction data, then saves the trained model in the `ml_models/` directory.

## Notes

- SQLite is used initially as requested.
- The application is designed for a clean, modular structure as requested.
- Some features are intentionally lightweight and production-friendly for a project prototype.
