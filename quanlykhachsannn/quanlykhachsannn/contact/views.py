from django.shortcuts import render, redirect
from django.contrib import messages
from .forms import ContactForm
from .models import Contact

def contact_us(request):
    if request.method == 'POST':
        form = ContactForm(request.POST)
        if form.is_valid():
            contact = form.save(commit=False)
            # Use form data for all users
            contact.name = form.cleaned_data['name']
            contact.email = form.cleaned_data['email']
            contact.save()
            messages.success(request, 'Your message has been sent successfully!')
            return redirect('contact:contact_us')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = ContactForm()

    return render(request, 'contact/contact.html', {'form': form})

