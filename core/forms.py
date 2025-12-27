
from django import forms
class UploadForm(forms.Form):
    file = forms.FileField(help_text="Upload .xlsx with 15 columns")
