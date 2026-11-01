# Masa Rica

Sistema web de gestión y venta de productos para Masa Rica, emprendimiento familiar dedicado a la elaboración y comercialización de empanadas y preparaciones tradicionales.

## Características principales

- Catálogo de productos y categorías.
- Carrito de compras con cálculo automático de precios.
- Registro e inicio de sesión de clientes.
- Gestión y seguimiento de pedidos.
- Panel de administración.
- Control de inventario.
- Integración con métodos de pago.
- Notificaciones automáticas por correo electrónico.
- Validación de formularios.
- Base de datos SQLite.
- Gestión de usuarios y permisos.

## Tecnologías utilizadas

- Python
- Django 6.0.7
- SQLite
- HTML5
- CSS3
- JavaScript
- WhiteNoise
- Transbank SDK
- Gmail SMTP

## Estructura del proyecto

```text
Masa-Rica/
│
├── config/
├── web/
│   ├── migrations/
│   ├── static/
│   └── templates/
│
├── productos_iniciales.json
├── manage.py
├── requirements.txt
├── .env.example
└── .gitignore
```

## Instalación

### 1. Descargar el proyecto

Descargar o clonar este repositorio.

### 2. Crear un entorno virtual

```bash
python -m venv .venv
```

Activar el entorno virtual:

Windows:

```bash
.venv\Scripts\activate
```

Linux:

```bash
source .venv/bin/activate
```

### 3. Instalar dependencias

```bash
pip install -r requirements.txt
```

### 4. Configurar las variables de entorno

Crear un archivo `.env` a partir de `.env.example`.

Completar las variables necesarias con las credenciales propias del entorno.

No compartir ni publicar el archivo `.env`.

### 5. Crear las tablas de la base de datos

```bash
python manage.py migrate
```

### 6. Cargar los productos iniciales

En una instalación nueva, cargar el catálogo original:

```bash
python manage.py loaddata productos_iniciales.json
```

El archivo contiene los 27 productos iniciales de Masa Rica.

### 7. Crear un administrador

```bash
python manage.py createsuperuser
```

### 8. Ejecutar el servidor

```bash
python manage.py runserver
```

Abrir en el navegador:

http://127.0.0.1:8000/

## Seguridad

- Las credenciales se administran mediante variables de entorno.
- El archivo `.env` no debe publicarse.
- Las bases de datos locales y los respaldos están excluidos del repositorio.
- Las contraseñas y configuraciones privadas no deben compartirse.

## Proyecto

Masa Rica es un proyecto desarrollado para apoyar la gestión y operación de un emprendimiento familiar, facilitando la administración de productos, clientes y pedidos.

**Repositorio:** joseovalle2004-gif/Masa-Rica
