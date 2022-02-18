from django import forms


class ShifterDateTimeInput(forms.DateTimeInput):
    input_type = 'datetime-local'
