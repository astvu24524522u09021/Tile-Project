from django.db import models


class Tile(models.Model):
    model_id = models.CharField(max_length=50, unique=True)
    name = models.CharField(max_length=200)
    category = models.CharField(max_length=100)
    size = models.CharField(max_length=50)
    color = models.CharField(max_length=50)
    finish = models.CharField(max_length=50)
    price = models.DecimalField(max_digits=12, decimal_places=2)
    description = models.TextField(blank=True, default='')
    image = models.ImageField(upload_to='tiles/', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['model_id']

    def __str__(self):
        return f"{self.model_id} - {self.name}"
