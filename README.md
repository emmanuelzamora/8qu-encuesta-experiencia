# Encuesta de Experiencia 8Qu

Aplicación Flask para Render con PostgreSQL, encuesta pública y panel de resultados protegido.

## Publicar

1. Crear un repositorio privado en GitHub, por ejemplo `8qu-encuesta-experiencia`, y subir el contenido de esta carpeta a la raíz.
2. Crear una base PostgreSQL en Render o utilizar otra base PostgreSQL autorizada. **No usar la base de ventas de NODON sin separar permisos/esquemas.**
3. En Render: New > Blueprint y seleccionar el repositorio; Render detecta `render.yaml`.
4. Configurar `DATABASE_URL` (cadena de conexión de PostgreSQL), `ADMIN_USER`, `ADMIN_PASSWORD` (larga y única). `PHONE_HASH_SECRET` se genera automáticamente y debe mantenerse constante.
5. Esperar a que Render construya la app y cree las tablas. Abrir la URL asignada y `/admin` para el tablero.

## Seguridad y privacidad

- El teléfono se transforma con HMAC-SHA256; no se almacena en texto claro. Se limita a una evaluación por celular y sede cada 7 días mediante bloqueo transaccional.
- Esto **no verifica la titularidad** del número. Para una campaña pública masiva agregar OTP por SMS, rate limiting por IP y CAPTCHA.
- El panel usa autenticación básica HTTP; Render ofrece HTTPS, pero para operación continua conviene implementar cuentas con sesiones y roles.
- Antes de abrir al público, completar el aviso de privacidad con responsable, domicilio, contacto, finalidades, plazos de conservación y derechos ARCO, y validar con asesoría legal.
- El backend no depende de Netlify. No publiques secretos en GitHub.
- Para conservar el diseño original, se utilizan los archivos oficiales proporcionados por 8Qu y una imagen de Ochu.

## Prueba local

```bash
pip install -r requirements.txt
export DATABASE_URL='postgresql://...'
export PHONE_HASH_SECRET='una-cadena-aleatoria-de-32-caracteres-o-mas'
export ADMIN_USER='admin'
export ADMIN_PASSWORD='una-clave-segura'
python init_db.py
python app.py
```
