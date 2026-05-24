import openpyxl
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from api.models import Student

class Command(BaseCommand):
    help = 'Imports students from an Excel file into the Neon database'

    def add_arguments(self, parser):
        # This allows us to pass the filename in the terminal
        parser.add_argument('excel_file', type=str, help='Path to the excel file')

    def handle(self, *args, **kwargs):
        file_path = kwargs['excel_file']
        
        try:
            workbook = openpyxl.load_workbook(file_path)
            sheet = workbook.active
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Error opening file: {e}"))
            return

        success_count = 0
        
        # iter_rows(min_row=2) skips the header row
        for row in sheet.iter_rows(min_row=2, values_only=True):
            # Assuming Column A is Full Name, Column B is Student ID
            full_name = str(row[0]).strip() if row[0] else ''
            student_id = str(row[1]).strip() if row[1] else ''

            if not full_name or not student_id:
                continue

            # Split the full name into First Name and Last Name
            name_parts = full_name.split(' ', 1)
            first_name = name_parts[0]
            last_name = name_parts[1] if len(name_parts) > 1 else ''

            # Check if student already exists to prevent crashing
            if not User.objects.filter(username=student_id).exists():
                # 1. Create the User with the default password
                user = User.objects.create_user(
                    username=student_id,
                    first_name=first_name,
                    last_name=last_name,
                    password='samspass123'
                )
                
                # 2. Create the linked Student profile
                Student.objects.create(
                    user=user, 
                    has_changed_password=False
                )
                
                self.stdout.write(self.style.SUCCESS(f'✅ Created: {full_name} ({student_id})'))
                success_count += 1
            else:
                self.stdout.write(self.style.WARNING(f'⚠️ Skipped: {student_id} already exists.'))

        self.stdout.write(self.style.SUCCESS(f'\n🎉 Import Complete! Added {success_count} students to the database.'))