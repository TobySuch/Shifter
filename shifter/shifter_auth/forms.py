from django import forms


class ChangePasswordForm(forms.Form):
    new_password = forms.CharField(widget=forms.PasswordInput,
                                   label='New Password')
    confirm_password = forms.CharField(widget=forms.PasswordInput,
                                       label='Confirm Password')

    def clean(self):
        cleaned_data = super(ChangePasswordForm, self).clean()

        new_password = cleaned_data.get('new_password')
        confirm_password = cleaned_data.get('confirm_password')

        if new_password and confirm_password:
            if new_password != confirm_password:
                raise forms.ValidationError("Passwords do not match!")

        return cleaned_data
