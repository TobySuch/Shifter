from django import forms
from django.contrib.auth import get_user_model


class ChangePasswordForm(forms.Form):
    new_password = forms.CharField(
        widget=forms.PasswordInput, label="New Password"
    )
    confirm_password = forms.CharField(
        widget=forms.PasswordInput, label="Confirm Password"
    )

    def clean(self):
        cleaned_data = super(ChangePasswordForm, self).clean()

        new_password = cleaned_data.get("new_password")
        confirm_password = cleaned_data.get("confirm_password")

        if new_password and confirm_password:
            if new_password != confirm_password:
                raise forms.ValidationError("Passwords do not match!")

        return cleaned_data


class NewUserForm(forms.Form):
    email = forms.EmailField(label="Email")
    password = forms.CharField(widget=forms.PasswordInput, label="Password")
    confirm_password = forms.CharField(
        widget=forms.PasswordInput, label="Confirm Password"
    )

    def clean(self):
        cleaned_data = super(NewUserForm, self).clean()

        password = cleaned_data.get("password")
        confirm_password = cleaned_data.get("confirm_password")

        if password and confirm_password:
            if password != confirm_password:
                raise forms.ValidationError("Passwords do not match!")

        return cleaned_data

    def clean_email(self):
        email = self.cleaned_data["email"]
        User = get_user_model()
        email_used = User.objects.filter(email=email).count() > 0

        if email_used:
            raise forms.ValidationError("Email already taken!")

        return email
