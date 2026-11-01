
import json
import logging
import re
import uuid

from datetime import date, timedelta
from decimal import Decimal
from functools import wraps
from io import BytesIO
from pathlib import Path
from xml.sax.saxutils import escape

from django.conf import settings
from django.contrib import messages

from django.contrib.auth import (
    authenticate,
    get_user_model,
    login,
    logout,
)

from django.contrib.auth.decorators import (
    login_required,
    user_passes_test,
)
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError

from django.core.mail import (
    EmailMessage,
    send_mail,
)

from django.core.paginator import Paginator
from django.db import IntegrityError, transaction

from django.db.models import (
    Count,
    DecimalField,
    ExpressionWrapper,
    F,
    IntegerField,
    Q,
    Sum,
)

from django.db.models.functions import TruncDate

from django.http import (
    FileResponse,
    Http404,
    HttpResponseForbidden,
    JsonResponse,
)

from django.shortcuts import (
    get_object_or_404,
    redirect,
    render,
)

from django.urls import reverse
from django.utils import timezone

from django.views.decorators.csrf import (
    csrf_exempt,
    ensure_csrf_cookie,
)

from django.views.decorators.http import (
    require_http_methods,
    require_POST,
)

from .models import (
    ComprobanteTransferencia,
    ConfiguracionBancaria,
    ConsumoInventarioPedido,
    DetallePedido,
    DetalleOrdenProveedor,
    IngredienteReceta,
    Insumo,
    MovimientoInventario,
    OrdenCompraProveedor,
    Pedido,
    Producto,
    Proveedor,
    TransaccionWebpay,
)

from .forms import (
    DetalleOrdenProveedorForm,
    InsumoForm,
    MovimientoInventarioForm,
    OrdenCompraProveedorForm,
    ProveedorForm,
)

from transbank.common.integration_api_keys import (
    IntegrationApiKeys,
)

from transbank.common.integration_commerce_codes import (
    IntegrationCommerceCodes,
)

from transbank.common.integration_type import (
    IntegrationType,
)

from transbank.common.options import WebpayOptions

from transbank.webpay.webpay_plus.transaction import (
    Transaction,
)

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet

from reportlab.platypus import (
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)


logger = logging.getLogger(__name__)

MAX_CANTIDAD_PRODUCTO = 1000
MAX_OBSERVACIONES = 1000
DIAS_PARA_ELIMINAR = 30

PATRON_NOMBRE = re.compile(
    r"^[^\W\d_]+(?:[ '-][^\W\d_]+)*$",
    re.UNICODE,
)

PATRON_TELEFONO = re.compile(
    r"^(?:\+56)?[2-9]\d{8}$"
)

def obtener_transaccion_webpay():
    opciones = WebpayOptions(
        IntegrationCommerceCodes.WEBPAY_PLUS,
        IntegrationApiKeys.WEBPAY,
        IntegrationType.TEST
    )

    return Transaction(opciones)

@login_required(login_url="login_cliente")
@require_POST
def iniciar_pago_webpay(request, pedido_id):

    if request.user.is_staff:
        return HttpResponseForbidden(
            "Esta sección es exclusiva para clientes."
        )

    pedido = get_object_or_404(
        Pedido,
        pk=pedido_id,
        cliente_usuario=request.user,
        metodo_pago__in=["debito", "credito"]
    )

    if pedido.estado == "cancelado":
        messages.error(
            request,
            "No puedes pagar un pedido cancelado."
        )
        return redirect("mis_compras")

    if pedido.estado_pago == "confirmado":
        messages.info(
            request,
            "Este pedido ya se encuentra pagado."
        )
        return redirect("mis_compras")

    monto = calcular_total_pedido(pedido)

    if (
        not isinstance(monto, int)
        or isinstance(monto, bool)
        or monto <= 0
    ):
        messages.error(
            request,
            "El monto del pedido no es válido."
        )
        return redirect("mis_compras")

    orden_compra = f"OP-{pedido.id}-{uuid.uuid4().hex[:16]}"

    transaccion_webpay = TransaccionWebpay.objects.create(
        pedido=pedido,
        orden_compra=orden_compra,
        monto=monto,
        estado="iniciada"
    )

    url_retorno = request.build_absolute_uri(
        reverse("retorno_webpay")
    )

    try:
        respuesta = obtener_transaccion_webpay().create(
            buy_order=orden_compra,
            session_id=str(request.user.pk),
            amount=monto,
            return_url=url_retorno
        )

        token = respuesta["token"]
        url_webpay = respuesta["url"]

        if not token or not url_webpay:
            raise ValueError(
                "Transbank no devolvió los datos esperados."
            )

        transaccion_webpay.token = token
        transaccion_webpay.save(
            update_fields=["token", "fecha_actualizacion"]
        )

    except Exception:
        logger.exception(
            "Error al iniciar Webpay para pedido #%s",
            pedido.id
        )

        transaccion_webpay.estado = "error"
        transaccion_webpay.save(
            update_fields=["estado", "fecha_actualizacion"]
        )

        messages.error(
            request,
            "No pudimos conectar con Webpay. "
            "Intenta nuevamente."
        )
        return redirect("mis_compras")

    return render(
        request,
        "web/redireccion_webpay.html",
        {
            "url_webpay": url_webpay,
            "token": token,
        }
    )

@csrf_exempt
@require_http_methods(["GET", "POST"])

def generar_comprobante_webpay(pedido, transaccion_webpay):

    buffer = BytesIO()

    documento = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=45,
        leftMargin=45,
        topMargin=45,
        bottomMargin=45,
    )

    estilos = getSampleStyleSheet()
    elementos = []

    def limpiar(valor):
        return escape(str(valor))

    elementos.append(
        Paragraph(
            "OPERIA MASA RICA",
            estilos["Title"]
        )
    )

    elementos.append(
        Paragraph(
            "Comprobante de compra - Webpay Plus",
            estilos["Heading2"]
        )
    )

    elementos.append(Spacer(1, 18))

    datos = [
        ("Número de pedido", f"#{pedido.id}"),
        ("Estado del pago", "APROBADO"),
        (
            "Monto pagado",
            f"${transaccion_webpay.monto:,}".replace(",", ".")
        ),
        ("Orden de compra", transaccion_webpay.orden_compra),
        (
            "Código de autorización",
            transaccion_webpay.codigo_autorizacion or "No informado"
        ),
        (
            "Fecha del comprobante",
            timezone.localtime().strftime("%d/%m/%Y %H:%M")
        ),
        ("Medio de pago", "Tarjeta mediante Webpay Plus"),
    ]

    tabla_datos = Table(
        [
            [
                Paragraph(limpiar(etiqueta), estilos["BodyText"]),
                Paragraph(limpiar(valor), estilos["BodyText"]),
            ]
            for etiqueta, valor in datos
        ],
        colWidths=[170, 320],
        hAlign="LEFT",
    )

    tabla_datos.setStyle(
        TableStyle([
            (
                "BACKGROUND",
                (0, 0),
                (0, -1),
                colors.HexColor("#F7EFE7")
            ),
            ("TOPPADDING", (0, 0), (-1, -1), 9),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 9),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            (
                "LINEBELOW",
                (0, 0),
                (-1, -1),
                0.4,
                colors.lightgrey
            ),
        ])
    )

    elementos.append(tabla_datos)
    elementos.append(Spacer(1, 22))

    elementos.append(
        Paragraph(
            "Detalle de productos",
            estilos["Heading2"]
        )
    )

    filas = [
        ["Producto", "Cantidad", "Subtotal"]
    ]

    for detalle in pedido.detalles.select_related("producto").all():

        filas.append([
            Paragraph(
                limpiar(detalle.producto.nombre),
                estilos["BodyText"]
            ),
            str(detalle.cantidad),
            f"${detalle.subtotal:,}".replace(",", "."),
        ])

    tabla_productos = Table(
        filas,
        colWidths=[290, 80, 120],
        repeatRows=1,
    )

    tabla_productos.setStyle(
        TableStyle([
            (
                "BACKGROUND",
                (0, 0),
                (-1, 0),
                colors.HexColor("#8C2424")
            ),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("TOPPADDING", (0, 0), (-1, -1), 9),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 9),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            (
                "LINEBELOW",
                (0, 1),
                (-1, -1),
                0.4,
                colors.lightgrey
            ),
        ])
    )

    elementos.append(tabla_productos)
    elementos.append(Spacer(1, 22))

    elementos.append(
        Paragraph(
            "Documento generado automáticamente por "
            "Operia Masa Rica a partir de un pago "
            "autorizado mediante Webpay Plus. "
            "Este comprobante no reemplaza una boleta "
            "o factura tributaria.",
            estilos["BodyText"]
        )
    )

    documento.build(elementos)

    contenido_pdf = buffer.getvalue()
    buffer.close()

    return contenido_pdf

def generar_comprobante_webpay(pedido, transaccion_webpay):

    buffer = BytesIO()

    documento = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=45,
        leftMargin=45,
        topMargin=45,
        bottomMargin=45,
    )

    estilos = getSampleStyleSheet()
    elementos = []

    def limpiar(valor):
        return escape(str(valor))

    def formato_pesos(valor):
        return f"${valor:,}".replace(",", ".")

    elementos.append(
        Paragraph("OPERIA MASA RICA", estilos["Title"])
    )

    elementos.append(
        Paragraph(
            "Comprobante de compra - Webpay Plus",
            estilos["Heading2"]
        )
    )

    elementos.append(Spacer(1, 18))

    datos = [
        ("Número de pedido", f"#{pedido.id}"),
        ("Estado del pago", "APROBADO"),
        ("Monto pagado", formato_pesos(transaccion_webpay.monto)),
        ("Orden de compra", transaccion_webpay.orden_compra),
        (
            "Código de autorización",
            transaccion_webpay.codigo_autorizacion or "No informado"
        ),
        (
            "Fecha de emisión",
            timezone.localtime().strftime("%d/%m/%Y %H:%M")
        ),
        ("Medio de pago", "Tarjeta mediante Webpay Plus"),
    ]

    tabla_datos = Table(
        [
            [
                Paragraph(limpiar(etiqueta), estilos["BodyText"]),
                Paragraph(limpiar(valor), estilos["BodyText"]),
            ]
            for etiqueta, valor in datos
        ],
        colWidths=[170, 320],
        hAlign="LEFT",
    )

    tabla_datos.setStyle(
        TableStyle([
            ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#F7EFE7")),
            ("TOPPADDING", (0, 0), (-1, -1), 9),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 9),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LINEBELOW", (0, 0), (-1, -1), 0.4, colors.lightgrey),
        ])
    )

    elementos.append(tabla_datos)
    elementos.append(Spacer(1, 22))

    elementos.append(
        Paragraph("Detalle de productos", estilos["Heading2"])
    )

    filas = [
        ["Producto", "Cantidad", "Subtotal"]
    ]

    for detalle in pedido.detalles.select_related("producto").all():

        filas.append([
            Paragraph(
                limpiar(detalle.producto.nombre),
                estilos["BodyText"]
            ),
            str(detalle.cantidad),
            formato_pesos(detalle.subtotal),
        ])

    tabla_productos = Table(
        filas,
        colWidths=[290, 80, 120],
        repeatRows=1,
    )

    tabla_productos.setStyle(
        TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#8C2424")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("TOPPADDING", (0, 0), (-1, -1), 9),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 9),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LINEBELOW", (0, 1), (-1, -1), 0.4, colors.lightgrey),
        ])
    )

    elementos.append(tabla_productos)
    elementos.append(Spacer(1, 22))

    elementos.append(
        Paragraph(
            "Este comprobante fue generado automáticamente "
            "por Operia Masa Rica a partir de una transacción "
            "autorizada mediante Webpay Plus. "
            "No reemplaza una boleta o factura tributaria "
            "ni constituye un documento emitido por Transbank.",
            estilos["BodyText"]
        )
    )

    documento.build(elementos)

    contenido_pdf = buffer.getvalue()
    buffer.close()

    return contenido_pdf

def enviar_correo_pago_webpay(pedido_id, transaccion_id):

    try:
        transaccion_webpay = (
            TransaccionWebpay.objects
            .select_related("pedido")
            .get(
                pk=transaccion_id,
                pedido_id=pedido_id,
                estado="aprobada",
                pedido__estado_pago="confirmado",
            )
        )

        pedido = transaccion_webpay.pedido

        # Utilizamos el mismo correo que ya recibe
        # las notificaciones de nuevos pedidos.
        destinatario = getattr(
            settings,
            "MASA_RICA_PEDIDOS_EMAIL",
            ""
        )

        if not destinatario:
            logger.error(
                "No se configuró MASA_RICA_PEDIDOS_EMAIL."
            )
            return

        comprobante_pdf = generar_comprobante_webpay(
            pedido,
            transaccion_webpay
        )

        monto = f"${transaccion_webpay.monto:,}".replace(",", ".")

        asunto = (
            f"Masa Rica - Pago Webpay confirmado "
            f"- Pedido #{pedido.id}"
        )

        mensaje = (
            "OPERIA MASA RICA\n\n"
            "Se ha confirmado un pago mediante Webpay Plus.\n\n"
            f"Número de pedido: #{pedido.id}\n"
            f"Cliente: {pedido.nombre_cliente}\n"
            f"Monto pagado: {monto}\n"
            f"Orden de compra: {transaccion_webpay.orden_compra}\n"
            f"Código de autorización: "
            f"{transaccion_webpay.codigo_autorizacion or 'No informado'}\n"
            "Método: Tarjeta mediante Webpay Plus\n"
            "Estado: PAGO APROBADO\n\n"
            "Se adjunta el comprobante de compra "
            "generado automáticamente por Operia.\n\n"
            "No se incluyen datos sensibles de la tarjeta.\n\n"
            "Ingresa al panel administrativo de Operia "
            "para gestionar el pedido."
        )

        correo = EmailMessage(
            subject=asunto,
            body=mensaje,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[destinatario],
        )

        correo.attach(
            f"Comprobante_Webpay_Pedido_{pedido.id}.pdf",
            comprobante_pdf,
            "application/pdf",
        )

        correo.send(fail_silently=False)

        logger.info(
            "Comprobante Webpay enviado para pedido #%s",
            pedido.id
        )

    except Exception:
        # Un error de Gmail nunca debe cambiar
        # el resultado de un pago ya autorizado.
        logger.exception(
            "No se pudo enviar el comprobante Webpay "
            "del pedido #%s",
            pedido_id
        )

@csrf_exempt
@require_http_methods(["GET", "POST"])
def retorno_webpay(request):

    token = (
        request.POST.get("token_ws")
        or request.GET.get("token_ws")
    )

    token_cancelado = (
        request.POST.get("TBK_TOKEN")
        or request.GET.get("TBK_TOKEN")
    )

    if not token:

        if token_cancelado:
            # No modificar el estado basándose solamente
            # en un token de cancelación recibido.
            logger.info(
                "Retorno de Webpay sin token_ws. "
                "Se recibió una señal de cancelación."
            )

        messages.warning(
            request,
            "El pago no fue completado o no pudo verificarse. "
            "Revisa el pedido antes de intentar pagar nuevamente."
        )
        return redirect("mis_compras")

    if len(token) > 128:
        messages.error(
            request,
            "La respuesta del pago no es válida."
        )
        return redirect("mis_compras")

    transaccion_webpay = (
        TransaccionWebpay.objects
        .select_related("pedido")
        .filter(token=token)
        .first()
    )

    if transaccion_webpay is None:
        messages.error(
            request,
            "No se encontró la transacción del pago."
        )
        return redirect("mis_compras")

    if transaccion_webpay.estado == "aprobada":
        messages.info(
            request,
            "Este pago ya había sido confirmado."
        )
        return redirect("mis_compras")

    if transaccion_webpay.estado != "iniciada":
        messages.warning(
            request,
            "Esta transacción ya fue procesada."
        )
        return redirect("mis_compras")

    try:
        respuesta = obtener_transaccion_webpay().commit(token)

    except Exception:
        logger.exception(
            "No se pudo consultar el resultado Webpay "
            "de la orden %s",
            transaccion_webpay.orden_compra
        )

        messages.error(
            request,
            "No pudimos verificar el resultado del pago. "
            "Contacta a Masa Rica antes de volver a pagar."
        )
        return redirect("mis_compras")

    try:
        monto_recibido = int(respuesta["amount"])
        codigo_respuesta = int(respuesta["response_code"])
        orden_recibida = respuesta["buy_order"]
        estado_recibido = respuesta["status"]

    except (KeyError, TypeError, ValueError):
        logger.error(
            "Respuesta Webpay incompleta para orden %s",
            transaccion_webpay.orden_compra
        )

        messages.error(
            request,
            "No fue posible validar los datos del pago."
        )
        return redirect("mis_compras")

    pago_autorizado = (
        estado_recibido == "AUTHORIZED"
        and codigo_respuesta == 0
        and orden_recibida == transaccion_webpay.orden_compra
        and monto_recibido == transaccion_webpay.monto
    )

    with transaction.atomic():

        transaccion_webpay = (
            TransaccionWebpay.objects
            .select_for_update()
            .get(pk=transaccion_webpay.pk)
        )

        pedido = (
            Pedido.objects
            .select_for_update()
            .get(pk=transaccion_webpay.pedido_id)
        )

        if transaccion_webpay.estado != "iniciada":
            return redirect("mis_compras")

        if pago_autorizado:

            monto_actual = calcular_total_pedido(pedido)

            if (
                pedido.estado == "cancelado"
                or pedido.metodo_pago not in ["debito", "credito"]
                or monto_actual != transaccion_webpay.monto
            ):
                transaccion_webpay.estado = "error"
                transaccion_webpay.save(update_fields=["estado"])

                logger.error(
                    "Pago autorizado requiere revisión manual: "
                    "pedido #%s",
                    pedido.id
                )

                messages.error(
                    request,
                    "El pago requiere revisión del negocio. "
                    "No intentes pagarlo nuevamente."
                )
                return redirect("mis_compras")

            # Guardar primero la aprobación bancaria.
            transaccion_webpay.estado = "aprobada"
            transaccion_webpay.codigo_autorizacion = str(
                respuesta.get("authorization_code") or ""
            )[:64]

            transaccion_webpay.save(
                update_fields=[
                    "estado",
                    "codigo_autorizacion",
                    "fecha_actualizacion",
                ]
            )

            pedido.estado_pago = "confirmado"
            pedido.save(update_fields=["estado_pago"])

            # El correo se envía únicamente después
            # de confirmar la transacción en la base de datos.
            transaction.on_commit(
                lambda pedido_id=pedido.id,
                       transaccion_id=transaccion_webpay.id:
                enviar_correo_pago_webpay(
                    pedido_id,
                    transaccion_id
                )
            )

        else:

            if (
                orden_recibida != transaccion_webpay.orden_compra
                or monto_recibido != transaccion_webpay.monto
            ):
                transaccion_webpay.estado = "error"

                logger.error(
                    "Inconsistencia en Webpay para pedido #%s",
                    pedido.id
                )

            else:
                transaccion_webpay.estado = "rechazada"

            transaccion_webpay.save(
                update_fields=[
                    "estado",
                    "fecha_actualizacion",
                ]
            )

    if pago_autorizado:

        messages.success(
            request,
            f"¡Pago aprobado! El pedido #{pedido.id} "
            "fue pagado correctamente mediante Webpay."
        )

    else:

        messages.warning(
            request,
            "El pago no fue aprobado o requiere revisión. "
            "Consulta el estado antes de volver a intentarlo."
        )

    return redirect("mis_compras")

def normalizar_telefono(telefono):
    """
    Elimina espacios, paréntesis y guiones.
    """

    return re.sub(
        r"[\s()-]",
        "",
        telefono.strip()
    )


def telefono_usuario(telefono):
    """
    Normaliza el teléfono y elimina +56.
    """

    telefono = normalizar_telefono(telefono)

    if telefono.startswith("+56"):
        telefono = telefono[3:]

    return telefono


def personal_requerido(vista):
    """
    Permite acceder únicamente al personal autorizado.
    """

    @wraps(vista)
    @login_required(login_url="login_operia")
    def protegida(request, *args, **kwargs):

        if not request.user.is_staff:
            return HttpResponseForbidden(
                "No tienes permisos para acceder "
                "a esta sección."
            )

        return vista(request, *args, **kwargs)

    return protegida


def calcular_total_pedido(pedido):
    """
    Calcula el total utilizando los precios guardados
    en cada detalle del pedido.
    """

    return sum(
        detalle.subtotal
        for detalle in pedido.detalles.all()
    )


def construir_etapas_visuales(pedido):
    """
    Prepara las cinco etapas del pedido para mostrarlas
    según su estado actual.
    """

    etapas = []

    etapas_completadas = set(
        pedido.etapas_completadas
    )

    for numero, valor in enumerate(
        Pedido.ETAPAS_PROGRESO,
        start=1
    ):

        etiqueta = dict(Pedido.ESTADOS).get(
            valor,
            valor
        )

        es_actual = pedido.estado == valor

        esta_completada = (
            valor in etapas_completadas
        )

        if pedido.estado == "cancelado":
            clase_visual = "pendiente"

        elif es_actual:
            clase_visual = "actual"

        elif esta_completada:
            clase_visual = "completada"

        else:
            clase_visual = "pendiente"

        etapas.append({
            "valor": valor,
            "etiqueta": etiqueta,
            "numero": numero,
            "clase_visual": clase_visual,
            "es_actual": es_actual,
            "esta_completada": esta_completada,
        })

    return etapas

def enviar_correo_nuevo_pedido(pedido_id):
    """
    Envía un correo al negocio cuando llega un pedido.

    Para activar el envío real se debe configurar:
    - MASA_RICA_PEDIDOS_EMAIL
    - EMAIL_HOST
    - EMAIL_PORT
    - EMAIL_HOST_USER
    - EMAIL_HOST_PASSWORD, si corresponde

    Si no existe un correo receptor configurado,
    el pedido se guarda normalmente.
    """

    correo_destino = getattr(
        settings,
        "MASA_RICA_PEDIDOS_EMAIL",
        ""
    )

    if not correo_destino:
        logger.info(
            "Pedido #%s registrado. "
            "Correo de avisos no configurado.",
            pedido_id
        )
        return

    try:
        pedido = (
            Pedido.objects
            .prefetch_related("detalles__producto")
            .get(pk=pedido_id)
        )

        total = calcular_total_pedido(pedido)

        productos = []

        for detalle in pedido.detalles.all():
            productos.append(
                f"- {detalle.producto.nombre}\n"
                f"  Cantidad: {detalle.cantidad}\n"
                f"  Subtotal: ${detalle.subtotal:,}"
            )

        detalle_productos = "\n".join(productos)

        asunto = (
            f"Masa Rica - Nuevo pedido #{pedido.id}"
        )

        mensaje = (
            "Se ha recibido un nuevo pedido "
            "desde la página web de Masa Rica.\n\n"

            f"Número de pedido: #{pedido.id}\n"
            f"Cliente: {pedido.nombre_cliente}\n"
            f"Teléfono: {pedido.telefono_cliente}\n"

            f"Método de pago: "
            f"{pedido.get_metodo_pago_display()}\n"

            f"Estado del pago: "
            f"{pedido.get_estado_pago_display()}\n"

            f"Estado del pedido: "
            f"{pedido.get_estado_display()}\n\n"

            "PRODUCTOS:\n"
            f"{detalle_productos}\n\n"

            f"TOTAL: ${total:,}\n\n"

            "Ingresa al panel administrativo "
            "de Operia para gestionar el pedido."
        )

        send_mail(
            subject=asunto,
            message=mensaje,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[correo_destino],
            fail_silently=False,
        )

    except Exception:
        logger.exception(
            "No se pudo enviar el correo "
            "del pedido #%s.",
            pedido_id
        )

@ensure_csrf_cookie
def inicio(request):

    productos_diarios = (
        Producto.objects
        .filter(
            disponible=True,
            tipo_venta="diaria"
        )
        .order_by("categoria", "nombre")
    )

    productos_encargo = (
        Producto.objects
        .filter(
            disponible=True,
            tipo_venta="encargo"
        )
        .order_by("categoria", "nombre")
    )

    return render(
        request,
        "web/inicio.html",
        {
            "productos_diarios": productos_diarios,
            "productos_encargo": productos_encargo,
        }
    )

CATEGORIAS_CATALOGO = {

    "empanadas": {
        "titulo": "Empanadas",
        "icono": "🥟",
        "descripcion": (
            "Descubre nuestras variedades de empanadas "
            "y elige tus favoritas."
        ),
        "tipo_venta": "diaria",
    },

    "humitas": {
        "titulo": "Humitas",
        "icono": "🌽",
        "descripcion": (
            "Disfruta de nuestras preparaciones "
            "tradicionales de humitas."
        ),
        "tipo_venta": "diaria",
    },

    "pastel-de-choclo": {
        "titulo": "Pastel de choclo",
        "icono": "🍲",
        "descripcion": (
            "Una preparación tradicional "
            "para disfrutar en familia."
        ),
        "tipo_venta": "diaria",
    },

    "sopaipillas": {
        "titulo": "Sopaipillas",
        "icono": "🍽️",
        "descripcion": (
            "Conoce nuestras sopaipillas tradicionales."
        ),
        "tipo_venta": "diaria",
    },

    "sopaipillas-pasadas": {
        "titulo": "Sopaipillas pasadas",
        "icono": "🍯",
        "descripcion": (
            "Una alternativa dulce "
            "de nuestra cocina chilena."
        ),
        "tipo_venta": "diaria",
    },

    "bebidas": {
        "titulo": "Bebidas",
        "icono": "🥤",
        "descripcion": (
            "Elige una bebida para acompañar tu pedido."
        ),
        "tipo_venta": "diaria",
    },

    "mini-empanadas": {
        "titulo": "Mini empanadas",
        "icono": "🥟",
        "descripcion": (
            "Preparaciones por encargo "
            "para reuniones y celebraciones."
        ),
        "tipo_venta": "encargo",
    },

    "mini-pizzas": {
        "titulo": "Mini pizzas",
        "icono": "🍕",
        "descripcion": (
            "Una alternativa especial para compartir."
        ),
        "tipo_venta": "encargo",
    },

    "cocteles": {
        "titulo": "Cócteles",
        "icono": "🍢",
        "descripcion": (
            "Preparaciones especiales para tus eventos."
        ),
        "tipo_venta": "encargo",
    },

    "pavo-relleno": {
        "titulo": "Pavo relleno",
        "icono": "🍗",
        "descripcion": (
            "Una preparación especial "
            "para compartir en familia."
        ),
        "tipo_venta": "encargo",
    },
}



@ensure_csrf_cookie
def productos_categoria(request, categoria):

    datos_categoria = CATEGORIAS_CATALOGO.get(categoria)

    if datos_categoria is None:
        raise Http404(
            "La categoría solicitada no existe."
        )

    # Relacionar las direcciones del catálogo
    # con las categorías guardadas en la base de datos.
    categorias_modelo = {
        "empanadas": "empanadas",
        "humitas": "humitas",
        "pastel-de-choclo": "pastel_choclo",
        "sopaipillas": "sopaipillas",
        "sopaipillas-pasadas": "sopaipillas_pasadas",
        "bebidas": "bebidas",
        "mini-empanadas": "mini_empanadas",
        "mini-pizzas": "mini_pizzas",
        "cocteles": "cocteles",
        "pavo-relleno": "pavo_relleno",
    }

    categoria_modelo = categorias_modelo.get(categoria)

    if categoria_modelo is None:
        raise Http404(
            "La categoría solicitada no existe."
        )

    # Consultar los productos registrados.
    productos = (
        Producto.objects
        .filter(
            categoria=categoria_modelo,
            tipo_venta=datos_categoria["tipo_venta"],
            disponible=True
        )
        .order_by("nombre")
    )

    return render(
        request,
        "web/productos.html",
        {
            "categoria_actual": categoria,
            "titulo_categoria": datos_categoria["titulo"],
            "icono_categoria": datos_categoria["icono"],
            "descripcion_categoria": datos_categoria["descripcion"],
            "tipo_venta": datos_categoria["tipo_venta"],
            "productos": productos,
        }
    )

def registro_cliente(request):

    if request.user.is_authenticated:

        if request.user.is_staff:
            return redirect("panel_operia")

        return redirect("inicio")

    if request.method == "POST":

        nombre_completo = " ".join(
            request.POST.get(
                "nombre_completo", ""
            ).split()
        )

        telefono = request.POST.get(
            "telefono", ""
        ).strip()

        password1 = request.POST.get(
            "password1", ""
        )

        password2 = request.POST.get(
            "password2", ""
        )

        telefono_normalizado = normalizar_telefono(
            telefono
        )

        username_telefono = telefono_usuario(
            telefono
        )

        errores = []

        # VALIDAR NOMBRE COMPLETO

        if (
            len(nombre_completo.split()) < 2
            or len(nombre_completo) > 150
            or not PATRON_NOMBRE.fullmatch(
                nombre_completo
            )
        ):

            errores.append(
                "Ingresa tu nombre y apellido. "
                "Utiliza solo letras, espacios, "
                "guiones o apóstrofes."
            )

        # VALIDAR TELÉFONO

        if not PATRON_TELEFONO.fullmatch(
            telefono_normalizado
        ):

            errores.append(
                "Ingresa un teléfono chileno válido "
                "de 9 dígitos, con o sin +56."
            )

        Usuario = get_user_model()

        if Usuario.objects.filter(
            username=username_telefono
        ).exists():

            errores.append(
                "Este teléfono ya tiene "
                "una cuenta registrada."
            )

        # VALIDAR CONTRASEÑAS

        if not password1 or not password2:

            errores.append(
                "Debes ingresar y confirmar "
                "tu contraseña."
            )

        elif password1 != password2:

            errores.append(
                "Las contraseñas no coinciden."
            )

        else:

            try:
                validate_password(password1)

            except ValidationError as error:
                errores.extend(error.messages)

        # MOSTRAR ERRORES

        if errores:

            for error in errores:
                messages.error(request, error)

            return render(
                request,
                "web/registro_cliente.html",
                {
                    "datos": {
                        "nombre_completo": nombre_completo,
                        "telefono": telefono,
                    }
                }
            )

        # CREAR CUENTA

        try:

            with transaction.atomic():

                usuario = Usuario.objects.create_user(
                    username=username_telefono,
                    password=password1,
                    first_name=nombre_completo,
                    is_staff=False,
                    is_superuser=False,
                )

        except IntegrityError:

            messages.error(
                request,
                "No se pudo crear la cuenta. "
                "Verifica que el teléfono "
                "no esté registrado."
            )

            return render(
                request,
                "web/registro_cliente.html",
                {
                    "datos": {
                        "nombre_completo": nombre_completo,
                        "telefono": telefono,
                    }
                }
            )

        login(request, usuario)

        messages.success(
            request,
            "¡Tu cuenta se creó correctamente! "
            "Bienvenido a Masa Rica."
        )

        return redirect("inicio")

    return render(
        request,
        "web/registro_cliente.html"
    )

def login_cliente(request):

    if request.user.is_authenticated:

        if request.user.is_staff:
            return redirect("panel_operia")

        return redirect("inicio")

    nombre_completo = ""

    if request.method == "POST":

        nombre_completo = " ".join(
            request.POST.get(
                "nombre_completo", ""
            ).split()
        )

        password = request.POST.get(
            "password", ""
        )

        Usuario = get_user_model()

        clientes = Usuario.objects.filter(
            first_name__iexact=nombre_completo,
            is_staff=False,
            is_active=True
        )

        cantidad_clientes = clientes.count()

        if cantidad_clientes == 1:

            cliente = clientes.first()

            usuario = authenticate(
                request,
                username=cliente.username,
                password=password
            )

            if (
                usuario is not None
                and usuario.is_active
                and not usuario.is_staff
            ):

                login(request, usuario)

                messages.success(
                    request,
                    "¡Bienvenido nuevamente a Masa Rica!"
                )

                return redirect("inicio")

            messages.error(
                request,
                "El nombre completo o la contraseña "
                "son incorrectos."
            )

        elif cantidad_clientes > 1:

            messages.error(
                request,
                "Hay más de una cuenta con ese nombre. "
                "Para evitar confusiones, solicita ayuda "
                "para identificar tu cuenta."
            )

        else:

            messages.error(
                request,
                "El nombre completo o la contraseña "
                "son incorrectos."
            )

    return render(
        request,
        "web/login_cliente.html",
        {
            "nombre_completo": nombre_completo
        }
    )

@login_required(login_url="login_cliente")
@require_POST
def logout_cliente(request):

    if request.user.is_staff:

        return HttpResponseForbidden(
            "Utiliza la opción de cerrar "
            "sesión del personal."
        )

    logout(request)

    messages.success(
        request,
        "Has cerrado sesión correctamente."
    )

    return redirect("inicio")


@require_POST
def confirmar_pedido(request):

    # VALIDAR SESIÓN DEL CLIENTE

    if not request.user.is_authenticated:

        return JsonResponse(
            {
                "ok": False,
                "mensaje": (
                    "Debes iniciar sesión "
                    "para confirmar tu pedido."
                )
            },
            status=401
        )

    if request.user.is_staff:

        return JsonResponse(
            {
                "ok": False,
                "mensaje": (
                    "Esta función es exclusiva "
                    "para clientes."
                )
            },
            status=403
        )

    # LEER DATOS DEL CARRITO

    try:
        datos = json.loads(request.body)

    except (ValueError, UnicodeDecodeError):

        return JsonResponse(
            {
                "ok": False,
                "mensaje": (
                    "Los datos del pedido no son válidos."
                )
            },
            status=400
        )

    if not isinstance(datos, dict):

        return JsonResponse(
            {
                "ok": False,
                "mensaje": (
                    "El formato del pedido no es válido."
                )
            },
            status=400
        )

    productos_recibidos = datos.get(
        "productos", []
    )

    metodo_pago = datos.get(
        "metodo_pago", ""
    )

    # AUTORIZACIÓN DE WHATSAPP
    # EL CLIENTE DEBE RESPONDER SÍ O NO.

    if (
        "acepta_whatsapp" not in datos
        or type(datos["acepta_whatsapp"]) is not bool
    ):

        return JsonResponse(
            {
                "ok": False,
                "mensaje": (
                    "Debes indicar si autorizas "
                    "recibir avisos por WhatsApp "
                    "antes de confirmar tu pedido."
                )
            },
            status=400
        )

    acepta_whatsapp = datos["acepta_whatsapp"]

    # VALIDAR LOS CUATRO MÉTODOS DE PAGO

    metodos_validos = {
        "efectivo",
        "debito",
        "credito",
        "transferencia",
    }

    if (
        not isinstance(metodo_pago, str)
        or metodo_pago not in metodos_validos
    ):

        return JsonResponse(
            {
                "ok": False,
                "mensaje": (
                    "Selecciona un método "
                    "de pago válido."
                )
            },
            status=400
        )

    # VALIDAR CARRITO

    if (
        not isinstance(productos_recibidos, list)
        or not 1 <= len(productos_recibidos) <= 50
    ):

        return JsonResponse(
            {
                "ok": False,
                "mensaje": (
                    "El carrito está vacío o supera "
                    "el límite permitido."
                )
            },
            status=400
        )

    cantidades = {}

    for item in productos_recibidos:

        if not isinstance(item, dict):

            return JsonResponse(
                {
                    "ok": False,
                    "mensaje": (
                        "Hay un producto inválido "
                        "en el carrito."
                    )
                },
                status=400
            )

        producto_id = item.get("id")
        cantidad = item.get("cantidad")

        if (
            type(producto_id) is not int
            or producto_id <= 0
            or type(cantidad) is not int
            or not 1 <= cantidad <= MAX_CANTIDAD_PRODUCTO
        ):

            return JsonResponse(
                {
                    "ok": False,
                    "mensaje": (
                        "Revisa las cantidades "
                        "del carrito."
                    )
                },
                status=400
            )

        cantidades[producto_id] = (
            cantidades.get(producto_id, 0)
            + cantidad
        )

        if (
            cantidades[producto_id]
            > MAX_CANTIDAD_PRODUCTO
        ):

            return JsonResponse(
                {
                    "ok": False,
                    "mensaje": (
                        "La cantidad de un producto "
                        "supera el máximo permitido."
                    )
                },
                status=400
            )

    # VERIFICAR PRODUCTOS Y GUARDAR PEDIDO

    with transaction.atomic():

        productos = list(
            Producto.objects.filter(
                id__in=cantidades.keys(),
                disponible=True
            )
        )

        if len(productos) != len(cantidades):

            return JsonResponse(
                {
                    "ok": False,
                    "mensaje": (
                        "Uno o más productos "
                        "ya no están disponibles."
                    )
                },
                status=400
            )

        # DATOS DEL CLIENTE

        nombre_cliente = (
            request.user.get_full_name().strip()
            or request.user.first_name.strip()
            or request.user.username
        )

        telefono_cliente = request.user.username

        # CALCULAR TIEMPO ESTIMADO

        cantidad_empanadas = sum(
            cantidades[producto.id]
            for producto in productos
            if producto.categoria == "empanadas"
        )

        minutos_estimados = (
            Pedido.calcular_minutos_estimados(
                cantidad_empanadas
            )
        )

        # CREAR PEDIDO
        # GUARDAR AUTORIZACIÓN DE WHATSAPP

        pedido = Pedido.objects.create(
            cliente_usuario=request.user,
            nombre_cliente=nombre_cliente[:100],
            telefono_cliente=telefono_cliente[:20],
            origen="web",
            acepta_whatsapp=acepta_whatsapp,
            metodo_pago=metodo_pago,
            estado_pago="pendiente",
            estado="pendiente",
            minutos_estimados=minutos_estimados
        )

        total = 0

        # CREAR DETALLES DEL PEDIDO

        for producto in productos:

            cantidad = cantidades[producto.id]

            detalle = DetallePedido.objects.create(
                pedido=pedido,
                producto=producto,
                cantidad=cantidad
            )

            total += detalle.subtotal
        
        
        if metodo_pago == "efectivo":
            transaction.on_commit(
                lambda pedido_id=pedido.id:
                enviar_correo_nuevo_pedido(pedido_id)
            )

    # RESPUESTA AL CLIENTE

    return JsonResponse(
        {
            "ok": True,
            "mensaje": (
                "Tu pedido fue registrado correctamente."
            ),
            "pedido_id": pedido.id,
            "total": total,
            "metodo_pago": metodo_pago,
            "estado_pago": "pendiente",
            "estado": "pendiente",
        },
        status=201
    )


def login_operia(request):

    if request.user.is_authenticated:

        if request.user.is_staff:
            return redirect("inicio")

        return HttpResponseForbidden(
            "Esta sección es exclusiva "
            "del personal de Masa Rica."
        )

    if request.method == "POST":

        username = request.POST.get(
            "username", ""
        ).strip()

        password = request.POST.get(
            "password", ""
        )

        usuario = authenticate(
            request,
            username=username,
            password=password
        )

        if (
            usuario is not None
            and usuario.is_active
            and usuario.is_staff
        ):

            login(request, usuario)

            messages.success(
                request,
                "Has iniciado sesión correctamente. "
                "Bienvenido a Masa Rica."
            )

            return redirect("inicio")

        messages.error(
            request,
            "Credenciales incorrectas "
            "o usuario sin autorización."
        )

    return render(
        request,
        "web/login.html"
    )


@personal_requerido
def panel_operia(request):

    hoy = timezone.localdate()

    pedidos_hoy = Pedido.objects.filter(
        fecha_pedido__date=hoy
    ).count()

    pedidos_pendientes = Pedido.objects.filter(
        estado__in=[
            "pendiente",
            "preparacion",
            "coccion",
        ]
    ).count()

    subtotal = ExpressionWrapper(
        F("cantidad") * F("precio_unitario"),
        output_field=IntegerField()
    )

    ventas_dia = DetallePedido.objects.filter(
        pedido__fecha_pedido__date=hoy,
        pedido__estado="entregado",
        pedido__estado_pago="confirmado"
    ).aggregate(
        total=Sum(subtotal)
    )["total"] or 0

    alertas_inventario = Insumo.objects.filter(
        activo=True,
        stock_actual__lte=F("stock_minimo")
    ).count()

    resumen_estados = Pedido.objects.filter(
        fecha_pedido__date=hoy
    ).aggregate(
        pendientes=Count(
            "id",
            filter=Q(estado="pendiente")
        ),
        preparacion=Count(
            "id",
            filter=Q(estado="preparacion")
        ),
        coccion=Count(
            "id",
            filter=Q(estado="coccion")
        ),
        listos=Count(
            "id",
            filter=Q(estado="listo")
        ),
        entregados=Count(
            "id",
            filter=Q(estado="entregado")
        ),
        cancelados=Count(
            "id",
            filter=Q(estado="cancelado")
        )
    )

    pedidos_recientes = Pedido.objects.order_by(
        "-fecha_pedido"
    )[:5]

    insumos_bajo_stock = Insumo.objects.filter(
        activo=True,
        stock_actual__lte=F("stock_minimo")
    ).order_by(
        "stock_actual",
        "id"
    )[:5]

    return render(
        request,
        "web/panel.html",
        {
            "pedidos_hoy": pedidos_hoy,
            "pedidos_pendientes": pedidos_pendientes,
            "ventas_dia": ventas_dia,
            "alertas_inventario": alertas_inventario,
            "resumen_estados": resumen_estados,
            "pedidos_recientes": pedidos_recientes,
            "insumos_bajo_stock": insumos_bajo_stock,
        }
    )


@personal_requerido
def pedidos_operia(request):

    pedidos = list(
        Pedido.objects
        .prefetch_related("detalles__producto")
        .order_by("-fecha_pedido", "-id")
    )

    fecha_limite = (
        timezone.now()
        - timedelta(days=DIAS_PARA_ELIMINAR)
    )

    for pedido in pedidos:

        # TOTAL DEL PEDIDO

        pedido.total_pedido = (
            calcular_total_pedido(pedido)
        )

        # CANTIDAD DE PRODUCTOS

        pedido.cantidad_productos = sum(
            detalle.cantidad
            for detalle in pedido.detalles.all()
        )

        # PERMITIR ELIMINAR SOLO PEDIDOS ANTIGUOS
        # ENTREGADOS O CANCELADOS.

        pedido.puede_eliminarse = (
            pedido.estado in (
                "entregado",
                "cancelado"
            )
            and pedido.fecha_pedido <= fecha_limite
        )

        # CINCO ETAPAS VISUALES

        pedido.etapas_visuales = (
            construir_etapas_visuales(pedido)
        )

        # SIGUIENTE ETAPA

        pedido.proximo_estado = (
            pedido.siguiente_estado
        )

        pedido.puede_avanzar_pedido = (
            pedido.puede_avanzar
        )

        # MÉTODO DE PAGO

        pedido.nombre_metodo_pago = (
            pedido.get_metodo_pago_display()
        )

        # ESTADO DEL PAGO

        pedido.nombre_estado_pago = (
            pedido.get_estado_pago_display()
        )

    return render(
        request,
        "web/pedidos.html",
        {
            "pedidos": pedidos,
            "estados": Pedido.ESTADOS,
        }
    )


def descontar_inventario_pedido(pedido, usuario):

    with transaction.atomic():

        # EVITAR DESCONTAR DOS VECES EL MISMO PEDIDO

        if ConsumoInventarioPedido.objects.filter(
            pedido=pedido
        ).exists():

            raise ValidationError(
                "El inventario de este pedido ya fue descontado."
            )

        # OBTENER LOS PRODUCTOS DEL PEDIDO Y SUS RECETAS

        detalles = list(
            pedido.detalles
            .select_related("producto")
            .prefetch_related(
                "producto__ingredientes_receta__insumo"
            )
        )

        if not detalles:

            raise ValidationError(
                "El pedido no contiene productos."
            )

        # CALCULAR LAS CANTIDADES NECESARIAS

        cantidades_necesarias = {}

        nombres_insumos = {}

        for detalle in detalles:

            if detalle.cantidad <= 0:

                raise ValidationError(
                    "El pedido contiene una cantidad no válida."
                )

            recetas = list(
                detalle.producto.ingredientes_receta.all()
            )

            if not recetas:

                raise ValidationError(
                    f"El producto {detalle.producto.nombre} "
                    "no tiene una receta configurada."
                )

            for receta in recetas:

                cantidad_total = (
                    receta.cantidad * Decimal(detalle.cantidad)
                )

                insumo_id = receta.insumo_id

                cantidades_necesarias[insumo_id] = (
                    cantidades_necesarias.get(
                        insumo_id,
                        Decimal("0")
                    ) + cantidad_total
                )

                nombres_insumos[insumo_id] = (
                    receta.insumo.nombre
                )

        # BLOQUEAR LOS INSUMOS MIENTRAS SE COMPRUEBA EL STOCK

        insumos = {
            insumo.pk: insumo
            for insumo in (
                Insumo.objects
                .select_for_update()
                .filter(
                    pk__in=cantidades_necesarias.keys()
                )
                .order_by("pk")
            )
        }

        # COMPROBAR QUE TODOS LOS INSUMOS EXISTAN

        if len(insumos) != len(cantidades_necesarias):

            raise ValidationError(
                "No se pudieron encontrar todos los ingredientes."
            )

        # COMPROBAR QUE EXISTA STOCK SUFICIENTE

        for insumo_id, cantidad in cantidades_necesarias.items():

            insumo = insumos[insumo_id]

            if not insumo.activo:

                raise ValidationError(
                    f"El ingrediente {insumo.nombre} "
                    "está desactivado."
                )

            if insumo.stock_actual < cantidad:

                raise ValidationError(
                    f"No hay suficiente stock de {insumo.nombre}. "
                    f"Disponible: {insumo.stock_actual}. "
                    f"Necesario: {cantidad}."
                )

        # REGISTRAR LAS SALIDAS DE INVENTARIO

        for insumo_id in sorted(cantidades_necesarias):

            movimiento = MovimientoInventario(
                insumo=insumos[insumo_id],
                tipo="salida",
                cantidad=cantidades_necesarias[insumo_id],
                motivo=(
                    f"Consumo automático por pedido #{pedido.pk}"
                ),
                usuario=usuario
            )

            movimiento.save()

        # REGISTRAR QUE EL PEDIDO YA DESCONTÓ INVENTARIO

        consumo = ConsumoInventarioPedido.objects.create(
            pedido=pedido,
            usuario=usuario
        )

        return consumo


@personal_requerido
@require_POST
def actualizar_estado_pedido(request, pedido_id):

    origen_detalle = request.POST.get("origen") == "detalle"

    def volver_al_origen():

        if origen_detalle:
            return redirect(
                "detalle_pedido",
                pedido_id=pedido_id
            )

        return redirect(
            reverse("pedidos_operia") + f"#pedido-{pedido_id}"
        )

    estados_recibidos = request.POST.getlist("estado")

    if len(estados_recibidos) != 1:
        messages.error(
            request,
            "Debes seleccionar un único estado válido."
        )
        return volver_al_origen()

    nuevo_estado = estados_recibidos[0]

    estados_validos = {
        valor
        for valor, etiqueta in Pedido.ESTADOS
    }

    if nuevo_estado not in estados_validos:
        messages.error(
            request,
            "El estado seleccionado no es válido."
        )
        return volver_al_origen()

    with transaction.atomic():

        pedido = get_object_or_404(
            Pedido.objects.select_for_update(),
            pk=pedido_id
        )

        estado_anterior = pedido.estado

        if nuevo_estado == estado_anterior:
            messages.info(
                request,
                f"El pedido #{pedido.id} ya está en esa etapa."
            )
            return volver_al_origen()

        if nuevo_estado == "cancelado":

            if estado_anterior in ("entregado", "cancelado"):
                messages.error(
                    request,
                    "No puedes cancelar un pedido "
                    "que ya fue retirado o cancelado."
                )
                return volver_al_origen()

            pedido.estado = "cancelado"
            pedido.save(update_fields=["estado"])

            messages.success(
                request,
                f"El pedido #{pedido.id} fue cancelado."
            )
            return volver_al_origen()

        if not pedido.puede_cambiar_a(nuevo_estado):
            messages.error(
                request,
                "No puedes saltarte etapas. "
                "Debes avanzar el pedido en el orden establecido."
            )
            return volver_al_origen()

        if nuevo_estado == "entregado":

            numero_confirmacion = request.POST.get(
                "numero_confirmacion",
                ""
            ).strip()

            if numero_confirmacion != str(pedido.id):
                messages.error(
                    request,
                    "El número ingresado no coincide. "
                    "Verifica el número del pedido con el cliente."
                )
                return volver_al_origen()
                # DESCONTAR INVENTARIO AL INICIAR LA PREPARACIÓN

        if nuevo_estado == "preparacion":

            try:

                descontar_inventario_pedido(
                    pedido,
                    request.user
                )

            except ValidationError as error:

                if hasattr(error, "message_dict"):

                    errores = [
                        mensaje
                        for mensajes in error.message_dict.values()
                        for mensaje in mensajes
                    ]

                else:

                    errores = error.messages

                for mensaje in errores:

                    messages.error(
                        request,
                        mensaje
                    )

                return volver_al_origen()

        nombre_estado = pedido.get_estado_display()

        messages.success(
            request,
            f"El pedido #{pedido.id} "
            f"ahora está en: {nombre_estado}."
        )

    return volver_al_origen()

@personal_requerido
def detalle_pedido(request, pedido_id):

    # BUSCAR EL PEDIDO Y SUS PRODUCTOS

    pedido = get_object_or_404(
        Pedido.objects.prefetch_related(
            "detalles__producto"
        ),
        pk=pedido_id
    )

    # OBTENER LOS DETALLES DEL PEDIDO

    detalles = pedido.detalles.all()

    # CALCULAR EL TOTAL DEL PEDIDO

    total_pedido = sum(
        detalle.subtotal
        for detalle in detalles
    )

    # PREPARAR LAS ETAPAS VISUALES

    pedido.etapas_visuales = (
        construir_etapas_visuales(pedido)
    )

    # MOSTRAR LA PÁGINA DE DETALLE

    return render(
        request,
        "web/detalle_pedido.html",
        {
            "pedido": pedido,
            "detalles": detalles,
            "total_pedido": total_pedido,
        }
    )



@personal_requerido
@require_POST
def eliminar_pedido(request, pedido_id):

    if not request.user.is_superuser:
        messages.error(
            request,
            "Solo un administrador puede eliminar pedidos "
            "de forma permanente."
        )
        return redirect("pedidos_operia")

    with transaction.atomic():

        pedido = get_object_or_404(
            Pedido.objects.select_for_update(),
            pk=pedido_id
        )

        numero_pedido = pedido.id

        if pedido.estado_pago == "confirmado":
            messages.error(
                request,
                f"No puedes eliminar el pedido #{numero_pedido} "
                "porque su pago ya está confirmado."
            )
            return redirect("detalle_pedido", pedido_id=numero_pedido)

        if pedido.estado == "entregado":
            messages.error(
                request,
                f"No puedes eliminar el pedido #{numero_pedido} "
                "porque ya fue retirado por el cliente."
            )
            return redirect("detalle_pedido", pedido_id=numero_pedido)

        if pedido.estado_pago == "en_verificacion":
            messages.error(
                request,
                f"No puedes eliminar el pedido #{numero_pedido} "
                "porque su pago está en verificación."
            )
            return redirect("detalle_pedido", pedido_id=numero_pedido)

        if pedido.transacciones_webpay.exists():
            messages.error(
                request,
                f"No puedes eliminar el pedido #{numero_pedido} "
                "porque tiene una transacción Webpay registrada."
            )
            return redirect("detalle_pedido", pedido_id=numero_pedido)

        pedido.delete()

    messages.success(
        request,
        f"El pedido #{numero_pedido} fue eliminado correctamente."
    )

    return redirect("pedidos_operia")


@personal_requerido
@require_POST
def confirmar_pago_transferencia(request, pedido_id):

    # Bloquear confirmaciones accidentales o no verificadas.
    confirmacion = request.POST.get(
        "confirmacion_transferencia", ""
    )

    if confirmacion != "confirmar":
        messages.error(
            request,
            "Debes confirmar que verificaste el ingreso "
            "del dinero en la cuenta bancaria."
        )
        return redirect("detalle_pedido", pedido_id=pedido_id)

    with transaction.atomic():

        # Bloquear el registro mientras se actualiza.
        pedido = get_object_or_404(
            Pedido.objects.select_for_update(),
            pk=pedido_id
        )

        # Solo se pueden confirmar transferencias.
        if pedido.metodo_pago != "transferencia":
            messages.error(
                request,
                "Este pedido no utiliza transferencia bancaria."
            )
            return redirect(
                "detalle_pedido",
                pedido_id=pedido.id
            )

        # No confirmar pedidos cancelados.
        if pedido.estado == "cancelado":
            messages.error(
                request,
                "No se puede confirmar el pago "
                "de un pedido cancelado."
            )
            return redirect(
                "detalle_pedido",
                pedido_id=pedido.id
            )

        # Evitar confirmar dos veces el mismo pago.
        if pedido.estado_pago == "confirmado":
            messages.info(
                request,
                f"El pago del pedido #{pedido.id} "
                "ya estaba confirmado."
            )
            return redirect(
                "detalle_pedido",
                pedido_id=pedido.id
            )

        # Confirmar el pago después de la verificación.
        pedido.estado_pago = "confirmado"

        pedido.save(
            update_fields=["estado_pago"]
        )

    messages.success(
        request,
        f"El pago por transferencia del pedido "
        f"#{pedido_id} fue confirmado correctamente."
    )

    return redirect(
        "detalle_pedido",
        pedido_id=pedido_id
    )


@personal_requerido
@require_POST
def confirmar_pago_efectivo(request, pedido_id):

    confirmacion = request.POST.get(
        "confirmacion_efectivo", ""
    )

    if confirmacion != "confirmar":
        messages.error(
            request,
            "Debes confirmar que recibiste el dinero en efectivo."
        )
        return redirect(
            "detalle_pedido",
            pedido_id=pedido_id
        )

    with transaction.atomic():

        pedido = get_object_or_404(
            Pedido.objects.select_for_update(),
            pk=pedido_id
        )

        if pedido.metodo_pago != "efectivo":
            messages.error(
                request,
                "Este pedido no utiliza efectivo como método de pago."
            )
            return redirect(
                "detalle_pedido",
                pedido_id=pedido.id
            )

        if pedido.estado == "cancelado":
            messages.error(
                request,
                "No se puede confirmar el pago de un pedido cancelado."
            )
            return redirect(
                "detalle_pedido",
                pedido_id=pedido.id
            )

        if pedido.estado_pago == "confirmado":
            messages.info(
                request,
                f"El pago del pedido #{pedido.id} ya estaba confirmado."
            )
            return redirect(
                "detalle_pedido",
                pedido_id=pedido.id
            )

        pedido.estado_pago = "confirmado"

        pedido.save(
            update_fields=["estado_pago"]
        )

    messages.success(
        request,
        f"El pago en efectivo del pedido #{pedido_id} "
        "fue confirmado correctamente."
    )

    return redirect(
        "detalle_pedido",
        pedido_id=pedido_id
    )


@login_required(login_url="login_cliente")
@require_POST
def subir_comprobante_transferencia(request, pedido_id):

    if request.user.is_staff:
        return HttpResponseForbidden(
            "Esta sección es exclusiva para clientes."
        )

    pedido = get_object_or_404(
        Pedido,
        pk=pedido_id,
        cliente_usuario=request.user,
        metodo_pago="transferencia"
    )

    destino = "pago_transferencia"

    if pedido.estado == "cancelado":
        messages.error(
            request,
            "No puedes enviar comprobantes de un pedido cancelado."
        )
        return redirect(destino, pedido_id=pedido.id)

    if pedido.estado_pago == "confirmado":
        messages.error(
            request,
            "Este pedido ya tiene su pago confirmado."
        )
        return redirect(destino, pedido_id=pedido.id)

    if ComprobanteTransferencia.objects.filter(
        pedido=pedido
    ).exists():
        messages.info(
            request,
            "Ya recibimos un comprobante para este pedido."
        )
        return redirect(destino, pedido_id=pedido.id)

    if not ConfiguracionBancaria.objects.filter(
        activa=True
    ).exists():
        messages.error(
            request,
            "No hay una cuenta bancaria habilitada."
        )
        return redirect(destino, pedido_id=pedido.id)

    archivo = request.FILES.get("comprobante")

    if not archivo:
        messages.error(
            request,
            "Debes seleccionar un comprobante."
        )
        return redirect(destino, pedido_id=pedido.id)

    # Validar el tamaño máximo: 5 MB.

    if archivo.size > 5 * 1024 * 1024:
        messages.error(
            request,
            "El comprobante no puede superar los 5 MB."
        )
        return redirect(destino, pedido_id=pedido.id)

    # Validar la extensión y el contenido real del archivo.

    extension = Path(archivo.name).suffix.lower()

    tipos_permitidos = {
        ".pdf": "application/pdf",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
    }

    if extension not in tipos_permitidos:
        messages.error(
            request,
            "Solo se permiten archivos PDF, JPG o PNG."
        )
        return redirect(destino, pedido_id=pedido.id)

    # Comprobar la firma básica del archivo.

    firma = archivo.read(16)
    archivo.seek(0)

    if extension == ".pdf":
        contenido_valido = firma.startswith(b"%PDF-")
    elif extension in (".jpg", ".jpeg"):
        contenido_valido = firma.startswith(b"\xff\xd8\xff")
    else:
        contenido_valido = firma.startswith(
            b"\x89PNG\r\n\x1a\n"
        )

    if not contenido_valido:
        messages.error(
            request,
            "El archivo seleccionado no tiene un formato válido."
        )
        return redirect(destino, pedido_id=pedido.id)

    # Guardar el comprobante asociado al pedido.

    try:
        with transaction.atomic():

            pedido = Pedido.objects.select_for_update().get(
                pk=pedido.id
            )

            if (
                pedido.estado == "cancelado"
                or pedido.estado_pago == "confirmado"
            ):
                messages.error(
                    request,
                    "El pedido ya no admite comprobantes."
                )
                return redirect(destino, pedido_id=pedido.id)

            comprobante = ComprobanteTransferencia.objects.create(
                pedido=pedido,
                archivo=archivo
            )

            pedido.estado_pago = "en_verificacion"
            pedido.save(update_fields=["estado_pago"])

    except IntegrityError:
        messages.info(
            request,
            "Ya existe un comprobante para este pedido."
        )
        return redirect(destino, pedido_id=pedido.id)

    # Preparar el correo con los datos del pedido.

    correo_destino = getattr(
        settings,
        "MASA_RICA_PEDIDOS_EMAIL",
        ""
    )

    if correo_destino:

        try:
            pedido = Pedido.objects.prefetch_related(
                "detalles__producto"
            ).get(pk=pedido.id)

            productos = []

            for detalle in pedido.detalles.all():
                productos.append(
                    f"- {detalle.producto.nombre}\n"
                    f"  Cantidad: {detalle.cantidad}\n"
                    f"  Subtotal: ${detalle.subtotal:,}"
                )

            total = calcular_total_pedido(pedido)

            mensaje = (
                "Se ha recibido un comprobante de transferencia "
                "de un pedido realizado en Masa Rica.\n\n"
                f"Número de pedido: #{pedido.id}\n"
                f"Cliente: {pedido.nombre_cliente}\n"
                f"Teléfono: {pedido.telefono_cliente}\n"
                f"Método de pago: {pedido.get_metodo_pago_display()}\n"
                f"Estado del pago: {pedido.get_estado_pago_display()}\n"
                f"Estado del pedido: {pedido.get_estado_display()}\n\n"
                "PRODUCTOS:\n"
                f"{chr(10).join(productos)}\n\n"
                f"TOTAL: ${total:,}\n\n"
                "COMPROBANTE DE TRANSFERENCIA ADJUNTO.\n\n"
                "Revisa el comprobante y verifica que el dinero "
                "haya ingresado realmente a la cuenta bancaria "
                "antes de confirmar el pago en Operia."
            )

            correo = EmailMessage(
                subject=(
                    f"Masa Rica - Comprobante recibido "
                    f"- Pedido #{pedido.id}"
                ),
                body=mensaje,
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=[correo_destino]
            )

            with comprobante.archivo.open("rb") as archivo_guardado:
                correo.attach(
                    f"comprobante_pedido_{pedido.id}{extension}",
                    archivo_guardado.read(),
                    tipos_permitidos[extension]
                )

            correo.send(fail_silently=False)

        except Exception:
            logger.exception(
                "No se pudo enviar el comprobante del pedido #%s.",
                pedido.id
            )

            messages.warning(
                request,
                "El comprobante fue guardado, pero no se pudo "
                "enviar la notificación por correo. "
                "Contacta a Masa Rica para informar el problema."
            )

            return redirect(destino, pedido_id=pedido.id)

    messages.success(
        request,
        "Tu comprobante fue recibido correctamente. "
        "El pago está pendiente de verificación bancaria."
    )

    return redirect(destino, pedido_id=pedido.id)

@personal_requerido
def descargar_comprobante_transferencia(request, pedido_id):

    comprobante = get_object_or_404(
        ComprobanteTransferencia,
        pedido_id=pedido_id
    )

    extension = Path(
        comprobante.archivo.name
    ).suffix.lower()

    nombre_descarga = (
        f"comprobante_pedido_{pedido_id}{extension}"
    )

    try:
        archivo = comprobante.archivo.open("rb")
    except (FileNotFoundError, OSError):
        raise Http404(
            "El archivo del comprobante no está disponible."
        )

    return FileResponse(
        archivo,
        as_attachment=True,
        filename=nombre_descarga
    )

@personal_requerido
@require_POST
def logout_operia(request):

    logout(request)

    return redirect("login_operia")


@login_required(login_url="login_cliente")
def mis_compras(request):
    """
    Historial de pedidos del cliente.

    Seguridad:
    - Requiere inicio de sesión.
    - No permite acceso al personal.
    - Solo muestra pedidos del usuario autenticado.
    """

    if request.user.is_staff:

        return HttpResponseForbidden(
            "Esta sección es exclusiva para clientes."
        )

    pedidos = list(
        Pedido.objects
        .filter(cliente_usuario=request.user)
        .prefetch_related("detalles__producto")
        .order_by("-fecha_pedido", "-id")
    )

    for pedido in pedidos:

        detalles = list(
            pedido.detalles.all()
        )

        pedido.total_pedido = sum(
            detalle.subtotal
            for detalle in detalles
        )

        pedido.cantidad_productos = sum(
            detalle.cantidad
            for detalle in detalles
        )

    return render(
        request,
        "web/mis_compras.html",
        {
            "pedidos": pedidos
        }
    )

@login_required(login_url="login_cliente")
def pago_transferencia(request, pedido_id):

    # Solo pueden acceder los clientes.
    if request.user.is_staff:
        return HttpResponseForbidden(
            "Esta sección es exclusiva para clientes."
        )

    # Comprobar que el pedido pertenece al cliente.
    pedido = get_object_or_404(
        Pedido.objects.prefetch_related("detalles__producto"),
        pk=pedido_id,
        cliente_usuario=request.user,
        metodo_pago="transferencia"
    )

    # Calcular el total real del pedido.
    total_pedido = calcular_total_pedido(pedido)

    # Obtener los datos bancarios activos desde la base de datos.
    cuenta_bancaria = (
        ConfiguracionBancaria.objects
        .filter(activa=True)
        .first()
    )

    # Enviar los datos a la página del cliente.
    return render(
        request,
        "web/pago_transferencia.html",
        {
            "pedido": pedido,
            "total_pedido": total_pedido,
            "cuenta_bancaria": cuenta_bancaria,
        }
    )

@personal_requerido
@require_POST
def registrar_movimiento_inventario(request):

    # Recibir los datos del formulario
    formulario = MovimientoInventarioForm(request.POST)

    # Validar los campos ingresados
    if formulario.is_valid():

        movimiento = formulario.save(commit=False)

        # Registrar el usuario responsable
        movimiento.usuario = request.user

        try:

            # Guardar movimiento y actualizar stock
            movimiento.save()

            messages.success(
                request,
                "El movimiento de inventario se registró correctamente."
            )

            return redirect("inventario_operia")

        except ValidationError as error:

            # Mostrar el campo que provoca el error
            if hasattr(error, "message_dict"):

                for campo, errores in error.message_dict.items():

                    for mensaje in errores:

                        formulario.add_error(
                            None,
                            f"{campo}: {mensaje}"
                        )

            else:

                for mensaje in error.messages:

                    formulario.add_error(
                        None,
                        mensaje
                    )

    # Obtener los valores del buscador y filtro
    busqueda = request.GET.get("buscar", "").strip()
    estado = request.GET.get("estado", "todos")

    # Obtener todos los ingredientes
    insumos = Insumo.objects.all()

    # Buscar ingredientes por nombre
    if busqueda:
        insumos = insumos.filter(
            nombre__icontains=busqueda
        )

    # Filtrar ingredientes por estado
    if estado == "activos":
        insumos = insumos.filter(
            activo=True
        )

    elif estado == "inactivos":
        insumos = insumos.filter(
            activo=False
        )

    # Ordenar los ingredientes alfabéticamente
    insumos = insumos.order_by("nombre")

    # Contar los ingredientes activos
    total_insumos = Insumo.objects.filter(
        activo=True
    ).count()

    # Contar las alertas de stock bajo
    alertas_inventario = Insumo.objects.filter(
        activo=True,
        stock_actual__lte=F("stock_minimo")
    ).count()

    # Consultar los últimos movimientos
    movimientos = (
        MovimientoInventario.objects
        .select_related("insumo", "usuario")
        .order_by("-fecha")[:10]
    )


    return render(
        request,
        "web/inventario.html",
        {
            "formulario": InsumoForm(),
            "formulario_movimiento": formulario,
            "insumos": insumos,
            "total_insumos": total_insumos,
            "alertas_inventario": alertas_inventario,
            "movimientos": movimientos,
        }
    )


@personal_requerido
def inventario_operia(request):

    if request.method == "POST":

        formulario = InsumoForm(request.POST)

        if formulario.is_valid():

            formulario.save()

            messages.success(
                request,
                "El insumo se registró correctamente."
            )

            return redirect("inventario_operia")

    else:
        formulario = InsumoForm()

    formulario_movimiento = MovimientoInventarioForm()


    busqueda = request.GET.get("buscar", "").strip()
    estado = request.GET.get("estado", "todos")

    # Obtener ingredientes registrados
    insumos = Insumo.objects.all()

    # Buscar por nombre
    if busqueda:

        insumos = insumos.filter(
            nombre__icontains=busqueda
        )

    # Filtrar ingredientes activos
    if estado == "activos":

        insumos = insumos.filter(
            activo=True
        )

    # Filtrar ingredientes inactivos
    elif estado == "inactivos":

        insumos = insumos.filter(
            activo=False
        )

    # Ordenar alfabéticamente
    insumos = insumos.order_by("nombre")


    # Contar insumos activos
    total_insumos = Insumo.objects.filter(
        activo=True
    ).count()

    # Detectar insumos con stock bajo
    alertas_inventario = Insumo.objects.filter(
        activo=True,
        stock_actual__lte=F("stock_minimo")
    ).count()


    movimientos = (
        MovimientoInventario.objects
        .select_related("insumo", "usuario")
        .order_by("-fecha")[:10]
    )

    return render(
        request,
        "web/inventario.html",
        {
            "formulario": formulario,
            "formulario_movimiento": formulario_movimiento,
            "insumos": insumos,
            "total_insumos": total_insumos,
            "alertas_inventario": alertas_inventario,
            "movimientos": movimientos,
        }
    )


@personal_requerido
@require_POST
def cambiar_estado_insumo(request, insumo_id):

    insumo = get_object_or_404(
        Insumo,
        pk=insumo_id
    )

    # Cambiar el estado actual
    insumo.activo = not insumo.activo

    # Guardar únicamente el estado
    insumo.save(update_fields=["activo"])

    if insumo.activo:
        messages.success(
            request,
            f"El insumo {insumo.nombre} fue reactivado correctamente."
        )
    else:
        messages.success(
            request,
            f"El insumo {insumo.nombre} fue desactivado correctamente."
        )

    return redirect("inventario_operia")


@personal_requerido
def editar_insumo(request, insumo_id):

    insumo = get_object_or_404(
        Insumo,
        pk=insumo_id
    )

    if request.method == "POST":

        formulario = InsumoForm(
            request.POST,
            instance=insumo
        )

        if formulario.is_valid():

            formulario.save()

            messages.success(
                request,
                "Los datos del insumo se actualizaron correctamente."
            )

            return redirect("inventario_operia")

    else:

        formulario = InsumoForm(
            instance=insumo
        )

    return render(
        request,
        "web/editar_insumo.html",
        {
            "formulario": formulario,
            "insumo": insumo,
        }
    )


@personal_requerido
def proveedores_operia(request):

    proveedores = (
        Proveedor.objects
        .order_by("nombre")
    )

    ordenes = (
        OrdenCompraProveedor.objects
        .select_related("proveedor")
        .order_by("-fecha_creacion")
    )

    total_proveedores = proveedores.filter(
        activo=True
    ).count()

    ordenes_pendientes = ordenes.filter(
        estado="pendiente"
    ).count()

    ordenes_recibidas = ordenes.filter(
        estado="recibida"
    ).count()

    contexto = {
        "proveedores": proveedores,
        "ordenes": ordenes,
        "total_proveedores": total_proveedores,
        "ordenes_pendientes": ordenes_pendientes,
        "ordenes_recibidas": ordenes_recibidas,
        "form_proveedor": ProveedorForm(),
        "form_orden": OrdenCompraProveedorForm(),
        "form_detalle": DetalleOrdenProveedorForm(),
    }

    return render(
        request,
        "web/proveedores.html",
        contexto
    )



@personal_requerido
def ventas_operia(request):

    hoy = timezone.localdate()
    inicio_predeterminado = hoy - timedelta(days=29)

    fecha_inicio_texto = request.GET.get(
        "desde",
        inicio_predeterminado.isoformat()
    )

    fecha_fin_texto = request.GET.get(
        "hasta",
        hoy.isoformat()
    )

    metodo = request.GET.get("metodo", "todos")
    buscar = request.GET.get("buscar", "").strip()

    metodos_validos = {
        "todos",
        "efectivo",
        "debito",
        "credito",
        "transferencia",
    }

    if metodo not in metodos_validos:
        metodo = "todos"

    try:
        fecha_inicio = date.fromisoformat(fecha_inicio_texto)
        fecha_fin = date.fromisoformat(fecha_fin_texto)

        if fecha_inicio > fecha_fin:
            raise ValueError("Rango de fechas incorrecto")

        if (fecha_fin - fecha_inicio).days > 366:
            raise ValueError("Rango demasiado amplio")

    except (ValueError, TypeError):

        messages.warning(
            request,
            "Selecciona un período válido de hasta 366 días."
        )

        fecha_inicio = inicio_predeterminado
        fecha_fin = hoy

    fecha_inicio_texto = fecha_inicio.isoformat()
    fecha_fin_texto = fecha_fin.isoformat()

    ventas_base = Pedido.objects.filter(
        estado="entregado",
        estado_pago="confirmado"
    )

    ventas_periodo = ventas_base.filter(
        fecha_pedido__date__gte=fecha_inicio,
        fecha_pedido__date__lte=fecha_fin
    )

    if metodo != "todos":
        ventas_periodo = ventas_periodo.filter(
            metodo_pago=metodo
        )

    if buscar:

        if buscar.startswith("#"):
            buscar = buscar[1:]

        if buscar.isdigit():
            ventas_periodo = ventas_periodo.filter(
                pk=int(buscar)
            )
        else:
            ventas_periodo = ventas_periodo.none()

    subtotal = ExpressionWrapper(
        F("cantidad") * F("precio_unitario"),
        output_field=IntegerField()
    )

    detalles_periodo = DetallePedido.objects.filter(
        pedido__in=ventas_periodo
    )

    resumen = detalles_periodo.aggregate(
        ingresos=Sum(subtotal),
        unidades=Sum("cantidad")
    )

    ingresos_periodo = resumen["ingresos"] or 0
    unidades_vendidas = resumen["unidades"] or 0
    cantidad_ventas = ventas_periodo.count()

    if cantidad_ventas > 0:
        ticket_promedio = round(
            ingresos_periodo / cantidad_ventas
        )
    else:
        ticket_promedio = 0

    detalles_hoy = DetallePedido.objects.filter(
        pedido__estado="entregado",
        pedido__estado_pago="confirmado",
        pedido__fecha_pedido__date=hoy
    )

    ingresos_hoy = (
        detalles_hoy.aggregate(
            total=Sum(subtotal)
        )["total"] or 0
    )

    metodos_pago = []

    for codigo, nombre in Pedido.METODOS_PAGO:

        resultado_metodo = detalles_periodo.filter(
            pedido__metodo_pago=codigo
        ).aggregate(
            total=Sum(subtotal)
        )

        total_metodo = resultado_metodo["total"] or 0

        if ingresos_periodo > 0:
            porcentaje = round(
                (total_metodo / ingresos_periodo) * 100,
                1
            )
        else:
            porcentaje = 0

        metodos_pago.append({
            "codigo": codigo,
            "nombre": nombre,
            "total": total_metodo,
            "porcentaje": porcentaje
        })

    fecha_grafico = max(
        fecha_inicio,
        fecha_fin - timedelta(days=13)
    )

    ingresos_por_dia = (
        detalles_periodo
        .filter(
            pedido__fecha_pedido__date__gte=fecha_grafico
        )
        .annotate(
            dia=TruncDate("pedido__fecha_pedido")
        )
        .values("dia")
        .annotate(
            total=Sum(subtotal)
        )
        .order_by("dia")
    )

    totales_diarios = {
        registro["dia"]: registro["total"]
        for registro in ingresos_por_dia
    }

    datos_grafico = []
    dia_actual = fecha_grafico

    while dia_actual <= fecha_fin:

        datos_grafico.append({
            "fecha": dia_actual.strftime("%d/%m"),
            "total": totales_diarios.get(
                dia_actual,
                0
            )
        })

        dia_actual += timedelta(days=1)

    ventas_ordenadas = ventas_periodo.order_by(
        "-fecha_pedido",
        "-id"
    )

    paginador = Paginator(
        ventas_ordenadas,
        15
    )

    pagina = paginador.get_page(
        request.GET.get("pagina")
    )

    pedidos_pagina = list(
        pagina.object_list
    )

    ids_pedidos = [
        pedido.pk
        for pedido in pedidos_pagina
    ]

    totales_pedidos = (
        DetallePedido.objects
        .filter(
            pedido_id__in=ids_pedidos
        )
        .values("pedido_id")
        .annotate(
            total=Sum(subtotal)
        )
    )

    totales_por_pedido = {
        registro["pedido_id"]: registro["total"]
        for registro in totales_pedidos
    }

    for pedido in pedidos_pagina:

        pedido.total_venta = totales_por_pedido.get(
            pedido.pk,
            0
        )

    contexto = {
        "fecha_inicio": fecha_inicio_texto,
        "fecha_fin": fecha_fin_texto,
        "metodo_seleccionado": metodo,
        "buscar": buscar,
        "ingresos_periodo": ingresos_periodo,
        "ingresos_hoy": ingresos_hoy,
        "cantidad_ventas": cantidad_ventas,
        "unidades_vendidas": unidades_vendidas,
        "ticket_promedio": ticket_promedio,
        "metodos_pago": metodos_pago,
        "datos_grafico": datos_grafico,
        "pagina": pagina,
        "pedidos_pagina": pedidos_pagina
    }

    return render(
        request,
        "web/ventas.html",
        contexto
    )



@personal_requerido
def reportes_operia(request):

    hoy = timezone.localdate()
    inicio_predeterminado = hoy - timedelta(days=29)

    try:
        fecha_inicio = date.fromisoformat(
            request.GET.get(
                "desde",
                inicio_predeterminado.isoformat()
            )
        )

        fecha_fin = date.fromisoformat(
            request.GET.get(
                "hasta",
                hoy.isoformat()
            )
        )

        if fecha_inicio > fecha_fin:
            raise ValueError("Fechas invertidas")

        if (fecha_fin - fecha_inicio).days > 366:
            raise ValueError("Período demasiado amplio")

        if fecha_fin > hoy:
            raise ValueError("Fecha futura")

    except (ValueError, TypeError):

        messages.warning(
            request,
            "El período no es válido. Se muestran los últimos 30 días."
        )

        fecha_inicio = inicio_predeterminado
        fecha_fin = hoy

    pedidos = Pedido.objects.filter(
        fecha_pedido__date__range=(
            fecha_inicio,
            fecha_fin
        )
    )

    ventas = pedidos.filter(
        estado="entregado",
        estado_pago="confirmado"
    )

    subtotal = ExpressionWrapper(
        F("cantidad") * F("precio_unitario"),
        output_field=DecimalField(
            max_digits=20,
            decimal_places=2
        )
    )

    detalles = DetallePedido.objects.filter(
        pedido__in=ventas
    )

    resumen_ventas = detalles.aggregate(
        ingresos=Sum(subtotal),
        unidades=Sum("cantidad")
    )

    ingresos = resumen_ventas["ingresos"] or 0
    unidades = resumen_ventas["unidades"] or 0

    total_ventas = ventas.count()

    ticket_promedio = (
        round(ingresos / total_ventas)
        if total_ventas > 0
        else 0
    )

    total_pedidos = pedidos.count()

    entregados = pedidos.filter(
        estado="entregado"
    ).count()

    cancelados = pedidos.filter(
        estado="cancelado"
    ).count()

    tasa_entrega = (
        round(
            entregados * 100 / total_pedidos,
            1
        )
        if total_pedidos > 0
        else 0
    )

    estados_pedidos = []

    for codigo, nombre in Pedido.ESTADOS:

        cantidad = pedidos.filter(
            estado=codigo
        ).count()

        porcentaje = (
            round(
                cantidad * 100 / total_pedidos,
                1
            )
            if total_pedidos > 0
            else 0
        )

        estados_pedidos.append({
            "codigo": codigo,
            "nombre": nombre,
            "cantidad": cantidad,
            "porcentaje": porcentaje
        })

    metodos_pago = []

    for codigo, nombre in Pedido.METODOS_PAGO:

        total = detalles.filter(
            pedido__metodo_pago=codigo
        ).aggregate(
            importe=Sum(subtotal)
        )["importe"] or 0

        porcentaje = (
            round(
                total * 100 / ingresos,
                1
            )
            if ingresos > 0
            else 0
        )

        metodos_pago.append({
            "codigo": codigo,
            "nombre": nombre,
            "total": total,
            "porcentaje": porcentaje
        })

    productos_vendidos = list(
        detalles.values(
            "producto_id",
            "producto__nombre"
        )
        .annotate(
            unidades=Sum("cantidad"),
            ingresos=Sum(subtotal)
        )
        .order_by(
            "-unidades",
            "-ingresos"
        )[:6]
    )

    max_unidades = (
        productos_vendidos[0]["unidades"]
        if productos_vendidos
        else 0
    )

    for producto in productos_vendidos:

        producto["porcentaje"] = (
            round(
                producto["unidades"] * 100 / max_unidades,
                1
            )
            if max_unidades > 0
            else 0
        )

    fecha_grafico = max(
        fecha_inicio,
        fecha_fin - timedelta(days=13)
    )

    registros_diarios = (
        detalles.filter(
            pedido__fecha_pedido__date__gte=fecha_grafico
        )
        .annotate(
            dia=TruncDate("pedido__fecha_pedido")
        )
        .values("dia")
        .annotate(
            total=Sum(subtotal)
        )
        .order_by("dia")
    )

    ingresos_por_fecha = {
        registro["dia"]: registro["total"]
        for registro in registros_diarios
    }

    grafico_ingresos = []

    dia = fecha_grafico

    while dia <= fecha_fin:

        grafico_ingresos.append({
            "fecha": dia.strftime("%d/%m"),
            "total": float(
                ingresos_por_fecha.get(dia, 0)
            )
        })

        dia += timedelta(days=1)

    insumos_activos = Insumo.objects.filter(
        activo=True
    )

    insumos_bajo_minimo = insumos_activos.filter(
        stock_actual__lte=F("stock_minimo")
    )

    alertas_stock = insumos_bajo_minimo.count()

    insumos_criticos = list(
        insumos_bajo_minimo.order_by(
            "stock_actual",
            "nombre"
        )[:6]
    )

    movimientos = MovimientoInventario.objects.filter(
        fecha__date__range=(
            fecha_inicio,
            fecha_fin
        )
    )

    entradas = movimientos.filter(
        tipo="entrada"
    ).count()

    salidas = movimientos.filter(
        tipo="salida"
    ).count()

    ordenes_periodo = OrdenCompraProveedor.objects.filter(
        fecha_creacion__date__range=(
            fecha_inicio,
            fecha_fin
        )
    )

    ordenes_pendientes = ordenes_periodo.filter(
        estado="pendiente"
    ).count()

    ordenes_recibidas = OrdenCompraProveedor.objects.filter(
        estado="recibida",
        fecha_recepcion__date__range=(
            fecha_inicio,
            fecha_fin
        )
    )

    total_ordenes_recibidas = ordenes_recibidas.count()

    importe_compra = ExpressionWrapper(
        F("cantidad") * F("precio_unitario"),
        output_field=DecimalField(
            max_digits=20,
            decimal_places=2
        )
    )

    compras_recibidas = (
        DetalleOrdenProveedor.objects.filter(
            orden__in=ordenes_recibidas
        )
        .aggregate(
            total=Sum(importe_compra)
        )["total"] or 0
    )

    contexto = {
        "fecha_inicio": fecha_inicio.isoformat(),
        "fecha_fin": fecha_fin.isoformat(),

        "ingresos": ingresos,
        "total_ventas": total_ventas,
        "unidades": unidades,
        "ticket_promedio": ticket_promedio,

        "total_pedidos": total_pedidos,
        "entregados": entregados,
        "cancelados": cancelados,
        "tasa_entrega": tasa_entrega,
        "estados_pedidos": estados_pedidos,

        "metodos_pago": metodos_pago,
        "productos_vendidos": productos_vendidos,
        "grafico_ingresos": grafico_ingresos,

        "total_insumos": insumos_activos.count(),
        "alertas_stock": alertas_stock,
        "insumos_criticos": insumos_criticos,
        "entradas": entradas,
        "salidas": salidas,

        "ordenes_pendientes": ordenes_pendientes,
        "total_ordenes_recibidas": total_ordenes_recibidas,
        "compras_recibidas": compras_recibidas,
    }

    return render(
        request,
        "web/reportes.html",
        contexto
    )

