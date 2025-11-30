from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from import_export import resources, fields
from import_export.widgets import ForeignKeyWidget
from import_export.admin import ImportExportModelAdmin
from .models import Empleado, RegistroHora, Periodo, Departamento, Secretaria

# --- IMPORTACIÓN ---
class EmpleadoResource(resources.ModelResource):
    legajo = fields.Field(attribute='legajo', column_name='Nº identificación')
    nombre_completo = fields.Field(attribute='nombre_completo', column_name='Nombre del empleado')
    departamento = fields.Field(attribute='departamento', column_name='Departamento', widget=ForeignKeyWidget(Departamento, field='nombre'))
    
    class Meta: 
        model = Empleado
        import_id_fields = ('legajo',)
        fields = ('legajo', 'nombre_completo', 'departamento')
        skip_unchanged = False 
        
    def before_import_row(self, row, **kwargs):
        if row.get('Departamento'):
            nombre = str(row.get('Departamento')).strip().upper()
            row['Departamento'] = nombre
            Departamento.objects.get_or_create(nombre=nombre)
            
    def skip_row(self, instance, original, row, import_validation_errors=None):
        return row.get('Nº identificación') is None or str(row.get('Nº identificación')).strip() == ''

# --- PANELES ---
class SecretariaAdmin(admin.ModelAdmin): 
    list_display = ('nombre',)
    search_fields = ('nombre',)

class DepartamentoAdmin(admin.ModelAdmin): 
    list_display = ('nombre', 'secretaria')
    list_filter = ('secretaria',)
    search_fields = ('nombre', 'secretaria__nombre')

class PeriodoAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'fecha_inicio', 'fecha_fin', 'activo', 'cerrado', 'acciones_reporte')
    list_filter = ('activo', 'cerrado')
    list_editable = ('activo', 'cerrado')
    
    def acciones_reporte(self, obj):
        url_a = reverse('reporte_pdf', args=[obj.pk, 'andrea'])
        url_e = reverse('reporte_pdf', args=[obj.pk, 'edith'])
        return format_html(
            '<a class="btn btn-info btn-sm" href="{}" target="_blank" style="margin-right:5px;"><i class="fas fa-file-pdf"></i> Andrea</a>'
            '<a class="btn btn-success btn-sm" href="{}" target="_blank"><i class="fas fa-file-pdf"></i> Edith</a>', url_a, url_e)
    acciones_reporte.short_description = "Reportes"

class EmpleadoAdmin(ImportExportModelAdmin):
    resource_class = EmpleadoResource
    list_display = ('legajo', 'nombre_completo', 'departamento')
    search_fields = ('legajo', 'nombre_completo', 'departamento__nombre')
    list_filter = ('departamento',)

class RegistroHoraAdmin(admin.ModelAdmin):
    # CAMBIO 1: Quitamos 'periodo' de la lista
    list_display = (
        'empleado', 
        'departamento_imputacion', 
        'cantidad_horas', 
        'confirmar_exceso'
    )
    
    list_editable = ('cantidad_horas', 'departamento_imputacion', 'confirmar_exceso')
    list_filter = ('periodo', 'departamento_imputacion')
    search_fields = ('empleado__nombre_completo', 'empleado__departamento__nombre')
    autocomplete_fields = ['empleado', 'departamento_imputacion']
    
    # CAMBIO 2: Inyectamos el dato del período en el título
    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}
        
        # ¿Estás filtrando por período?
        periodo_id = request.GET.get('periodo__id__exact')
        
        if periodo_id:
            try:
                p = Periodo.objects.get(pk=periodo_id)
                estado = "🔒 CERRADO" if p.cerrado else "🟢 ABIERTO"
                extra_context['periodo_info'] = f"Viendo Registros de: {p.nombre} ({estado})"
                extra_context['periodo_bg'] = '#ffc107' if p.cerrado else '#28a745' # Amarillo o Verde
            except:
                pass
        else:
            # Si no filtras, mostramos el Activo por defecto
            p_activo = Periodo.objects.filter(activo=True).first()
            if p_activo:
                extra_context['periodo_info'] = f"Período Activo Actual: {p_activo.nombre}"
                extra_context['periodo_bg'] = '#17a2b8' # Azul Info
            else:
                extra_context['periodo_info'] = "⚠️ No hay período activo seleccionado"
                extra_context['periodo_bg'] = '#6c757d' # Gris

        return super().changelist_view(request, extra_context=extra_context)

    def get_changeform_initial_data(self, request):
        initial = super().get_changeform_initial_data(request)
        p_activo = Periodo.objects.filter(activo=True).first()
        if p_activo: initial['periodo'] = p_activo.pk
        return initial

    class Media:
        css = {'all': ('css/admin_fixes.css',)}

admin.site.register(Secretaria, SecretariaAdmin)
admin.site.register(Departamento, DepartamentoAdmin)
admin.site.register(Periodo, PeriodoAdmin)
admin.site.register(Empleado, EmpleadoAdmin)
admin.site.register(RegistroHora, RegistroHoraAdmin)