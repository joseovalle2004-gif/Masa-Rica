from django.test import TestCase
from .models import Producto


class ProductoModelTest(TestCase):

    def test_crear_producto(self):
        producto = Producto.objects.create(
            nombre="Empanada de pino",
            categoria="empanadas",
            tipo_venta="diaria",
            precio=2500,
            disponible=True
        )

        self.assertEqual(producto.nombre, "Empanada de pino")
        self.assertEqual(producto.precio, 2500)
        self.assertTrue(producto.disponible)
        self.assertEqual(str(producto), "Empanada de pino")

    
    def test_actualizar_precio_producto(self):
        producto = Producto.objects.create(
            nombre="Empanada de queso",
            categoria="empanadas",
            tipo_venta="diaria",
            precio=2200,
            disponible=True
        )

        producto.precio = 2500
        producto.save()

        producto.refresh_from_db()

        self.assertEqual(producto.precio, 2500)

    
    def test_eliminar_producto(self):
        producto = Producto.objects.create(
            nombre="Empanada de prueba",
            categoria="empanadas",
            tipo_venta="diaria",
            precio=2000,
            disponible=True
        )

        producto_id = producto.id

        producto.delete()

        self.assertFalse(
            Producto.objects.filter(id=producto_id).exists()
        )
