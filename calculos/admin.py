from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from import_export import resources, fields
from import_export.widgets import ForeignKeyWidget
from import_export.admin import ImportExportModelAdmin
from .models import Empleado, RegistroHora, Periodo, Departamento, Secretaria

# --- RECURSO DE IMPORTACIÓN (EmpleadoResource) ---
class EmpleadoResource(resources.ModelResource):
    legajo = fields.Field(attribute='legajo', column_name='Nº identificación')
    nombre_completo = fields.Field(attribute='nombre_completo', column_name='Nombre del empleado')
    departamento = fields.Field(
        attribute='departamento', 
        column_name='Departamento',
        widget=ForeignKeyWidget(Departamento, field='nombre')
    )
    
    class Meta:
        model = Empleado
        import_id_fields = ('legajo',)
        fields = ('legajo', 'nombre_completo', 'departamento')
        skip_unchanged = False 

    def before_import_row(self, row, **kwargs):
        nombre_depto_raw = row.get('Departamento')
        if nombre_depto_raw:
            nombre_limpio = str(nombre_depto_raw).strip().upper()
            row['Departamento'] = nombre_limpio
            Departamento.objects.get_or_create(nombre=nombre_limpio)

    def skip_row(self, instance, original, row, import_validation_errors=None):
        val = row.get('Nº identificación')
        return val is None or str(val).strip() == ''

# --- PANELES DE ADMINISTRACIÓN ---

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
        url_andrea = reverse('reporte_pdf', args=[obj.pk, 'andrea'])
        url_edith = reverse('reporte_pdf', args=[obj.pk, 'edith'])
        return format_html(
            '<a class="btn btn-info btn-sm" href="{}" target="_blank" style="margin-right:5px;"><i class="fas fa-file-pdf"></i> Andrea</a>'
            '<a class="btn btn-success btn-sm" href="{}" target="_blank"><i class="fas fa-file-pdf"></i> Edith</a>', url_andrea, url_edith
        )
    acciones_reporte.short_description = "Reportes"

class EmpleadoAdmin(ImportExportModelAdmin):
    resource_class = EmpleadoResource
    list_display = ('legajo', 'nombre_completo', 'departamento')
    search_fields = ('legajo', 'nombre_completo', 'departamento__nombre')
    list_filter = ('departamento__secretaria', 'departamento')

class RegistroHoraAdmin(admin.ModelAdmin):
    # --- LISTA DE COLUMNAS FINAL Y LIMPIA ---
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
    
    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}
        
        # 1. Pasar la URL del reporte histórico al contexto
        extra_context['reporte_historico_url'] = reverse('reporte_historico')
        
        # 2. Lógica de Período (para la barra de contexto)
        periodo_id = request.GET.get('periodo__id__exact')
        if periodo_id:
            try:
                p = Periodo.objects.get(pk=periodo_id)
                estado = "🔒 CERRADO" if p.cerrado else "🟢 ABIERTO"
                extra_context['periodo_info'] = f"Viendo Registros de: {p.nombre} ({estado})"
                extra_context['periodo_bg'] = '#ffc107' 
            except: pass
        else:
            p_activo = Periodo.objects.filter(activo=True).first()
            if p_activo:
                extra_context['periodo_info'] = f"Período Activo Actual: {p_activo.nombre}"
                extra_context['periodo_bg'] = '#17a2b8'
            else:
                extra_context['periodo_info'] = "⚠️ No hay período activo"
                extra_context['periodo_bg'] = '#6c757d'
        
        return super().changelist_view(request, extra_context=extra_context)
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        
        # APLICAR FILTRO POR DEFECTO (Período Activo)
        if not request.GET:
            periodo_activo = Periodo.objects.filter(activo=True).first()
            
            if periodo_activo:
                qs = qs.filter(periodo=periodo_activo)
        
        return qs
    
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