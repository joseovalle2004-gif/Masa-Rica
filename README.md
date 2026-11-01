# Masa Rica – Operia

Sistema web de gestión y venta de productos desarrollado para Masa Rica, un emprendimiento familiar dedicado a la elaboración y comercialización de empanadas y preparaciones tradicionales.

El proyecto permite administrar las ventas y operaciones del negocio mediante una aplicación web desarrollada con Django.

## Características principales

- Catálogo de productos organizado por categorías.
- Carrito de compras con cálculo automático de precios.
- Registro e inicio de sesión de clientes.
- Gestión y seguimiento de pedidos.
- Panel administrativo para el personal autorizado.
- Control de inventario e insumos.
- Gestión de proveedores.
- Integración con métodos de pago, incluyendo Transbank Webpay.
- Notificaciones de pedidos mediante correo electrónico.
- Validación de formularios y control de permisos.
- Reportes de gestión.
- Base de datos SQLite.

## Tecnologías utilizadas

- Python 3.12 o superior.
- Django 6.0.7.
- SQLite.
- HTML5.
- CSS3.
- JavaScript.
- WhiteNoise.
- Transbank SDK.
- Gmail SMTP.

## Estructura del proyecto

```text
Masa-Rica/
├── config/
├── web/
│   ├── migrations/
│   ├── static/
│   └── templates/
├── productos_iniciales.json
├── manage.py
├── requirements.txt
├── .env.example
├── .gitignore
└── README.md
```

## Requisitos previos

- Tener instalado Python 3.12 o superior.
- Tener acceso a una terminal, como PowerShell o la terminal de Visual Studio Code.
- Disponer de conexión a internet para instalar las dependencias.

## Instalación del proyecto

### 1. Descargar el repositorio

Descargar el proyecto desde GitHub utilizando la opción **Code → Download ZIP**, o clonarlo mediante Git.

Extraer el archivo ZIP y abrir en Visual Studio Code la carpeta que contiene `manage.py`.

### 2. Crear el entorno virtual

Ejecutar:

```powershell
python -m venv .venv
```

Activar el entorno virtual en Windows PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
```

En Windows CMD:

```cmd
.venv\Scripts\activate.bat
```

En Linux o macOS:

```bash
source .venv/bin/activate
```

### 3. Instalar las dependencias

Con el entorno virtual activado:

```powershell
python -m pip install -r requirements.txt
```

### 4. Configurar las variables de entorno

Crear una copia del archivo `.env.example` con el nombre `.env`.

En PowerShell:

```powershell
Copy-Item .env.example .env
```

El archivo `.env` debe contener las variables de configuración del proyecto:

```dotenv
DJANGO_SECRET_KEY=REEMPLAZAR_CON_UNA_CLAVE_SEGURA
DJANGO_DEBUG=True
DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1
MASA_RICA_EMAIL=
MASA_RICA_EMAIL_PASSWORD=
MASA_RICA_PEDIDOS_EMAIL=
```

Para generar una clave secreta aleatoria, ejecutar:

```powershell
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

Copiar el resultado y reemplazar `REEMPLAZAR_CON_UNA_CLAVE_SEGURA` en el archivo `.env`.

Las variables de correo electrónico son necesarias para habilitar las notificaciones mediante Gmail SMTP. Para una instalación local de prueba pueden permanecer vacías, aunque el envío de correos no estará disponible sin configurarlas.

**Nunca publicar el archivo `.env` ni compartir claves privadas.**

### 5. Crear la base de datos

Ejecutar:

```powershell
python manage.py migrate
```

Esto creará las tablas necesarias en SQLite.

### 6. Cargar los productos iniciales

En una instalación nueva, ejecutar:

```powershell
python manage.py loaddata productos_iniciales.json
```

Este archivo contiene los **27 productos iniciales de Masa Rica**.

No se recomienda cargar esta información en una base de datos que ya tenga productos, sin revisar previamente los identificadores existentes.

### 7. Crear una cuenta de administrador

Ejecutar:

```powershell
python manage.py createsuperuser
```

Ingresar el nombre de usuario, correo electrónico y contraseña solicitados.

### 8. Ejecutar el servidor

Ejecutar:

```powershell
python manage.py runserver
```

Abrir la aplicación en el navegador:

http://127.0.0.1:8000/

Para ingresar al administrador de Django:

http://127.0.0.1:8000/admin/

## Comprobaciones del proyecto

Verificar la configuración de Django:

```powershell
python manage.py check
```

Verificar si existen cambios de modelos pendientes de migración:

```powershell
python manage.py makemigrations --check --dry-run
```

Verificar que todas las migraciones estén aplicadas:

```powershell
python manage.py migrate --check
```

## Seguridad

- Las claves y credenciales privadas se almacenan mediante variables de entorno.
- El archivo `.env` está excluido del repositorio.
- Las bases de datos locales y los respaldos no deben publicarse.
- Se utilizan mecanismos de autenticación y permisos de Django.
- Los archivos privados y los datos sensibles deben permanecer fuera del repositorio público.

## Pruebas realizadas

Se realizó una instalación nueva descargando el proyecto desde GitHub y se comprobó:

- Instalación de dependencias.
- Creación de las tablas SQLite.
- Importación de los 27 productos iniciales.
- Ejecución de la página web.
- Acceso al panel de administración.
- Acceso a las secciones internas de Operia.
- Comprobación de configuración y migraciones sin errores.

## Sitio web

**Aplicación publicada:** https://jose21.pythonanywhere.com/

**Repositorio:** https://github.com/joseovalle2004-gif/Masa-Rica

## Objetivo del proyecto

Masa Rica – Operia busca facilitar la digitalización de un emprendimiento familiar mediante herramientas para la venta de productos, administración de pedidos, gestión de inventario y apoyo a la toma de decisiones.
