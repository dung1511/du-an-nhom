from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from rooms.views import home , about_page 

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('rooms.urls')),
    path('accounts/', include('accounts.urls', namespace='accounts')),
    path('feedback/', include('feedback.urls', namespace='feedback')),
    path('contact/', include('contact.urls', namespace='contact')),
    path('blog/', include('blog.urls', namespace='blog')),
    path('', home, name='home'),
    path('about/', about_page, name='about'),
   ]

# Serve media files during development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)