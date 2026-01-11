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
    """Form for first-time setup with password fields."""

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


class CreateUserForm(forms.Form):
    """Form for creating new users with auto-generated passwords."""

    email = forms.EmailField(label="Email")
    is_staff = forms.BooleanField(
        label="Administrator",
        required=False,
        help_text="Administrators can manage users and change site settings",
    )

    def clean_email(self):
        email = self.cleaned_data["email"]
        User = get_user_model()
        email_used = User.objects.filter(email=email).count() > 0

        if email_used:
            raise forms.ValidationError("Email already taken!")

        return email


class UserSearchForm(forms.Form):
    """Form for searching users in the user list."""

    search = forms.CharField(
        required=False,
        label="Search",
        widget=forms.TextInput(
            attrs={
                "class": "input-primary flex-grow",
                "placeholder": "Search users by email",
            }
        ),
    )


class UserEditForm(forms.ModelForm):
    """Form for editing user details."""

    class Meta:
        model = get_user_model()
        fields = ["email", "is_staff", "is_active"]
        labels = {
            "email": "Email",
            "is_staff": "Administrator",
            "is_active": "Active",
        }

    def __init__(self, *args, editing_self=False, **kwargs):
        super().__init__(*args, **kwargs)
        self.editing_self = editing_self

        # If editing self, disable is_staff and is_active fields
        if editing_self:
            self.fields["is_staff"].disabled = True
            self.fields["is_active"].disabled = True

    def clean_email(self):
        email = self.cleaned_data["email"]
        User = get_user_model()
        # Check if email is taken by another user (not the current instance)
        existing = User.objects.filter(email=email).exclude(
            pk=self.instance.pk
        )
        if existing.exists():
            raise forms.ValidationError("Email already taken!")
        return email

    def clean(self):
        cleaned_data = super().clean()
        # Double-check: if editing self, preserve original values
        if self.editing_self:
            cleaned_data["is_staff"] = self.instance.is_staff
            cleaned_data["is_active"] = self.instance.is_active
        return cleaned_data
