from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import Group
from django.contrib.auth.views import redirect_to_login
from django.db.models import Sum, Value
from django.db.models.functions import Coalesce
from django.views.decorators.http import require_POST
from django.shortcuts import redirect, render
from django.urls import reverse

from inventory.models import InventoryStock
from tiles.models import Tile

from .forms import CustomUserCreationForm, ProfileUpdateForm, UserLoginForm
from .models import CustomerProfile
from .permissions import is_admin_user


def home_view(request):
    total_tiles = Tile.objects.count()
    total_stock = InventoryStock.objects.aggregate(total=Sum('quantity'))['total'] or 0
    low_stock_items = InventoryStock.objects.filter(quantity__lt=20).count()
    recent_tiles = Tile.objects.order_by('-created_at')[:6]
    return render(
        request,
        'home.html',
        {
            'total_tiles': total_tiles,
            'total_stock': total_stock,
            'low_stock_items': low_stock_items,
            'recent_tiles': recent_tiles,
        },
    )


@login_required
def customer_dashboard_view(request):
    tiles = Tile.objects.annotate(
        total_stock=Coalesce(Sum('stock_entries__quantity'), Value(0)),
    )[:12]
    total_stock = InventoryStock.objects.aggregate(total=Sum('quantity'))['total'] or 0
    return render(request, 'customer_dashboard.html', {'tiles': tiles, 'total_stock': total_stock})


def register_view(request):
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            CustomerProfile.objects.get_or_create(user=user, defaults={'role': 'customer'})
            customer_group, _ = Group.objects.get_or_create(name='customer')
            user.groups.add(customer_group)
            messages.success(request, 'Registration successful. Please log in to continue.')
            return redirect('login')
    else:
        form = CustomUserCreationForm()
    return render(request, 'accounts/register.html', {'form': form})


def login_view(request):
    if request.user.is_authenticated:
        destination = 'admin_dashboard' if is_admin_user(request.user) else 'customer_dashboard'
        return redirect(destination)

    if request.method == 'POST':
        form = UserLoginForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            if is_admin_user(user):
                form.add_error(None, 'Admin accounts must sign in at /admin-login/.')
            else:
                login(request, user)
                messages.success(request, f'Welcome back, {user.username}!')
                return redirect('customer_dashboard')
    else:
        form = UserLoginForm()
    return render(request, 'accounts/login.html', {'form': form})


def admin_login_view(request):
    next_url = request.GET.get('next') or reverse('admin_dashboard')
    return redirect_to_login(next_url, login_url=reverse('admin:login'))


@require_POST
def logout_view(request):
    logout(request)
    messages.info(request, 'You have been logged out successfully.')
    return redirect('home')


@login_required
def profile_view(request):
    profile, _ = CustomerProfile.objects.get_or_create(user=request.user)
    if request.method == 'POST':
        form = ProfileUpdateForm(request.POST, instance=profile)
        if form.is_valid():
            form.save()
            messages.success(request, 'Profile updated successfully.')
            return redirect('profile')
    else:
        form = ProfileUpdateForm(instance=profile)
    return render(request, 'accounts/profile.html', {'form': form, 'profile': profile})
