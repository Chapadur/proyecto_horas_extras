from django.shortcuts import get_object_or_404
from django.http import HttpResponse
from django.template.loader import render_to_string
from weasyprint import HTML
import datetime
import locale
from .models import Periodo, RegistroHora

try: locale.setlocale(locale.LC_TIME, 'es_ES.UTF-8')
except: pass

def generar_reporte_pdf(request, periodo_id, destinatario):
    periodo = get_object_or_404(Periodo, pk=periodo_id)
    
    # 1. Configurar Encabezado
    if destinatario == 'andrea':
        encabezado = {'linea1': 'A la', 'nombre': 'SRA. BALTIERI ANDREA SOLEDAD', 'cargo': 'A/C del Área Sueldos', 'organismo': 'del Gobierno de la Ciudad de Chajarí', 'ubicacion': 'S / D'}
    else:
        encabezado = {'linea1': 'A la SRA. SHORT, EDITH MARISA', 'nombre': '', 'cargo': 'Encargada del Área Sueldos', 'organismo': 'del Gobierno de la Ciudad de Chajarí', 'ubicacion': 'S / D'}
    
    # 2. PROCESAMIENTO INTELIGENTE DE DATOS
    # Traemos todos los registros del período
    registros_raw = RegistroHora.objects.filter(periodo=periodo).select_related(
        'empleado', 'empleado__departamento', 'departamento_imputacion'
    ).order_by('empleado__nombre_completo')

    # Agrupamos en memoria para contar cuántas cargas tiene cada uno
    agrupados = {}
    for r in registros_raw:
        emp_id = r.empleado.id
        if emp_id not in agrupados:
            agrupados[emp_id] = {'empleado': r.empleado, 'lista_registros': []}
        agrupados[emp_id]['lista_registros'].append(r)

    lista_final = []
    total_general = 0

    for item in agrupados.values():
        empleado = item['empleado']
        cargas = item['lista_registros']
        
        # Sumamos horas
        suma_horas = sum(c.cantidad_horas for c in cargas)
        total_general += suma_horas
        
        # --- LÓGICA DE DEPARTAMENTO ---
        if len(cargas) == 1:
            # Si tiene UNA sola carga -> Usamos la Imputación de esa carga
            depto_mostrar = cargas[0].departamento_imputacion.nombre if cargas[0].departamento_imputacion else "-"
        else:
            # Si tiene MÁS de una -> Usamos su Área Habitual
            depto_mostrar = empleado.departamento.nombre if empleado.departamento else "-"

        lista_final.append({
            'nombre': empleado.nombre_completo,
            'departamento': depto_mostrar,
            'total_horas': suma_horas
        })

    # 3. Contexto
    fecha_actual = datetime.date.today()
    fecha_nota = f"Chajarí, {fecha_actual.day} de {fecha_actual.strftime('%B')} de {fecha_actual.year}"

    context = {
        'periodo': periodo,
        'registros': lista_final, # Pasamos la lista procesada
        'encabezado': encabezado,
        'fecha_nota': fecha_nota,
        'total_general': total_general
    }

    # 4. Generar PDF
    html_string = render_to_string('reportes/pdf_horas.html', context)
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'inline; filename="Reporte_{periodo.nombre}.pdf"'
    HTML(string=html_string, base_url=request.build_absolute_uri()).write_pdf(response)
    return response