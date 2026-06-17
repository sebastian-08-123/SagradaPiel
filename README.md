# ⚽ GoalShop — Tienda de Camisetas de Fútbol

## 📁 Estructura de archivos

```
goalshop/
│
├── app.py              ← Servidor Flask (backend principal)
├── requirements.txt    ← Dependencias Python
│
├── index.html          ← Catálogo / Página principal
├── login.html          ← Login y Registro
├── carrito.html        ← Carrito de compras
├── checkout.html       ← Finalizar compra
│
├── style_main.css      ← Estilos de index y navbar
├── style_auth.css      ← Estilos de login/registro
├── style_carrito.css   ← Estilos de carrito y checkout
│
├── tienda.db           ← Base de datos SQLite (se crea automáticamente)
│
└── *.jpeg              ← TUS IMÁGENES aquí (ver abajo)
```

---

## 🚀 Instalación y arranque

### 1. Instalar Python 3.8+
Descarga desde: https://www.python.org/downloads/

### 2. Instalar Flask
```bash
pip install flask
```

### 3. Agregar tus imágenes
Coloca tus imágenes `.jpeg` en la **misma carpeta** con estos nombres exactos:
```
real_madrid.jpeg
barcelona.jpeg
man_city.jpeg
liverpool.jpeg
psg.jpeg
bayern.jpeg
juventus.jpeg
argentina.jpeg
brasil.jpeg
atletico.jpeg
chelsea.jpeg
inter.jpeg
```

### 4. Ejecutar el servidor
```bash
python app.py
```

### 5. Abrir en el navegador
```
http://localhost:5000
```

---

## 🌟 Funcionalidades

| Función              | Descripción                                  |
|----------------------|----------------------------------------------|
| **Catálogo**         | Grid de 12 camisetas con filtros por liga     |
| **Búsqueda**         | Buscar por nombre desde la navbar             |
| **Filtros**          | Filtrar por liga (La Liga, Premier, etc.)     |
| **Registro**         | Crear cuenta con nombre, email y contraseña  |
| **Login/Logout**     | Sesión con cookies seguras                   |
| **Carrito**          | Agregar, quitar, cambiar cantidades           |
| **Checkout**         | Formulario de entrega y método de pago       |
| **Confirmación**     | Página de pedido confirmado con número       |
| **Base de datos**    | SQLite con usuarios, productos y pedidos     |

---

## 🗃️ Base de datos (SQLite)

Se crea automáticamente como `tienda.db` con estas tablas:
- `usuarios` — Cuentas registradas
- `productos` — Camisetas con liga, precio e imagen
- `pedidos` — Órdenes realizadas
- `pedido_items` — Detalle de cada pedido

---

## 🎨 Personalizar imágenes

Las imágenes deben ser `.jpeg` y estar en la raíz del proyecto.
Si una imagen no se encuentra, se mostrará un placeholder automático.

Tamaño recomendado: **600×600 px** (cuadrado)

---

## 🔧 Personalizar productos

Los productos se insertan automáticamente la primera vez.
Para cambiar precios o agregar más, edita la lista en `app.py` dentro de `init_db()`.

---

## 📱 Responsive

El sitio es completamente responsive para móviles, tablets y desktop.
