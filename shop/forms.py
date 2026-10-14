import re

from django import forms

from .models import Enquiry, Review


class ReviewForm(forms.ModelForm):
    rating = forms.IntegerField(min_value=1, max_value=5, widget=forms.HiddenInput)

    class Meta:
        model = Review
        fields = ["rating", "title", "comment", "image"]
        widgets = {"comment": forms.Textarea(attrs={"rows": 4})}

    def clean_image(self):
        img = self.cleaned_data.get("image")
        if img and hasattr(img, "size") and img.size > 4 * 1024 * 1024:
            raise forms.ValidationError("Photo must be under 4 MB.")
        return img


class EnquiryForm(forms.ModelForm):
    class Meta:
        model = Enquiry
        fields = ["name", "business_name", "phone", "email", "city", "expected_qty", "message"]
        widgets = {"message": forms.Textarea(attrs={"rows": 4})}

    def clean_phone(self):
        p = re.sub(r"\D", "", self.cleaned_data["phone"])
        if p.startswith("91") and len(p) == 12:
            p = p[2:]
        if not re.match(r"^[6-9]\d{9}$", p):
            raise forms.ValidationError("Enter a valid 10-digit mobile number.")
        return p
