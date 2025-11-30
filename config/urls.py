from django.contrib import admin
from django.urls import path
from calculos import views  # <--- IMPORTAR TUS VISTAS

urlpatterns = [
    path('admin/', admin.site.urls),
    
    # RUTA NUEVA PARA EL REPORTE
    # Recibe el ID del período y el nombre del destinatario (andrea/edith)
    path('reporte/pdf/<int:periodo_id>/<str:destinatario>/', views.generar_reporte_pdf, name='reporte_pdf'),
]