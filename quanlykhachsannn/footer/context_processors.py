from footer.models import FooterText

def footer_text(request):
    footer_obj = FooterText.objects.first()  # Get the first entry
    return {'footer_text_obj': footer_obj}