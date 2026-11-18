# Configuración de la automatización de X — Mundo al Día

Esta automatización está aislada de los flujos de Facebook, Instagram, el sitio web y videos.

## Secretos de GitHub Actions

En el repositorio, abre **Settings → Secrets and variables → Actions → New repository secret** y crea:

- `OPENAI_API_KEY`: clave de API de OpenAI para redactar el post en español.
- `X_USER_ACCESS_TOKEN`: token OAuth 2.0 de usuario de X para la cuenta Mundo al Día.

El token de X debe pertenecer a una aplicación de desarrollador autorizada por el propietario de la cuenta y tener los permisos de usuario necesarios para leer los posts recientes y publicar: `users.read`, `tweet.read` y `tweet.write`. La aplicación debe usar autenticación de usuario OAuth 2.0 (Authorization Code with PKCE) y el propietario debe autorizar expresamente estas acciones.

## Variable de seguridad

En **Settings → Secrets and variables → Actions → Variables**, crea:

- `X_AUTO_PUBLISH_ENABLED` = `false` inicialmente.

Solo después de validar credenciales, revisar el contenido de prueba y dar aprobación expresa, cambia esta variable a `true` para permitir las publicaciones programadas. El disparo manual también tiene una opción explícita de publicación; déjala desactivada para pruebas.

## Horario

El workflow tiene tres ejecuciones diarias en UTC: 12:00, 17:00 y 23:00. Equivalen aproximadamente a 7/8 a. m., 12/1 p. m. y 6/7 p. m. en la hora del Este, según el horario de verano.

## Alcance y límites actuales

- Fuentes RSS: DW Español, BBC News Mundo y France 24 Español.
- Una publicación por ejecución, con enlace a la fuente original.
- Comprueba los últimos posts de la cuenta para evitar repetir un enlace reciente.
- La primera versión utiliza titular y descripción RSS; no sustituye una verificación editorial independiente de varias fuentes ni una revisión de derechos de imágenes.
- No automatiza likes, follows, respuestas no solicitadas ni mensajes directos.
- No se publica nada si el interruptor está apagado.
- Los workflows programados de GitHub solo se ejecutan desde la rama predeterminada; este PR debe revisarse y fusionarse antes de que empiece el horario automático.
