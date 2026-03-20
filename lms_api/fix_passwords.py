# fix_passwords.py
import os
import django

# ✅ FIXED: Changed to 'main.settings'
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'main.settings')
django.setup()

from django.contrib.auth.hashers import make_password
from lms_api.models import Teacher

for teacher in Teacher.objects.all():
    if not teacher.password.startswith('pbkdf2_'):
        old_password = teacher.password
        teacher.password = make_password(teacher.password)
        teacher.save()
        print(f"✅ Fixed password for {teacher.email}")
    else:
        print(f"⏭️  {teacher.email} already has hashed password")

print("\n✅ Done!")