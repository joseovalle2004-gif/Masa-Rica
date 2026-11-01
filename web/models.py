from decimal import Decimal
from urllib.parse import quote
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q
class Pedido(models.Model):
    ORIGENES_PEDIDO = [
        ('web', 'Página web'),
        ('telefono', 'Pedido telefónico'),
    ]

    origen = models.CharField(
        max_length=20,
        choices=ORIGENES_PEDIDO,
        default='web'
    )

    ESTADOS = [
        ('pendiente', 'Pedido recibido'),
        ('preparacion', 'En preparación'),
        ('coccion', 'En cocción'),
        ('listo', 'Listo para retirar'),
        ('entregado', 'Retirado'),
        ('cancelado', 'Cancelado'),
    ]

    ETAPAS_PROGRESO = [
        'pendiente',
        'preparacion',
        'coccion',
        'listo',
        'entregado',
    ]

    PORCENTAJES_PROGRESO = {
        'pendiente': 20,
        'preparacion': 40,
        'coccion': 60,
        'listo': 80,
        'entregado': 100,
        'cancelado': 0,
    }

    SIGUIENTE_ESTADO = {
        'pendiente': 'preparacion',
        'preparacion': 'coccion',
        'coccion': 'listo',
        'listo': 'entregado',
    }

    TIEMPOS_PREPARACION = [
        (5, 10),
        (10, 15),
        (20, 20),
        (30, 30),
    ]
    METODOS_PAGO = [
        ('efectivo', 'Efectivo'),
        ('debito', 'Tarjeta de débito'),
        ('credito', 'Tarjeta de crédito'),
        ('transferencia', 'Transferencia bancaria'),
    ]
    ESTADOS_PAGO = [
        ('pendiente', 'Pendiente de pago'),
        ('en_verificacion', 'En verificación bancaria'),
        ('confirmado', 'Pago confirmado'),
    ]
    cliente_usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='pedidos_cliente'
    )

    nombre_cliente = models.CharField(
        max_length=100
    )

    telefono_cliente = models.CharField(
        max_length=20,
        blank=True
    )
    acepta_whatsapp = models.BooleanField(
        default=False,
        help_text=(
            'El cliente autorizó recibir avisos '
            'sobre su pedido por WhatsApp.'
        )
    )

    fecha_pedido = models.DateTimeField(
        auto_now_add=True
    )

    observaciones = models.TextField(
        blank=True
    )
    estado = models.CharField(
        max_length=20,
        choices=ESTADOS,
        default='pendiente'
    )
    metodo_pago = models.CharField(
        max_length=20,
        choices=METODOS_PAGO,
        default='efectivo'
    )

    estado_pago = models.CharField(
        max_length=20,
        choices=ESTADOS_PAGO,
        default='pendiente'
    )
    minutos_estimados = models.PositiveIntegerField(
        default=10,
        help_text='Tiempo estimado de preparación en minutos.'
    )
    @classmethod
    def calcular_minutos_estimados(cls, cantidad_empanadas):

        if cantidad_empanadas <= 0:
            return 10

        for cantidad_maxima, minutos in cls.TIEMPOS_PREPARACION:

            if cantidad_empanadas <= cantidad_maxima:
                return minutos

        bloques_adicionales = (
            cantidad_empanadas - 31
        ) // 10 + 1

        return 30 + bloques_adicionales * 10
    @property
    def porcentaje_progreso(self):

        return self.PORCENTAJES_PROGRESO.get(
            self.estado,
            0
        )
    @property
    def etapa_actual(self):

        return self.get_estado_display()
    @property
    def indice_etapa_actual(self):

        if self.estado == 'cancelado':
            return -1

        try:
            return self.ETAPAS_PROGRESO.index(
                self.estado
            )

        except ValueError:
            return -1
    @property
    def etapas_completadas(self):

        if self.estado == 'cancelado':
            return []

        indice_actual = self.indice_etapa_actual

        return self.ETAPAS_PROGRESO[
            :indice_actual + 1
        ]
    @property
    def siguiente_estado(self):

        return self.SIGUIENTE_ESTADO.get(
            self.estado
        )
    @property
    def puede_avanzar(self):

        return self.siguiente_estado is not None
    def avanzar_estado(self):

        siguiente = self.siguiente_estado

        if siguiente is None:
            return False

        self.estado = siguiente

        self.save(
            update_fields=['estado']
        )

        return True
    def puede_cambiar_a(self, nuevo_estado):

        if nuevo_estado == self.estado:
            return True

        return nuevo_estado == self.siguiente_estado
    def etapa_completada(self, etapa):

        return etapa in self.etapas_completadas
    @property
    def esta_listo_para_retirar(self):

        return self.estado == 'listo'
    @property
    def esta_entregado(self):

        return self.estado == 'entregado'

    @property
    def esta_cancelado(self):

        return self.estado == 'cancelado'

    @property
    def pago_confirmado(self):

        return self.estado_pago == 'confirmado'

    @property
    def pago_pendiente(self):

        return self.estado_pago == 'pendiente'

    @property
    def mensaje_whatsapp(self):

        nombre = self.nombre_cliente.strip()

        return (
            f"¡Hola, {nombre}!\n\n"
            f"Te escribimos de Masa Rica para informarte "
            f"que tu pedido N.º {self.pk} "
            f"ya está listo para retirar.\n\n"
            f"¡Muchas gracias por preferirnos!\n"
            f"Te esperamos en nuestro local."
        )

    @property
    def enlace_whatsapp(self):

        if self.estado != 'listo':
            return ''

        if not self.acepta_whatsapp:
            return ''

        if not self.telefono_cliente:
            return ''

        telefono = ''.join(
            caracter
            for caracter in self.telefono_cliente
            if caracter.isdigit()
        )

        if (
            len(telefono) == 9
            and telefono.startswith('9')
        ):
            telefono = '56' + telefono

        elif (
            len(telefono) == 10
            and telefono.startswith('09')
        ):
            telefono = '56' + telefono[1:]

        if not (
            len(telefono) == 11
            and telefono.startswith('569')
        ):
            return ''

        mensaje = quote(
            self.mensaje_whatsapp,
            safe=''
        )

        return (
            f"https://wa.me/{telefono}"
            f"?text={mensaje}"
        )
    def __str__(self):

        return (
            f"Pedido #{self.id} - "
            f"{self.nombre_cliente}"
        )
    class Meta:

        ordering = [
            '-fecha_pedido'
        ]

        verbose_name = 'Pedido'

        verbose_name_plural = 'Pedidos'

class Producto(models.Model):

    CATEGORIAS = [
        ('empanadas', 'Empanadas'),
        ('tradicionales', 'Comidas tradicionales'),
        ('sopaipillas', 'Sopaipillas'),
        ('bebidas', 'Bebidas'),
        ('especiales', 'Pedidos especiales'),
        ('humitas', 'Humitas'),
        ('pastel_choclo', 'Pastel de choclo'),
        ('sopaipillas_pasadas', 'Sopaipillas pasadas'),
        ('mini_empanadas', 'Mini empanadas'),
        ('mini_pizzas', 'Mini pizzas'),
        ('cocteles', 'Cócteles'),
        ('pavo_relleno', 'Pavo relleno'),
    ]
    TIPOS_VENTA = [
        ('diaria', 'Venta diaria'),
        ('encargo', 'Por encargo'),
    ]
    nombre = models.CharField(
        max_length=120
    )

    categoria = models.CharField(
        max_length=20,
        choices=CATEGORIAS
    )

    tipo_venta = models.CharField(
        max_length=20,
        choices=TIPOS_VENTA,
        default='diaria'
    )

    precio = models.PositiveIntegerField(
        help_text=(
            'Precio actual del producto '
            'en pesos chilenos.'
        )
    )

    disponible = models.BooleanField(
        default=True
    )
    def __str__(self):

        return self.nombre
    class Meta:

        ordering = [
            'categoria',
            'nombre'
        ]

        verbose_name = 'Producto'

        verbose_name_plural = 'Productos'
class DetallePedido(models.Model):
    pedido = models.ForeignKey(
        Pedido,
        on_delete=models.CASCADE,
        related_name='detalles'
    )
    producto = models.ForeignKey(
        Producto,
        on_delete=models.PROTECT
    )
    cantidad = models.PositiveIntegerField(
        default=1
    )


    precio_unitario = models.PositiveIntegerField(
        editable=False
    )
    def save(self, *args, **kwargs):

        if self._state.adding:

            self.precio_unitario = (
                self.producto.precio
            )

        super().save(
            *args,
            **kwargs
        )


    @property
    def subtotal(self):

        return (
            self.cantidad *
            self.precio_unitario
        )


    def __str__(self):

        return (
            f"{self.cantidad} x "
            f"{self.producto.nombre}"
        )


    class Meta:

        verbose_name = 'Detalle de pedido'

        verbose_name_plural = 'Detalles de pedidos'



def validar_rut_chileno(valor):

    rut = (
        valor.replace(".", "")
        .replace("-", "")
        .strip()
        .upper()
    )

    if (
        len(rut) < 2
        or not rut[:-1].isdigit()
        or rut[-1] not in "0123456789K"
    ):
        raise ValidationError(
            "Ingresa un RUT chileno válido."
        )

    numero = rut[:-1]
    digito = rut[-1]

    if not 1 <= len(numero) <= 8 or int(numero) == 0:
        raise ValidationError(
            "Ingresa un RUT chileno válido."
        )

    suma = 0
    multiplicador = 2

    for caracter in reversed(numero):

        suma += int(caracter) * multiplicador

        multiplicador += 1

        if multiplicador > 7:
            multiplicador = 2

    resultado = 11 - (suma % 11)

    if resultado == 11:
        esperado = "0"

    elif resultado == 10:
        esperado = "K"

    else:
        esperado = str(resultado)

    if digito != esperado:
        raise ValidationError(
            "El dígito verificador del RUT no es correcto."
        )



class ConfiguracionBancaria(models.Model):


    BANCOS = [
        ("bancoestado", "BancoEstado"),
        ("falabella", "Banco Falabella"),
    ]


    TIPOS_CUENTA = [
        ("cuentarut", "CuentaRUT"),
        ("vista", "Cuenta vista"),
        ("corriente", "Cuenta corriente"),
    ]


    banco = models.CharField(
        max_length=30,
        choices=BANCOS
    )

    tipo_cuenta = models.CharField(
        max_length=30,
        choices=TIPOS_CUENTA
    )

    titular = models.CharField(
        max_length=120
    )

    rut_titular = models.CharField(
        max_length=12,
        validators=[validar_rut_chileno]
    )

    numero_cuenta = models.CharField(
        max_length=30
    )

    correo = models.EmailField()


    activa = models.BooleanField(
        default=False,
        help_text=(
            "Solo una cuenta bancaria puede "
            "estar activa para recibir transferencias."
        )
    )

    fecha_actualizacion = models.DateTimeField(
        auto_now=True
    )


    def clean(self):

        super().clean()

        self.titular = (self.titular or "").strip()

        self.rut_titular = (
            (self.rut_titular or "")
            .replace(".", "")
            .replace("-", "")
            .strip()
            .upper()
        )

        self.numero_cuenta = (
            self.numero_cuenta or ""
        ).strip()

        if not self.titular:
            raise ValidationError({
                "titular": (
                    "Debes indicar el nombre del titular."
                )
            })

        if (
            self.banco == "bancoestado"
            and self.tipo_cuenta == "cuentarut"
        ):

            numero_rut = self.rut_titular[:-1]

            if not self.numero_cuenta.isdigit():
                raise ValidationError({
                    "numero_cuenta": (
                        "La CuentaRUT debe contener solo números."
                    )
                })

            elif (
                self.numero_cuenta.lstrip("0")
                != numero_rut.lstrip("0")
            ):
                raise ValidationError({
                    "numero_cuenta": (
                        "El número de CuentaRUT debe coincidir "
                        "con el RUT del titular sin "
                        "dígito verificador."
                    )
                })

        elif self.tipo_cuenta == "cuentarut":
            raise ValidationError({
                "tipo_cuenta": (
                    "CuentaRUT corresponde a BancoEstado."
                )
            })

        elif not self.numero_cuenta.isdigit():
            raise ValidationError({
                "numero_cuenta": (
                    "El número de cuenta debe contener solo números."
                )
            })

        if self.activa:

            otras_activas = (
                ConfiguracionBancaria.objects
                .filter(activa=True)
            )

            if self.pk:
                otras_activas = otras_activas.exclude(
                    pk=self.pk
                )

            if otras_activas.exists():
                raise ValidationError({
                    "activa": (
                        "Ya existe una cuenta bancaria activa. "
                        "Desactívala antes de activar otra."
                    )
                })


    def save(self, *args, **kwargs):

        self.full_clean()

        super().save(*args, **kwargs)


    def __str__(self):

        return (
            f"{self.get_banco_display()} - "
            f"{self.get_tipo_cuenta_display()}"
        )


    class Meta:

        verbose_name = 'Configuración bancaria'

        verbose_name_plural = 'Configuraciones bancarias'

        constraints = [
            models.UniqueConstraint(
                fields=['activa'],
                condition=Q(activa=True),
                name='unica_configuracion_bancaria_activa'
            )
        ]

    

class TransaccionWebpay(models.Model):

    pedido = models.ForeignKey(
        Pedido,
        on_delete=models.PROTECT,
        related_name="transacciones_webpay"
    )

    token = models.CharField(
        max_length=128,
        unique=True,
        null=True,
        blank=True
    )

    orden_compra = models.CharField(
        max_length=64,
        unique=True
    )

    monto = models.PositiveIntegerField()

    estado = models.CharField(
        max_length=20,
        default="iniciada",
        choices=[
            ("iniciada", "Iniciada"),
            ("aprobada", "Aprobada"),
            ("rechazada", "Rechazada"),
            ("anulada", "Anulada"),
            ("error", "Error"),
        ]
    )

    codigo_autorizacion = models.CharField(
        max_length=64,
        blank=True
    )

    fecha_creacion = models.DateTimeField(
        auto_now_add=True
    )

    fecha_actualizacion = models.DateTimeField(
        auto_now=True
    )

    def __str__(self):
        return (
            f"Webpay - Pedido #{self.pedido_id} "
            f"- {self.estado}"
        )

    class Meta:
        verbose_name = "Transacción Webpay"
        verbose_name_plural = "Transacciones Webpay"




def ruta_comprobante_transferencia(instancia, nombre_archivo):

    import uuid
    from pathlib import Path

    extension = Path(nombre_archivo).suffix.lower()

    nombre_seguro = f"{uuid.uuid4().hex}{extension}"

    return (
        f"comprobantes_transferencia/"
        f"pedido_{instancia.pedido_id}/"
        f"{nombre_seguro}"
    )


class ComprobanteTransferencia(models.Model):

    pedido = models.OneToOneField(
        Pedido,
        on_delete=models.CASCADE,
        related_name="comprobante_transferencia"
    )

    archivo = models.FileField(
        upload_to=ruta_comprobante_transferencia
    )

    fecha_subida = models.DateTimeField(
        auto_now_add=True
    )

    def __str__(self):
        return (
            f"Comprobante de transferencia "
            f"- Pedido #{self.pedido_id}"
        )

    class Meta:
        verbose_name = "Comprobante de transferencia"
        verbose_name_plural = "Comprobantes de transferencia"




class Insumo(models.Model):

    UNIDADES = [
        ("kg", "Kilogramos"),
        ("g", "Gramos"),
        ("l", "Litros"),
        ("ml", "Mililitros"),
        ("unidad", "Unidades"),
    ]

    nombre = models.CharField(
        max_length=120,
        unique=True
    )

    unidad_medida = models.CharField(
        max_length=20,
        choices=UNIDADES
    )

    stock_actual = models.DecimalField(
        max_digits=12,
        decimal_places=3,
        default=0
    )

    stock_minimo = models.DecimalField(
        max_digits=12,
        decimal_places=3,
        default=0
    )

    activo = models.BooleanField(
        default=True
    )

    fecha_creacion = models.DateTimeField(
        auto_now_add=True
    )


    def clean(self):

        super().clean()

        errores = {}

        # Validar que el stock mínimo no sea negativo
        if (
            self.stock_minimo is not None
            and self.stock_minimo < 0
        ):
            errores["stock_minimo"] = (
                "El stock mínimo no puede ser negativo."
            )

        # Validar que el stock actual no sea negativo
        if (
            self.stock_actual is not None
            and self.stock_actual < 0
        ):
            errores["stock_actual"] = (
                "El stock actual no puede ser negativo."
            )

        # Comprobar cambios de unidad en insumos existentes
        if self.pk:

            unidad_original = (
                type(self).objects
                .filter(pk=self.pk)
                .values_list("unidad_medida", flat=True)
                .first()
            )

            if (
                unidad_original is not None
                and self.unidad_medida != unidad_original
            ):

                if self.movimientos.exists():

                    errores["unidad_medida"] = (
                        "No puedes cambiar la unidad de medida "
                        "porque este insumo ya tiene movimientos "
                        "de inventario registrados."
                    )

        if errores:
            raise ValidationError(errores)


    def save(self, *args, **kwargs):

        self.full_clean()

        return super().save(*args, **kwargs)


    @property
    def stock_bajo(self):
        return self.stock_actual <= self.stock_minimo

    def __str__(self):
        return (
            f"{self.nombre} "
            f"({self.get_unidad_medida_display()})"
        )

    class Meta:
        ordering = ["nombre"]
        verbose_name = "Insumo"
        verbose_name_plural = "Insumos"




class MovimientoInventario(models.Model):

    TIPOS_MOVIMIENTO = [
        ("entrada", "Entrada"),
        ("salida", "Salida"),
    ]

    insumo = models.ForeignKey(
        Insumo,
        on_delete=models.PROTECT,
        related_name="movimientos"
    )

    tipo = models.CharField(
        max_length=10,
        choices=TIPOS_MOVIMIENTO
    )

    cantidad = models.DecimalField(
        max_digits=12,
        decimal_places=3
    )

    motivo = models.CharField(
        max_length=200
    )

    fecha = models.DateTimeField(
        auto_now_add=True
    )

    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )



    def clean(self):

        super().clean()

        # Validar que la cantidad sea mayor que cero.
        if self.cantidad is None or self.cantidad <= 0:

            raise ValidationError({
                "cantidad": "La cantidad debe ser mayor que cero."
            })

        # Validar que el ingrediente esté activo.
        if self.insumo_id:

            insumo = Insumo.objects.filter(
                pk=self.insumo_id
            ).first()

            if insumo is not None and not insumo.activo:

                raise ValidationError({
                    "insumo": (
                        "No puedes registrar movimientos "
                        "de un ingrediente desactivado."
                    )
                })

    def save(self, *args, **kwargs):

        from django.db import transaction

        # Los movimientos registrados no se pueden editar.
        if self.pk:

            raise ValidationError(
                "Los movimientos registrados no se pueden editar."
            )

        with transaction.atomic():

            # Obtener el insumo.
            insumo = Insumo.objects.select_for_update().get(
                pk=self.insumo_id
            )

            # Validar el movimiento.
            # La fecha se genera automáticamente al guardar.
            self.full_clean(exclude=["fecha"])

            # ENTRADA DE MERCADERÍA
            if self.tipo == "entrada":

                nuevo_stock = (
                    insumo.stock_actual + self.cantidad
                )

            # SALIDA DE MERCADERÍA
            elif self.tipo == "salida":

                nuevo_stock = (
                    insumo.stock_actual - self.cantidad
                )

                # Evitar stock negativo.
                if nuevo_stock < Decimal("0"):

                    raise ValidationError(
                        "No hay suficiente stock para esta salida."
                    )

            else:

                raise ValidationError(
                    "Tipo de movimiento no válido."
                )

            # Guardar el movimiento.
            super().save(*args, **kwargs)

            # Actualizar el stock del insumo.
            insumo.stock_actual = nuevo_stock

            insumo.save(
                update_fields=["stock_actual"]
            )

    def delete(self, *args, **kwargs):

        raise ValidationError(
            "Los movimientos no se pueden eliminar."
        )


    def __str__(self):

        return (
            f"{self.get_tipo_display()} - "
            f"{self.insumo.nombre} - {self.cantidad}"
        )

    class Meta:
        ordering = ["-fecha"]
        verbose_name = "Movimiento de inventario"
        verbose_name_plural = "Movimientos de inventario"


class Proveedor(models.Model):

    nombre = models.CharField(
        max_length=150,
        unique=True
    )

    rut = models.CharField(
        max_length=12,
        blank=True,
        validators=[validar_rut_chileno]
    )

    contacto = models.CharField(
        max_length=120,
        blank=True
    )

    telefono = models.CharField(
        max_length=20
    )

    correo = models.EmailField(
        blank=True
    )

    direccion = models.CharField(
        max_length=200,
        blank=True
    )

    observaciones = models.TextField(
        blank=True
    )

    activo = models.BooleanField(
        default=True
    )

    fecha_registro = models.DateTimeField(
        auto_now_add=True
    )

    def clean(self):

        super().clean()

        self.nombre = " ".join(
            (self.nombre or "").split()
        )

        self.telefono = (self.telefono or "").strip()

        if not self.nombre:
            raise ValidationError({
                "nombre": "Debes ingresar el nombre del proveedor."
            })

        if not self.telefono:
            raise ValidationError({
                "telefono": "Debes ingresar un teléfono."
            })

        if self.rut:
            self.rut = (
                self.rut.replace(".", "")
                .replace("-", "")
                .strip()
                .upper()
            )

    def save(self, *args, **kwargs):

        self.full_clean()
        return super().save(*args, **kwargs)

    def __str__(self):

        return self.nombre

    class Meta:

        ordering = ["nombre"]

        verbose_name = "Proveedor"
        verbose_name_plural = "Proveedores"


class OrdenCompraProveedor(models.Model):

    TIPOS = [
        ("orden", "Orden de compra"),
        ("directa", "Recepción directa"),
    ]

    ESTADOS = [
        ("pendiente", "Pendiente"),
        ("recibida", "Recibida"),
        ("cancelada", "Cancelada"),
    ]

    proveedor = models.ForeignKey(
        Proveedor,
        on_delete=models.PROTECT,
        related_name="ordenes"
    )

    tipo = models.CharField(
        max_length=15,
        choices=TIPOS,
        default="orden"
    )

    estado = models.CharField(
        max_length=15,
        choices=ESTADOS,
        default="pendiente"
    )

    fecha_creacion = models.DateTimeField(
        auto_now_add=True
    )

    fecha_recepcion = models.DateTimeField(
        null=True,
        blank=True
    )

    observaciones = models.TextField(
        blank=True
    )

    usuario_creacion = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="ordenes_proveedor_creadas"
    )

    usuario_recepcion = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="ordenes_proveedor_recibidas"
    )

    @property
    def total_estimado(self):

        return sum(
            detalle.subtotal
            for detalle in self.detalles.all()
        )

    def clean(self):

        super().clean()

        if self.tipo == "directa" and self.estado == "cancelada":
            raise ValidationError({
                "estado": (
                    "Una recepción directa no debe cancelarse "
                    "después de registrarse como recibida."
                )
            })

        if self.estado == "recibida" and not self.fecha_recepcion:
            raise ValidationError({
                "fecha_recepcion": (
                    "Una orden recibida necesita fecha de recepción."
                )
            })

        if self.estado != "recibida" and self.fecha_recepcion:
            raise ValidationError({
                "fecha_recepcion": (
                    "Solo las órdenes recibidas pueden tener "
                    "fecha de recepción."
                )
            })

    def __str__(self):

        return (
            f"Orden #{self.pk or 'Nueva'} - "
            f"{self.proveedor.nombre}"
        )

    class Meta:

        ordering = ["-fecha_creacion", "-id"]

        verbose_name = "Orden de compra a proveedor"
        verbose_name_plural = "Órdenes de compra a proveedores"


class DetalleOrdenProveedor(models.Model):

    orden = models.ForeignKey(
        OrdenCompraProveedor,
        on_delete=models.CASCADE,
        related_name="detalles"
    )

    insumo = models.ForeignKey(
        Insumo,
        on_delete=models.PROTECT,
        related_name="detalles_compra"
    )

    cantidad = models.DecimalField(
        max_digits=12,
        decimal_places=3
    )

    precio_unitario = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0
    )

    @property
    def subtotal(self):

        return self.cantidad * self.precio_unitario

    def clean(self):

        super().clean()

        if self.cantidad is None or self.cantidad <= 0:
            raise ValidationError({
                "cantidad": "La cantidad debe ser mayor que cero."
            })

        if self.precio_unitario is None or self.precio_unitario < 0:
            raise ValidationError({
                "precio_unitario": (
                    "El precio unitario no puede ser negativo."
                )
            })

        if self.insumo_id and not self.insumo.activo:
            raise ValidationError({
                "insumo": "No puedes comprar un insumo desactivado."
            })

        if self.orden_id and self.orden.estado != "pendiente":
            raise ValidationError({
                "orden": (
                    "No puedes modificar los productos de una "
                    "orden que ya fue recibida o cancelada."
                )
            })

    def save(self, *args, **kwargs):

        self.full_clean()
        return super().save(*args, **kwargs)

    def __str__(self):

        return (
            f"{self.insumo.nombre} - "
            f"{self.cantidad} {self.insumo.unidad_medida}"
        )

    class Meta:

        ordering = ["id"]

        verbose_name = "Detalle de orden a proveedor"
        verbose_name_plural = "Detalles de órdenes a proveedores"

        constraints = [
            models.UniqueConstraint(
                fields=["orden", "insumo"],
                name="insumo_unico_por_orden_proveedor"
            )
        ]


class IngredienteReceta(models.Model):

    producto = models.ForeignKey(
        Producto,
        on_delete=models.CASCADE,
        related_name="ingredientes_receta"
    )

    insumo = models.ForeignKey(
        Insumo,
        on_delete=models.PROTECT,
        related_name="recetas"
    )

    cantidad = models.DecimalField(
        max_digits=12,
        decimal_places=3,
        help_text="Cantidad utilizada para preparar una unidad del producto."
    )

    def clean(self):
        super().clean()

        if self.cantidad is None or self.cantidad <= 0:
            raise ValidationError({
                "cantidad": "La cantidad debe ser mayor que cero."
            })

        if self.insumo_id and not self.insumo.activo:
            raise ValidationError({
                "insumo": "No puedes utilizar un insumo desactivado."
            })

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)

    def __str__(self):
        return (
            f"{self.producto.nombre} - "
            f"{self.insumo.nombre}: {self.cantidad}"
        )

    class Meta:
        ordering = ["producto__nombre", "insumo__nombre"]
        verbose_name = "Ingrediente de receta"
        verbose_name_plural = "Ingredientes de recetas"

        constraints = [
            models.UniqueConstraint(
                fields=["producto", "insumo"],
                name="ingrediente_unico_por_producto"
            ),
            models.CheckConstraint(
                condition=Q(cantidad__gt=0),
                name="cantidad_receta_positiva"
            )
        ]


class ConsumoInventarioPedido(models.Model):

    pedido = models.OneToOneField(
        Pedido,
        on_delete=models.PROTECT,
        related_name="consumo_inventario"
    )

    fecha = models.DateTimeField(
        auto_now_add=True
    )

    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    def __str__(self):
        return f"Inventario descontado - Pedido #{self.pedido_id}"

    class Meta:
        verbose_name = "Consumo de inventario por pedido"
        verbose_name_plural = "Consumos de inventario por pedidos"
