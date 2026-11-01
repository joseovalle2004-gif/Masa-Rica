
from django.contrib import admin

from .models import (
    Pedido,
    Producto,
    DetallePedido,
    ConfiguracionBancaria,
    IngredienteReceta,
)

class DetallePedidoInline(admin.TabularInline):

    model = DetallePedido

    extra = 1

    fields = (
        'producto',
        'cantidad',
        'mostrar_precio',
        'mostrar_subtotal',
    )

    readonly_fields = (
        'mostrar_precio',
        'mostrar_subtotal',
    )

    @admin.display(description='Precio unitario')
    def mostrar_precio(self, obj):

        if obj.pk:
            return f"${obj.precio_unitario:,}".replace(',', '.')

        return 'Se asignará al guardar'

    @admin.display(description='Subtotal')
    def mostrar_subtotal(self, obj):

        if obj.pk:
            return f"${obj.subtotal:,}".replace(',', '.')

        return 'Se calculará al guardar'



@admin.register(Pedido)
class PedidoAdmin(admin.ModelAdmin):

    list_display = (
        'id',
        'nombre_cliente',
        'telefono_cliente',
        'origen',
        'estado',
        'acepta_whatsapp',
        'mostrar_total',
    )

    list_filter = (
        'estado',
        'origen',
        'acepta_whatsapp',
    )

    search_fields = (
        'nombre_cliente',
        'telefono_cliente',
    )

    ordering = (
        '-fecha_pedido',
    )

    fieldsets = (
        (
            'Información del cliente',
            {
                'fields': (
                    'cliente_usuario',
                    'nombre_cliente',
                    'telefono_cliente',
                    'origen',
                )
            }
        ),
        (
            'Avisos por WhatsApp',
            {
                'fields': (
                    'acepta_whatsapp',
                ),
                'description': (
                    'Activa esta opción únicamente cuando '
                    'el cliente haya autorizado recibir '
                    'avisos de su pedido por WhatsApp.'
                ),
            }
        ),
        (
            'Estado del pedido',
            {
                'fields': (
                    'estado',
                    'minutos_estimados',
                    'observaciones',
                )
            }
        ),
        (
            'Información del pago',
            {
                'fields': (
                    'metodo_pago',
                    'estado_pago',
                )
            }
        ),
    )

    # Permite administrar los productos de cada pedido.
    inlines = [
        DetallePedidoInline
    ]

    @admin.display(description='Total del pedido')
    def mostrar_total(self, obj):

        total = sum(
            detalle.subtotal
            for detalle in obj.detalles.all()
        )

        return f"${total:,}".replace(',', '.')



@admin.register(Producto)
class ProductoAdmin(admin.ModelAdmin):

    list_display = (
        'id',
        'nombre',
        'categoria',
        'tipo_venta',
        'precio',
        'disponible',
    )

    list_filter = (
        'categoria',
        'tipo_venta',
        'disponible',
    )

    search_fields = (
        'nombre',
    )

    list_editable = (
        'precio',
        'disponible',
    )

    ordering = (
        'categoria',
        'nombre',
    )



@admin.register(ConfiguracionBancaria)
class ConfiguracionBancariaAdmin(admin.ModelAdmin):


    list_display = (
        'id',
        'banco',
        'tipo_cuenta',
        'titular',
        'mostrar_cuenta',
        'activa',
        'fecha_actualizacion',
    )


    list_filter = (
        'banco',
        'tipo_cuenta',
        'activa',
    )


    search_fields = (
        'titular',
        'rut_titular',
    )


    ordering = (
        '-fecha_actualizacion',
    )


    readonly_fields = (
        'fecha_actualizacion',
    )


    fieldsets = (
        (
            'Información bancaria',
            {
                'fields': (
                    'banco',
                    'tipo_cuenta',
                    'titular',
                    'rut_titular',
                    'numero_cuenta',
                    'correo',
                ),
                'description': (
                    'Registra los datos reales de la cuenta '
                    'que recibirá las transferencias '
                    'de los clientes de Masa Rica.'
                ),
            }
        ),
        (
            'Estado de la cuenta bancaria',
            {
                'fields': (
                    'activa',
                    'fecha_actualizacion',
                ),
                'description': (
                    'Solo puede existir una cuenta bancaria '
                    'activa. Verifica todos los datos antes '
                    'de habilitarla para recibir transferencias.'
                ),
            }
        ),
    )


    @admin.display(description='Número de cuenta')
    def mostrar_cuenta(self, obj):

        numero = obj.numero_cuenta

        if not numero:
            return 'Sin número'

        if len(numero) <= 4:
            return '****'

        return '****' + numero[-4:]


    # Solo los superusuarios pueden acceder a este módulo.

    def has_module_permission(self, request):

        return (
            request.user.is_authenticated
            and request.user.is_active
            and request.user.is_superuser
        )

    def has_view_permission(self, request, obj=None):

        return (
            request.user.is_authenticated
            and request.user.is_active
            and request.user.is_superuser
        )

    def has_add_permission(self, request):

        return (
            request.user.is_authenticated
            and request.user.is_active
            and request.user.is_superuser
        )

    def has_change_permission(self, request, obj=None):

        return (
            request.user.is_authenticated
            and request.user.is_active
            and request.user.is_superuser
        )

    def has_delete_permission(self, request, obj=None):

        return (
            request.user.is_authenticated
            and request.user.is_active
            and request.user.is_superuser
        )

@admin.register(IngredienteReceta)
class IngredienteRecetaAdmin(admin.ModelAdmin):
    list_display = (
        "producto",
        "insumo",
        "cantidad",
    )

    list_filter = (
        "producto",
        "insumo",
    )

    search_fields = (
        "producto__nombre",
        "insumo__nombre",
    )