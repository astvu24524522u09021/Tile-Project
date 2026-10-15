from django import forms

from tiles.models import Tile


class AddStockForm(forms.Form):
    tile = forms.ModelChoiceField(queryset=Tile.objects.all(), label='Tile Model', widget=forms.Select(attrs={'class': 'form-select'}))
    godown = forms.ChoiceField(label='Godown', widget=forms.Select(attrs={'class': 'form-select'}))
    quantity = forms.IntegerField(min_value=1, widget=forms.NumberInput(attrs={'class': 'form-control'}))
    notes = forms.CharField(required=False, widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3}))

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from inventory.models import Godown
        self.fields['godown'].choices = [(godown.id, str(godown)) for godown in Godown.objects.all()]


class RemoveStockForm(forms.Form):
    tile = forms.ModelChoiceField(queryset=Tile.objects.all(), label='Tile Model', widget=forms.Select(attrs={'class': 'form-select'}))
    godown = forms.ChoiceField(label='Godown', widget=forms.Select(attrs={'class': 'form-select'}))
    quantity = forms.IntegerField(min_value=1, widget=forms.NumberInput(attrs={'class': 'form-control'}))
    notes = forms.CharField(required=False, widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3}))

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from inventory.models import Godown
        self.fields['godown'].choices = [(godown.id, str(godown)) for godown in Godown.objects.all()]


class TransferStockForm(forms.Form):
    tile = forms.ModelChoiceField(queryset=Tile.objects.all(), label='Tile Model', widget=forms.Select(attrs={'class': 'form-select'}))
    source_godown = forms.ChoiceField(label='Source Godown', widget=forms.Select(attrs={'class': 'form-select'}))
    destination_godown = forms.ChoiceField(label='Destination Godown', widget=forms.Select(attrs={'class': 'form-select'}))
    quantity = forms.IntegerField(min_value=1, widget=forms.NumberInput(attrs={'class': 'form-control'}))
    notes = forms.CharField(required=False, widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3}))

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from inventory.models import Godown
        choices = [(godown.id, str(godown)) for godown in Godown.objects.all()]
        self.fields['source_godown'].choices = choices
        self.fields['destination_godown'].choices = choices
