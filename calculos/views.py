from django.shortcuts import render, get_object_or_404
from django.http import HttpResponse, HttpResponseBadRequest
from django.db.models import Sum, FloatField, Value, CharField 
from django.db.models.functions import Coalesce, Cast 
from django.template.loader import render_to_string
from weasyprint import HTML
import datetime
import locale
from django.utils import timezone
from collections import defaultdict
import calculos.models as models 
import json

try: locale.setlocale(locale.LC_TIME, 'es_ES.UTF-8')
except: pass

# ====================================================================
# FUNCIÓN 1: GENERACIÓN DE PDF
# ====================================================================
def generar_reporte_pdf(request, periodo_id, destinatario):
    periodo = get_object_or_404(models.Periodo, pk=periodo_id)
    
    if not periodo.cerrado:
        mensaje = f"""... mensaje de bloqueo ..."""
        return HttpResponseBadRequest(mensaje)
    
    if destinatario == 'andrea':
        encabezado = {'linea1': 'A la', 'nombre': 'SRA. BALTIERI ANDREA SOLEDAD', 'cargo': 'A/C del Área Sueldos', 'organismo': 'del Gobierno de la Ciudad de Chajarí', 'ubicacion': 'S / D'}
    else:
        encabezado = {'linea1': 'A la SRA. SHORT, EDITH MARISA', 'nombre': '', 'cargo': 'Encargada del Área Sueldos', 'organismo': 'del Gobierno de la Ciudad de Chajarí', 'ubicacion': 'S / D'}
    
    # PROCESAMIENTO INTELIGENTE DE DATOS
    registros_raw = models.RegistroHora.objects.filter(periodo=periodo).select_related(
        'empleado', 'empleado__departamento', 'departamento_imputacion'
    ).order_by('empleado__nombre_completo')

    agrupados = defaultdict(lambda: {'empleado': None, 'lista_registros': []})
    for r in registros_raw:
        agrupados[r.empleado.id]['empleado'] = r.empleado
        agrupados[r.empleado.id]['lista_registros'].append(r)

    lista_final = []
    total_general = 0

    for item in agrupados.values():
        empleado = item['empleado']
        cargas = item['lista_registros']
        
        suma_horas = sum(c.cantidad_horas for c in cargas)
        total_general += suma_horas
        
        if len(cargas) == 1:
            depto_mostrar = cargas[0].departamento_imputacion.nombre if cargas[0].departamento_imputacion else "-"
        else:
            depto_mostrar = empleado.departamento.nombre if empleado.departamento else "-"

        lista_final.append({
            'nombre': empleado.nombre_completo,
            'departamento': depto_mostrar,
            'total_horas': suma_horas
        })

    fecha_actual = datetime.date.today()
    fecha_nota = f"Chajarí, {fecha_actual.day} de {fecha_actual.strftime('%B')} de {fecha_actual.year}"

    context = {'periodo': periodo, 'registros': lista_final, 'encabezado': encabezado, 'fecha_nota': fecha_nota, 'total_general': total_general}

    html_string = render_to_string('reportes/pdf_horas.html', context)
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'inline; filename="Reporte_{periodo.nombre}.pdf"'
    HTML(string=html_string, base_url=request.build_absolute_uri()).write_pdf(response)
    return response

# ====================================================================
# FUNCIÓN 2: DASHBOARD HISTÓRICO (Gráficos) - ÚLTIMO INTENTO DE ROBUSTEZ
# ====================================================================
def reporte_historico(request):
    # 1. Gráfico de Barras (Histórico - Mínimo Filtro)
    # CONSULTA: Solo filtra los que tienen período asignado, sin límite de 6 meses
    data_barra_qs = list(models.RegistroHora.objects.exclude(periodo__isnull=True).values( 
        'periodo__nombre',
        'periodo__fecha_inicio'
    ).annotate(
        total_horas=Sum(Cast('cantidad_horas', FloatField()))
    ).order_by('periodo__fecha_inicio'))
    print('data_barra_qs')
    print(data_barra_qs)
    
    labels_barra = [f"{item['periodo__nombre']}" for item in data_barra_qs]
    datos_barra = [float(item['total_horas']) for item in data_barra_qs]
    
    print('labels_barra')
    print(labels_barra)
    
    print('datos_barra')
    print(datos_barra)

    # 2. Gráfico de Torta (Distribución por Secretaría del Período Activo)
    periodo_actual = models.Periodo.objects.filter(activo=True).first()

    print('periodo_actual')
    print(periodo_actual)
    
    labels_torta = ['Sin Datos']
    datos_torta = [1]
    periodo_actual_nombre = "No Definido"
    
    if periodo_actual:
        periodo_actual_nombre = periodo_actual.nombre
        
        # CONSULTA: Filtra por período activo Y Excluye cualquier registro con Secretaría NULL
        data_torta_qs = list(models.RegistroHora.objects.filter(
            periodo=periodo_actual
        ).exclude(departamento_imputacion__secretaria__isnull=True).values( # <--- CRÍTICO: Evita JOINs rotos
            secretaria_nombre=Coalesce('departamento_imputacion__secretaria__nombre', Value('SIN SECRETARÍA', output_field=CharField()))
        ).annotate(
            total_horas=Sum(Cast('cantidad_horas', FloatField()))
        ).order_by('secretaria_nombre'))
        
        labels_torta = [item['secretaria_nombre'] for item in data_torta_qs]
        datos_torta = [float(item['total_horas']) for item in data_torta_qs]
        
        if not any(datos_torta):
             labels_torta = ['Sin Datos']
             datos_torta = [1]


#    context = {
 #       'labels_barra': labels_barra,
  #      'datos_barra': datos_barra,
   #     'labels_torta': labels_torta,
    #    'datos_torta': datos_torta,
     #   'periodo_actual_nombre': periodo_actual_nombre
    # }

    context = {
        'labels_barra': json.dumps(labels_barra),
        'datos_barra': json.dumps(datos_barra),
        'labels_torta': json.dumps(labels_torta),
        'datos_torta': json.dumps(datos_torta),
        'periodo_actual_nombre': periodo_actual_nombre,
    }



    
    print('contextcontextcontextcontextcontext')
    print(context)

    return render(request, 'reportes/historico.html', context)