
from django.contrib import admin
from .models import Client, ClientMembership, TfarRecord, UserProfile

admin.site.register(Client)
admin.site.register(ClientMembership)
admin.site.register(TfarRecord)
admin.site.register(UserProfile)
