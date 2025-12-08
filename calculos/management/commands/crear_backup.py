import os
import shutil
from datetime import datetime
from django.core.management.base import BaseCommand
from django.conf import settings

class Command(BaseCommand):
    help = 'Genera una copia de seguridad de la base de datos SQLite y limpia las antiguas.'

    def handle(self, *args, **options):
        # 1. Configuración
        db_path = settings.DATABASES['default']['NAME']
        backup_dir = os.path.join(settings.BASE_DIR, 'backups')
        
        # 2. Crear carpeta de backups si no existe
        if not os.path.exists(backup_dir):
            os.makedirs(backup_dir)
            self.stdout.write(self.style.WARNING(f'📁 Carpeta creada: {backup_dir}'))

        # 3. Nombre del archivo con Fecha y Hora
        timestamp = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
        backup_filename = f"db_backup_{timestamp}.sqlite3"
        backup_path = os.path.join(backup_dir, backup_filename)

        # 4. Realizar la copia
        try:
            if os.path.exists(db_path):
                shutil.copy2(db_path, backup_path)
                self.stdout.write(self.style.SUCCESS(f'✅ Backup creado exitosamente: {backup_filename}'))
            else:
                self.stdout.write(self.style.ERROR('❌ No se encontró la base de datos original.'))
                return
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'❌ Error al crear backup: {str(e)}'))
            return

        # 5. Limpieza (Borrar backups de más de 30 días)
        self.limpiar_backups_antiguos(backup_dir)

    def limpiar_backups_antiguos(self, directorio):
        dias_a_mantener = 30
        ahora = datetime.now().timestamp()
        
        count = 0
        for archivo in os.listdir(directorio):
            ruta_completa = os.path.join(directorio, archivo)
            if os.path.isfile(ruta_completa) and archivo.startswith("db_backup_"):
                # Obtener fecha de creación/modificación
                file_time = os.path.getmtime(ruta_completa)
                # Si es más viejo que X días (dias * 24h * 60m * 60s)
                if (ahora - file_time) > (dias_a_mantener * 86400):
                    os.remove(ruta_completa)
                    count += 1
        
        if count > 0:
            self.stdout.write(self.style.WARNING(f'🗑️ Se eliminaron {count} backups antiguos (>30 días).'))