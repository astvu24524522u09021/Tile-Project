from django import forms

from .models import Tile


class TileScanForm(forms.Form):
    image = forms.ImageField(
        widget=forms.ClearableFileInput(attrs={
            'accept': 'image/*',
            'capture': 'environment',
        }),
    )

    def clean_image(self):
        image = self.cleaned_data['image']
        if image.size > 8 * 1024 * 1024:
            raise forms.ValidationError('Choose an image smaller than 8 MB.')
        return image


class TileForm(forms.ModelForm):
    class Meta:
        model = Tile
        fields = [
            'model_id',
            'name',
            'category',
            'size',
            'color',
            'finish',
            'price',
            'description',
            'image',
        ]
        widgets = {
            'model_id': forms.TextInput(attrs={'class': 'form-control'}),
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'category': forms.TextInput(attrs={'class': 'form-control'}),
            'size': forms.TextInput(attrs={'class': 'form-control'}),
            'color': forms.TextInput(attrs={'class': 'form-control'}),
            'finish': forms.TextInput(attrs={'class': 'form-control'}),
            'price': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'image': forms.ClearableFileInput(attrs={'class': 'form-control'}),
        }
