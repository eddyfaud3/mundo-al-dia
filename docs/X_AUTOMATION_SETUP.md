# Configuración de la automatización de X — Mundo al Día

Esta automatización está aislada de los flujos de Facebook, Instagram, el sitio web y videos.

## Secretos de GitHub Actions

En el repositorio, abre **Settings → Secrets and variables → Actions → New repository secret** y crea:

- `OPENAI_API_KEY`: clave de API de OpenAI para redactar el post en español.
- `X_USER_ACCESS_TOKEN`: token OAuth 2.0 de usuario de X para la cuenta Mundo al Día.

El token de X debe pertenecer a una aplicación de desarrollador autorizada por el propietario de la cuenta y tener los permisos `users.read`, `tweet.read` y `tweet.write`. Usa OAuth 2.0 Authorization Code with PKCE y autoriza expresamente la aplicación. Nunca pegues tokens ni claves en el código, en un issue ni en este chat.

## Interruptor de publicación

En **Settings → Secrets and variables → Actions → Variables**, crea:

- `X_AUTO_PUBLISH_ENABLED` = `false`.

Debe permanecer en `false` durante las pruebas. La opción manual `publish` también debe quedar desactivada en los ensayos. Solo el propietario debe cambiar el interruptor a `true` después de revisar un borrador, confirmar las credenciales y aprobar el primer post real.

## Horario

El workflow tiene tres ejecuciones diarias en UTC: 12:00, 17:00 y 23:00. En la hora del Este corresponden aproximadamente a 7 a. m., mediodía y 6 p. m. durante el horario estándar; en horario de verano se desplazan una hora. GitHub Actions usa UTC, por lo que el horario local cambia con el DST.

## Reglas editoriales y límites

- Fuentes RSS: DW Español, BBC News Mundo y France 24 Español.
- Solo se procesa una noticia si los titulares tienen coincidencia suficiente entre al menos dos medios distintos. Si no hay coincidencia, el flujo se detiene sin publicar.
- El enlace incluido es el de la noticia original del medio seleccionado.
- OpenAI redacta en español usando los datos de la nota enlazada; no debe inventar datos, citas ni cifras.
- Antes de publicar, consulta los últimos 20 posts de la cuenta para evitar repetir el mismo enlace.
- No adjunta imágenes ni videos; no se ha comprobado ningún derecho de uso de medios.
- No sustituye la verificación editorial humana, especialmente en noticias de última hora, conflictos, víctimas o temas sensibles.
- No automatiza likes, follows, respuestas no solicitadas ni mensajes directos.
- Los workflows programados de GitHub solo se ejecutan desde la rama predeterminada; este PR debe revisarse y fusionarse antes de que empiece el horario automático.
- Sin `OPENAI_API_KEY`, el proceso se detiene. Sin `X_USER_ACCESS_TOKEN`, la publicación se detiene. La publicación también queda bloqueada mientras el interruptor esté apagado.
