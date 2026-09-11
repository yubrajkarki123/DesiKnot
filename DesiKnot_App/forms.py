from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from .models import CustomOrder
from .models import ProductReview




# =========================
# USER REGISTRATION FORM
# =========================
class CustomUserCreationForm(UserCreationForm):
    first_name = forms.CharField(
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter your first name'
        })
    )

    last_name = forms.CharField(
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter your last name'
        })
    )

    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter your email'
        })
    )

    class Meta:
        model = User
        fields = ("first_name", "last_name", "username", "email", "password1", "password2")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        for field_name in ['username', 'password1', 'password2']:
            self.fields[field_name].widget.attrs.update({
                'class': 'form-control',
                'placeholder': f'Enter {field_name}'
            })


# =========================
# CUSTOM ORDER STEP 1
# =========================
class CustomOrderBasicForm(forms.ModelForm):

    class Meta:
        model = CustomOrder
        fields = ['phone_number', 'alt_phone_number', 'address']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        for field in self.fields.values():
            field.widget.attrs.update({
                'class': 'form-control'
            })

        self.fields['phone_number'].required = True
        self.fields['address'].required = True
        self.fields['alt_phone_number'].required = False


# =========================
# CUSTOM ORDER STEP 2 
# =========================
class CustomOrderDetailForm(forms.ModelForm):

    class Meta:
        model = CustomOrder

        fields = [
            'kurtha_name',
            'delivery_date',
            'order_details'
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Kurtha Name
        self.fields['kurtha_name'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Enter Kurtha Name'
        })
        self.fields['kurtha_name'].required = True

        # Delivery Date
        self.fields['delivery_date'].widget = forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        })
        self.fields['delivery_date'].required = False

        # Order Details
        self.fields['order_details'].widget = forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'Additional instructions (optional)'
        })
        self.fields['order_details'].required = False



class ReviewForm(forms.ModelForm):
    class Meta:
        model = ProductReview
        fields = ['rating', 'comment']
        widgets = {
            'rating': forms.Select(choices=[(i, i) for i in range(1, 6)]),
            'comment': forms.Textarea(attrs={'rows': 3}),
        }

