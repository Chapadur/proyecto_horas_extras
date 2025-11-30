from django.contrib import admin
from import_export import resources, fields
from import_export.admin import ImportExportModelAdmin
from .models import Empleado, RegistroHora, Periodo

# --- IMPORTACIÓN EMPLEADOS ---
class EmpleadoResource(resources.ModelResource):
    # Mapeo de columnas Excel -> Base de Datos
    legajo = fields.Field(attribute='legajo', column_name='Nº identificación')
    nombre_completo = fields.Field(attribute='nombre_completo', column_name='Nombre del empleado')
    cargo = fields.Field(attribute='cargo', column_name='Departamento')
    
    class Meta:
        model = Empleado
        import_id_fields = ('legajo',)
        fields = ('legajo', 'nombre_completo', 'cargo')
        skip_unchanged = True

    # --- NUEVO: FILTRO PARA IGNORAR FILAS VACÍAS ---
    def skip_row(self, instance, original, row, import_validation_errors=None):
        # Verificamos si la columna 'Nº identificación' está vacía o es nula
        valor_legajo = row.get('Nº identificación')
        
        # Si no hay legajo, o es una cadena vacía, le decimos al sistema que SALTE esta fila
        if valor_legajo is None or str(valor_legajo).strip() == '':
            return True
            
        # Si tiene legajo, procesamos normal
        return super().skip_row(instance, original, row, import_validation_errors)

# --- ADMIN PERÍODOS ---
class PeriodoAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'fecha_inicio', 'fecha_fin', 'activo', 'cerrado')
    list_filter = ('activo', 'cerrado')
    search_fields = ('nombre',)
    list_editable = ('activo', 'cerrado')

# --- ADMIN EMPLEADOS ---
class EmpleadoAdmin(ImportExportModelAdmin):
    resource_class = EmpleadoResource
    list_display = ('legajo', 'nombre_completo', 'cargo')
    search_fields = ('legajo', 'nombre_completo')
    list_filter = ('cargo',)

# --- ADMIN HORAS EXTRAS ---
class RegistroHoraAdmin(admin.ModelAdmin):
    list_display = ('periodo', 'empleado', 'fecha', 'cantidad_horas', 'estado_coloreado')
    list_filter = ('periodo', 'estado', 'empleado')
    search_fields = ('empleado__nombre_completo', 'motivo')
    
    from django.utils.html import format_html
    def estado_coloreado(self, obj):
        if obj.estado == 'AP': 
            color = 'green'
        elif obj.estado == 'RE': 
            color = 'red'
        else: 
            color = 'orange'
        return format_html('<b style="color: {};">{}</b>', color, obj.get_estado_display())
    estado_coloreado.short_description = "Estado"

# Registramos todo
admin.site.register(Empleado, EmpleadoAdmin)
admin.site.register(RegistroHora, RegistroHoraAdmin)
admin.site.register(Periodo, PeriodoAdmin)