
from django.urls import path
from . import views


urlpatterns = [

    # PÁGINA PRINCIPAL Y PRODUCTOS

    path(
        "",
        views.inicio,
        name="inicio"
    ),

    path(
        "productos/<slug:categoria>/",
        views.productos_categoria,
        name="productos_categoria"
    ),


    # REGISTRO Y ACCESO DE CLIENTES

    path(
        "registro/",
        views.registro_cliente,
        name="registro_cliente"
    ),

    path(
        "clientes/login/",
        views.login_cliente,
        name="login_cliente"
    ),

    path(
        "clientes/logout/",
        views.logout_cliente,
        name="logout_cliente"
    ),


    # PEDIDOS DE CLIENTES

    path(
        "clientes/pedidos/confirmar/",
        views.confirmar_pedido,
        name="confirmar_pedido"
    ),

    path(
        "clientes/mis-compras/",
        views.mis_compras,
        name="mis_compras"
    ),


    # PAGOS CON WEBPAY

    path(
        "clientes/pedidos/<int:pedido_id>/webpay/iniciar/",
        views.iniciar_pago_webpay,
        name="iniciar_pago_webpay"
    ),

    path(
        "clientes/webpay/retorno/",
        views.retorno_webpay,
        name="retorno_webpay"
    ),


    # PAGOS POR TRANSFERENCIA BANCARIA

    path(
        "clientes/pedidos/<int:pedido_id>/transferencia/",
        views.pago_transferencia,
        name="pago_transferencia"
    ),

    path(
        "clientes/pedidos/<int:pedido_id>/transferencia/comprobante/",
        views.subir_comprobante_transferencia,
        name="subir_comprobante_transferencia"
    ),


    # ACCESO AL PANEL OPERIA

    path(
        "operia/login/",
        views.login_operia,
        name="login_operia"
    ),

    path(
        "operia/logout/",
        views.logout_operia,
        name="logout_operia"
    ),

    path(
        "operia/panel/",
        views.panel_operia,
        name="panel_operia"
    ),


    # GESTIÓN DE PEDIDOS

    path(
        "operia/pedidos/",
        views.pedidos_operia,
        name="pedidos_operia"
    ),

    path(
        "operia/pedidos/<int:pedido_id>/",
        views.detalle_pedido,
        name="detalle_pedido"
    ),

    path(
        "operia/pedidos/<int:pedido_id>/estado/",
        views.actualizar_estado_pedido,
        name="actualizar_estado_pedido"
    ),

    path(
        "operia/pedidos/<int:pedido_id>/eliminar/",
        views.eliminar_pedido,
        name="eliminar_pedido"
    ),


    # GESTIÓN DE PAGOS Y COMPROBANTES

    path(
        "operia/pedidos/<int:pedido_id>/confirmar-transferencia/",
        views.confirmar_pago_transferencia,
        name="confirmar_pago_transferencia"
    ),

    # NUEVA RUTA: CONFIRMACIÓN DE PAGO EN EFECTIVO

    path(
        "operia/pedidos/<int:pedido_id>/confirmar-efectivo/",
        views.confirmar_pago_efectivo,
        name="confirmar_pago_efectivo"
    ),

    path(
        "operia/pedidos/<int:pedido_id>/comprobante/",
        views.descargar_comprobante_transferencia,
        name="descargar_comprobante_transferencia"
    ),


    # GESTIÓN DE PROVEEDORES

    path(
        "operia/proveedores/",
        views.proveedores_operia,
        name="proveedores_operia"
    ),


    # GESTIÓN DE INVENTARIO

    path(
        "operia/inventario/",
        views.inventario_operia,
        name="inventario_operia"
    ),

    path(
        "operia/inventario/movimiento/",
        views.registrar_movimiento_inventario,
        name="registrar_movimiento_inventario"
    ),

    path(
        "operia/inventario/editar/<int:insumo_id>/",
        views.editar_insumo,
        name="editar_insumo"
    ),

    path(
        "operia/inventario/estado/<int:insumo_id>/",
        views.cambiar_estado_insumo,
        name="cambiar_estado_insumo"
    ),


    # GESTIÓN DE VENTAS

    path(
        "operia/ventas/",
        views.ventas_operia,
        name="ventas_operia"
    ),


    # REPORTES

    path(
        "operia/reportes/",
        views.reportes_operia,
        name="reportes_operia"
    ),

]
