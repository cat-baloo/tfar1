
# core/forms.py
from django import forms
from .models import ClientMembership

class UploadForm(forms.Form):
    file = forms.FileField(help_text="Upload .xlsx with 15 headers, or 16 including 'client'")
    client = forms.ChoiceField(choices=[], label="Client")

    def __init__(self, *args, **kwargs):
        user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)
        self.fields["client"].choices = self._client_choices(user)

    def _client_choices(self, user):
        if user is None or not user.is_authenticated:
            return []
        memberships = ClientMembership.objects.filter(user=user).select_related("client").order_by("client__name")
        return [(str(m.client.id), m.client.name) for m in memberships]


class ClientSelectForm(forms.Form):
    client = forms.ChoiceField(choices=[], label="Client")

    def __init__(self, *args, **kwargs):
        user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)
        self.fields["client"].choices = self._client_choices(user)

    def _client_choices(self, user):
        if user is None or not user.is_authenticated:
            return []
        memberships = ClientMembership.objects.filter(user=user).select_related("client").order_by("client__name")
        return [(str(m.client.id), m.client.name) for m in memberships]
