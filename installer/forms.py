from django import forms


class DatabaseConfigForm(forms.Form):
    host = forms.CharField(max_length=255, initial="127.0.0.1")
    port = forms.IntegerField(min_value=1, max_value=65535, initial=3306)
    database = forms.CharField(max_length=120, initial="carta_arcanum")
    test_database = forms.CharField(max_length=120, initial="test_carta_arcanum")
    user = forms.CharField(max_length=120, initial="carta")
    password = forms.CharField(
        max_length=255,
        required=False,
        widget=forms.PasswordInput(render_value=True),
    )

    def clean(self):
        cleaned_data = super().clean()
        for field_name in ("host", "database", "test_database", "user", "password"):
            value = cleaned_data.get(field_name)
            if isinstance(value, str) and any(character in value for character in "\r\n"):
                self.add_error(field_name, "This value cannot contain line breaks.")
        return cleaned_data
