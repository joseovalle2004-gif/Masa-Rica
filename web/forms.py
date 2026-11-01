

from django import forms

from .models import (
    Insumo,
    MovimientoInventario,
    Proveedor,
    OrdenCompraProveedor,
    DetalleOrdenProveedor,
)

class InsumoForm(forms.ModelForm):

    class Meta:
        model = Insumo

        fields = [
            "nombre",
            "unidad_medida",
            "stock_minimo",
        ]

        labels = {
            "nombre": "Nombre del insumo",
            "unidad_medida": "Unidad de medida",
            "stock_minimo": "Stock mínimo",
        }

        widgets = {
            "nombre": forms.TextInput(
                attrs={
                    "class": "inventario-input",
                    "placeholder": "Ej: Harina",
                }
            ),

            "unidad_medida": forms.Select(
                attrs={
                    "class": "inventario-input",
                }
            ),

            "stock_minimo": forms.NumberInput(
                attrs={
                    "class": "inventario-input",
                    "min": "0",
                    "step": "0.001",
                }
            ),
        }

    def clean_stock_minimo(self):

        stock_minimo = self.cleaned_data["stock_minimo"]

        if stock_minimo < 0:
            raise forms.ValidationError(
                "El stock mínimo no puede ser negativo."
            )

        return stock_minimo



    def clean_unidad_medida(self):

        nueva_unidad = self.cleaned_data["unidad_medida"]

        # Comprobar si estamos editando un insumo existente
        if self.instance.pk:

            # Consultar la unidad original en la base de datos
            unidad_original = (
                Insumo.objects
                .filter(pk=self.instance.pk)
                .values_list("unidad_medida", flat=True)
                .first()
            )

            # Comprobar si se intenta cambiar la unidad
            if (
                unidad_original is not None
                and nueva_unidad != unidad_original
            ):

                # Impedir el cambio si existen movimientos
                tiene_movimientos = (
                    MovimientoInventario.objects
                    .filter(insumo_id=self.instance.pk)
                    .exists()
                )

                if tiene_movimientos:

                    raise forms.ValidationError(
                        "No puedes cambiar la unidad de medida "
                        "porque este insumo ya tiene movimientos "
                        "de inventario registrados."
                    )

        return nueva_unidad



class MovimientoInventarioForm(forms.ModelForm):

    class Meta:
        model = MovimientoInventario

        fields = [
            "insumo",
            "tipo",
            "cantidad",
            "motivo",
        ]

        labels = {
            "insumo": "Ingrediente o material",
            "tipo": "Tipo de movimiento",
            "cantidad": "Cantidad",
            "motivo": "Motivo del movimiento",
        }

        widgets = {
            "insumo": forms.Select(
                attrs={
                    "class": "inventario-input",
                }
            ),

            "tipo": forms.Select(
                attrs={
                    "class": "inventario-input",
                }
            ),

            "cantidad": forms.NumberInput(
                attrs={
                    "class": "inventario-input",
                    "min": "0.001",
                    "step": "0.001",
                    "placeholder": "Ej: 25",
                }
            ),

            "motivo": forms.TextInput(
                attrs={
                    "class": "inventario-input",
                    "placeholder": "Ej: Compra de mercadería",
                }
            ),
        }

    def __init__(self, *args, **kwargs):

        super().__init__(*args, **kwargs)

        self.fields["insumo"].queryset = (
            Insumo.objects.filter(activo=True)
            .order_by("nombre")
        )

    def clean_cantidad(self):

        cantidad = self.cleaned_data["cantidad"]

        if cantidad <= 0:
            raise forms.ValidationError(
                "La cantidad debe ser mayor que cero."
            )

        return cantidad


class ProveedorForm(forms.ModelForm):

    class Meta:
        model = Proveedor

        fields = [
            "nombre",
            "rut",
            "contacto",
            "telefono",
            "correo",
            "direccion",
            "observaciones",
            "activo",
        ]

        labels = {
            "nombre": "Nombre del proveedor",
            "rut": "RUT del proveedor",
            "contacto": "Persona de contacto",
            "telefono": "Teléfono",
            "correo": "Correo electrónico",
            "direccion": "Dirección",
            "observaciones": "Observaciones",
            "activo": "Proveedor activo",
        }

        widgets = {
            "nombre": forms.TextInput(attrs={
                "class": "proveedores-input",
                "placeholder": "Ej: Distribuidora del Sur",
            }),
            "rut": forms.TextInput(attrs={
                "class": "proveedores-input",
                "placeholder": "Ej: 12345678-5",
            }),
            "contacto": forms.TextInput(attrs={
                "class": "proveedores-input",
                "placeholder": "Nombre del encargado",
            }),
            "telefono": forms.TextInput(attrs={
                "class": "proveedores-input",
                "placeholder": "Ej: +56912345678",
            }),
            "correo": forms.EmailInput(attrs={
                "class": "proveedores-input",
                "placeholder": "correo@empresa.cl",
            }),
            "direccion": forms.TextInput(attrs={
                "class": "proveedores-input",
                "placeholder": "Dirección del proveedor",
            }),
            "observaciones": forms.Textarea(attrs={
                "class": "proveedores-input",
                "rows": 3,
                "placeholder": "Información adicional",
            }),
        }


class OrdenCompraProveedorForm(forms.ModelForm):

    class Meta:
        model = OrdenCompraProveedor

        fields = [
            "proveedor",
            "tipo",
            "observaciones",
        ]

        labels = {
            "proveedor": "Proveedor",
            "tipo": "Modalidad de compra",
            "observaciones": "Observaciones",
        }

        widgets = {
            "proveedor": forms.Select(attrs={
                "class": "proveedores-input",
            }),
            "tipo": forms.Select(attrs={
                "class": "proveedores-input",
            }),
            "observaciones": forms.Textarea(attrs={
                "class": "proveedores-input",
                "rows": 3,
                "placeholder": "Detalles de la compra",
            }),
        }

    def __init__(self, *args, **kwargs):

        super().__init__(*args, **kwargs)

        self.fields["proveedor"].queryset = (
            Proveedor.objects.filter(activo=True)
            .order_by("nombre")
        )


class DetalleOrdenProveedorForm(forms.ModelForm):

    class Meta:
        model = DetalleOrdenProveedor

        fields = [
            "insumo",
            "cantidad",
            "precio_unitario",
        ]

        labels = {
            "insumo": "Insumo",
            "cantidad": "Cantidad",
            "precio_unitario": "Precio por unidad de medida",
        }

        widgets = {
            "insumo": forms.Select(attrs={
                "class": "proveedores-input",
            }),
            "cantidad": forms.NumberInput(attrs={
                "class": "proveedores-input",
                "min": "0.001",
                "step": "0.001",
                "placeholder": "Ej: 25",
            }),
            "precio_unitario": forms.NumberInput(attrs={
                "class": "proveedores-input",
                "min": "0",
                "step": "0.01",
                "placeholder": "Ej: 1500",
            }),
        }

    def __init__(self, *args, **kwargs):

        super().__init__(*args, **kwargs)

        self.fields["insumo"].queryset = (
            Insumo.objects.filter(activo=True)
            .order_by("nombre")
        )
