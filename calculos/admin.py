from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User
from django.utils.html import format_html
from django.urls import reverse
from import_export import resources, fields
from import_export.widgets import ForeignKeyWidget
from import_export.admin import ImportExportModelAdmin
from .models import Empleado, RegistroHora, Periodo, Departamento, Secretaria, PerfilUsuario

# --- 1. GESTIÓN DE USUARIOS ---
class PerfilUsuarioInline(admin.StackedInline):
    model = PerfilUsuario
    can_delete = False
    verbose_name_plural = 'Perfil de Secretaría'

class UserAdmin(BaseUserAdmin):
    inlines = (PerfilUsuarioInline,)

admin.site.unregister(User)
admin.site.register(User, UserAdmin)

# --- 2. MIXIN DE SEGURIDAD (MEJORADO) ---
class FiltroSecretariaMixin:
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        
        # 1. Si es Superusuario, ve TODO.
        if request.user.is_superuser: 
            return qs
        
        # 2. Intentamos obtener la secretaría del usuario
        try:
            # Verificamos si tiene perfil y secretaría
            if hasattr(request.user, 'perfilusuario') and request.user.perfilusuario.secretaria:
                sec = request.user.perfilusuario.secretaria
                
                # Filtramos según el modelo que se esté viendo
                if self.model == Empleado:
                    return qs.filter(departamento__secretaria=sec)
                elif self.model == RegistroHora:
                    return qs.filter(departamento_imputacion__secretaria=sec)
                elif self.model == Departamento:
                    return qs.filter(secretaria=sec)
            else:
                # CASO DIRECTOR (O usuario sin secretaría específica):
                # Si queremos que el Director vea todo, dejamos esto así:
                return qs 
                # Si quisieras que un usuario sin secretaría no vea NADA, pondrías: return qs.none()
                
        except Exception:
            pass
            
        return qs

# --- IMPORTACIÓN ---
class EmpleadoResource(resources.ModelResource):
    legajo = fields.Field(attribute='legajo', column_name='Nº identificación')
    nombre_completo = fields.Field(attribute='nombre_completo', column_name='Nombre del empleado')
    departamento = fields.Field(attribute='departamento', column_name='Departamento', widget=ForeignKeyWidget(Departamento, field='nombre'))
    class Meta: model = Empleado; import_id_fields = ('legajo',); fields = ('legajo', 'nombre_completo', 'departamento'); skip_unchanged = False 
    def before_import_row(self, row, **kwargs):
        if row.get('Departamento'):
            nombre = str(row.get('Departamento')).strip().upper()
            row['Departamento'] = nombre
            Departamento.objects.get_or_create(nombre=nombre)
    def skip_row(self, instance, original, row, import_validation_errors=None):
        return row.get('Nº identificación') is None or str(row.get('Nº identificación')).strip() == ''

# --- PANELES CON SEGURIDAD APLICADA ---

class SecretariaAdmin(admin.ModelAdmin):
    list_display = ('nombre',); search_fields = ('nombre',)

# APLICAMOS EL MIXIN AQUÍ
class DepartamentoAdmin(FiltroSecretariaMixin, admin.ModelAdmin):
    list_display = ('nombre', 'secretaria')
    list_filter = ('secretaria',); search_fields = ('nombre', 'secretaria__nombre')

class PeriodoAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'fecha_inicio', 'fecha_fin', 'activo', 'cerrado', 'acciones_reporte')
    list_filter = ('activo', 'cerrado'); list_editable = ('activo', 'cerrado')
    def acciones_reporte(self, obj):
        url_a = reverse('reporte_pdf', args=[obj.pk, 'andrea'])
        url_e = reverse('reporte_pdf', args=[obj.pk, 'edith'])
        return format_html(
            '<a class="btn btn-info btn-sm" href="{}" target="_blank" style="margin-right:5px;"><i class="fas fa-file-pdf"></i> Andrea</a>'
            '<a class="btn btn-success btn-sm" href="{}" target="_blank"><i class="fas fa-file-pdf"></i> Edith</a>', url_a, url_e)
    acciones_reporte.short_description = "Reportes"

# APLICAMOS EL MIXIN AQUÍ
class EmpleadoAdmin(FiltroSecretariaMixin, ImportExportModelAdmin):
    resource_class = EmpleadoResource
    list_display = ('legajo', 'nombre_completo', 'departamento')
    search_fields = ('legajo', 'nombre_completo', 'departamento__nombre')
    list_filter = ('departamento__secretaria', 'departamento')

# APLICAMOS EL MIXIN AQUÍ
class RegistroHoraAdmin(FiltroSecretariaMixin, admin.ModelAdmin):
    list_display = ('empleado', 'departamento_imputacion', 'cantidad_horas', 'confirmar_exceso')
    list_editable = ('cantidad_horas', 'departamento_imputacion', 'confirmar_exceso')
    list_filter = ('periodo', 'departamento_imputacion')
    search_fields = ('empleado__nombre_completo', 'empleado__departamento__nombre')
    autocomplete_fields = ['empleado', 'departamento_imputacion']
    
    # Combinamos filtros de seguridad con filtro de período activo
    def get_queryset(self, request):
        qs = super().get_queryset(request) # Llama al Mixin primero
        if not request.GET:
            p_activo = Periodo.objects.filter(activo=True).first()
            if p_activo: qs = qs.filter(periodo=p_activo)
        return qs

    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}
        
        # HERRAMIENTAS SOLO PARA SUPERUSUARIO O DIRECTOR (Si quieres que el secretario no vea esto, usa is_superuser)
        if request.user.is_superuser:
            extra_context['reporte_historico_url'] = reverse('reporte_historico')
            
            periodo_id = request.GET.get('periodo__id__exact')
            if periodo_id:
                try:
                    p = Periodo.objects.get(pk=periodo_id)
                    st = "🔒 CERRADO" if p.cerrado else "🟢 ABIERTO"
                    extra_context['periodo_info'] = f"Viendo: {p.nombre} ({st})"
                    extra_context['periodo_bg'] = '#ffc107' 
                except: pass
            else:
                p_activo = Periodo.objects.filter(activo=True).first()
                if p_activo:
                    extra_context['periodo_info'] = f"Activo: {p_activo.nombre}"
                    extra_context['periodo_bg'] = '#17a2b8'
                else:
                    extra_context['periodo_info'] = "⚠️ Sin período activo"; extra_context['periodo_bg'] = '#6c757d'
        
        return super().changelist_view(request, extra_context=extra_context)
    
    def get_changeform_initial_data(self, request):
        initial = super().get_changeform_initial_data(request)
        p = Periodo.objects.filter(activo=True).first()
        if p: initial['periodo'] = p.pk
        return initial
    
    # Filtro de desplegables (Dropdowns)
    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if not request.user.is_superuser:
            try:
                sec = request.user.perfilusuario.secretaria
                if sec:
                    if db_field.name == "empleado": kwargs["queryset"] = Empleado.objects.filter(departamento__secretaria=sec)
                    if db_field.name == "departamento_imputacion": kwargs["queryset"] = Departamento.objects.filter(secretaria=sec)
            except: pass
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    class Media: css = {'all': ('css/admin_fixes.css',)}

admin.site.register(Secretaria, SecretariaAdmin)
admin.site.register(Departamento, DepartamentoAdmin)
admin.site.register(Periodo, PeriodoAdmin)
admin.site.register(Empleado, EmpleadoAdmin)
admin.site.register(RegistroHora, RegistroHoraAdmin)