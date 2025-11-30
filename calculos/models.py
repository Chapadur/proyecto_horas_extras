from django.db import models
from django.core.exceptions import ValidationError

# --- MODELO DE PERÍODOS ---
class Periodo(models.Model):
    nombre = models.CharField(max_length=100, verbose_name="Nombre (ej: Período 01)")
    fecha_inicio = models.DateField(verbose_name="Fecha Inicio")
    fecha_fin = models.DateField(verbose_name="Fecha Fin")
    
    # CAMPO RESTAURADO: ACTIVO
    # Indica que este es el período de trabajo actual
    activo = models.BooleanField(default=True, verbose_name="¿Activo? (Período Actual)")

    # CAMPO DE SEGURIDAD: CERRADO
    # Si está marcado, bloquea ediciones
    cerrado = models.BooleanField(default=False, verbose_name="¿Cerrado? (Bloquea ediciones)")

    def __str__(self):
        estado = "🔒 CERRADO" if self.cerrado else "🟢 ABIERTO"
        es_activo = " [ACTUAL]" if self.activo else ""
        return f"{self.nombre} ({estado}){es_activo}"

    class Meta:
        verbose_name = "Período"
        verbose_name_plural = "Períodos"
        ordering = ['-fecha_inicio']


# --- MODELO EMPLEADOS ---
class Empleado(models.Model):
    nombre_completo = models.CharField(max_length=200, verbose_name="Nombre Completo")
    legajo = models.CharField(max_length=20, unique=True, verbose_name="Número de Legajo")
    cargo = models.CharField(max_length=100, verbose_name="Departamento / Área", blank=True, null=True)
    fecha_ingreso = models.DateField(auto_now_add=True, verbose_name="Fecha de Ingreso")

    def __str__(self):
        return f"{self.nombre_completo} ({self.legajo})"

    class Meta:
        verbose_name = "Empleado"
        verbose_name_plural = "Empleados"
        ordering = ['nombre_completo']


# --- MODELO HORAS EXTRAS ---
class RegistroHora(models.Model):
    periodo = models.ForeignKey(Periodo, on_delete=models.CASCADE, verbose_name="Período", null=True, blank=True)
    empleado = models.ForeignKey(Empleado, on_delete=models.CASCADE, verbose_name="Empleado")
    fecha = models.DateField(verbose_name="Fecha exacta")
    cantidad_horas = models.DecimalField(max_digits=4, decimal_places=1, verbose_name="Cantidad de Horas")
    motivo = models.TextField(verbose_name="Motivo / Descripción", blank=True, null=True)
    
    APROBADO = 'AP'
    PENDIENTE = 'PE'
    RECHAZADO = 'RE'
    
    ESTADOS = [
        (PENDIENTE, 'Pendiente'),
        (APROBADO, 'Aprobado'),
        (RECHAZADO, 'Rechazado'),
    ]
    
    estado = models.CharField(max_length=2, choices=ESTADOS, default=PENDIENTE, verbose_name="Estado")

    # --- REGLA DE SEGURIDAD ---
    def clean(self):
        # 1. Validar si el período está CERRADO
        if self.periodo and self.periodo.cerrado:
            raise ValidationError("⛔ ERROR: Este período está CERRADO. No se pueden hacer cambios.")
        
        # Opcional: Podríamos validar también que solo se cargue en el período ACTIVO,
        # pero por ahora solo dejamos el bloqueo de seguridad.
        
        super().clean()

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)
        
    def delete(self, *args, **kwargs):
        if self.periodo and self.periodo.cerrado:
            raise ValidationError("⛔ ERROR: No puedes borrar registros de un período CERRADO.")
        super().delete(*args, **kwargs)

    def __str__(self):
        return f"{self.empleado} - {self.cantidad_horas}hs ({self.periodo})"

    class Meta:
        verbose_name = "Registro de Hora"
        verbose_name_plural = "Registros de Horas"
        ordering = ['-fecha']