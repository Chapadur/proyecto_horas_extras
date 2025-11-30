from django.db import models
from django.core.exceptions import ValidationError

class Secretaria(models.Model):
    nombre = models.CharField(max_length=100, unique=True, verbose_name="Nombre de la Secretaría")
    def __str__(self): return self.nombre
    class Meta: verbose_name = "Secretaría"; verbose_name_plural = "Secretarías"; ordering = ['nombre']

class Departamento(models.Model):
    nombre = models.CharField(max_length=100, unique=True, verbose_name="Nombre del Departamento")
    secretaria = models.ForeignKey(Secretaria, on_delete=models.SET_NULL, verbose_name="Secretaría", null=True, blank=True)
    def __str__(self): return f"{self.nombre} ({self.secretaria.nombre})" if self.secretaria else self.nombre
    class Meta: verbose_name = "Departamento"; verbose_name_plural = "Departamentos"; ordering = ['nombre']

class Periodo(models.Model):
    nombre = models.CharField(max_length=100, verbose_name="Nombre (ej: Período 01)")
    fecha_inicio = models.DateField(verbose_name="Fecha Inicio")
    fecha_fin = models.DateField(verbose_name="Fecha Fin")
    activo = models.BooleanField(default=True, verbose_name="¿Activo? (Período Actual)")
    cerrado = models.BooleanField(default=False, verbose_name="¿Cerrado? (Bloquea ediciones)")
    
    def clean(self):
        if self.activo: Periodo.objects.filter(activo=True).exclude(pk=self.pk).update(activo=False)
    def save(self, *args, **kwargs): self.clean(); super().save(*args, **kwargs)
    def __str__(self): return f"{self.nombre} ({'🔒 CERRADO' if self.cerrado else '🟢 ABIERTO'})"
    class Meta: verbose_name = "Período"; verbose_name_plural = "Períodos"; ordering = ['-fecha_inicio']

class Empleado(models.Model):
    nombre_completo = models.CharField(max_length=200, verbose_name="Nombre Completo")
    legajo = models.CharField(max_length=20, unique=True, verbose_name="Número de Legajo")
    departamento = models.ForeignKey(Departamento, on_delete=models.SET_NULL, verbose_name="Departamento Habitual", null=True, blank=True)
    fecha_ingreso = models.DateField(auto_now_add=True, verbose_name="Fecha de Ingreso")
    def __str__(self): return f"{self.nombre_completo} ({self.departamento.nombre if self.departamento else 'Sin Área'})"
    class Meta: verbose_name = "Empleado"; verbose_name_plural = "Empleados"; ordering = ['nombre_completo']

class RegistroHora(models.Model):
    periodo = models.ForeignKey(Periodo, on_delete=models.CASCADE, verbose_name="Período", null=True, blank=True)
    empleado = models.ForeignKey(Empleado, on_delete=models.CASCADE, verbose_name="Empleado")
    departamento_imputacion = models.ForeignKey(Departamento, on_delete=models.CASCADE, verbose_name="Departamento (Imputación)", null=True, blank=True)
    cantidad_horas = models.DecimalField(max_digits=4, decimal_places=1, verbose_name="Cantidad de Horas")
    
    # --- CAMPO PARA VALIDAR EXCESO ---
    confirmar_exceso = models.BooleanField(default=False, verbose_name="Confirmar >180hs", help_text="Marque si carga más de 180hs.")

    def clean(self):
        if self.periodo and self.periodo.cerrado:
            raise ValidationError("⛔ ERROR: Este período está CERRADO.")
        
        # VALIDACIÓN INTELIGENTE:
        if self.cantidad_horas and self.cantidad_horas > 180 and not self.confirmar_exceso:
            raise ValidationError({
                'cantidad_horas': "⚠️ ALERTA: Valor alto.",
                'confirmar_exceso': "Debe marcar esta casilla para confirmar que cargar más de 180hs es correcto."
            })
        super().clean()

    def save(self, *args, **kwargs):
        if not self.departamento_imputacion_id and self.empleado.departamento:
            self.departamento_imputacion = self.empleado.departamento
        if not self.periodo:
            p_activo = Periodo.objects.filter(activo=True).first()
            if p_activo: self.periodo = p_activo
        self.full_clean()
        super().save(*args, **kwargs)
        
    def delete(self, *args, **kwargs):
        if self.periodo and self.periodo.cerrado: raise ValidationError("⛔ ERROR: Período CERRADO.")
        super().delete(*args, **kwargs)
    
    def __str__(self): return f"{self.empleado} - {self.cantidad_horas}hs"
    class Meta: verbose_name = "Registro de Hora"; verbose_name_plural = "Registros de Horas"; ordering = ['periodo', 'empleado']