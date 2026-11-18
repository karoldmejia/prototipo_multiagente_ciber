# Políticas de Seguridad de la Información

## 1. Introducción
Este documento describe las políticas de seguridad aplicables a los sistemas de la organización. Su propósito es establecer directrices claras para la protección de datos, el acceso autorizado y la respuesta a incidentes.

## 2. Alcance
Las políticas aquí definidas aplican a todos los sistemas, redes y personal de la organización, incluidos los sistemas basados en nube y los despliegues locales.

## 3. Control de Acceso
- **Principio de mínimo privilegio**: Los usuarios y procesos deben tener solo los permisos necesarios para funciones específicas.
- **Autenticación multifactor (MFA)**: Se requiere MFA para acceder a sistemas críticos.
- **Revisiones periódicas**: Los derechos de acceso se revisan cada 90 días.

## 4. Protección de Datos
- **Cifrado en reposo**: Todos los datos sensibles deben cifrarse usando AES-256 o superior.
- **Cifrado en tránsito**: Todos los comunicaciones deben usar TLS 1.2+.
- **Clasificación de datos**: Los datos se clasifican como públicos, internos, confidenciales o restringidos.

## 5. Gestión de Incidentes
- **Detección**: Los sistemas de monitoreo deben alertar sobre actividades sospechosas en menos de 5 minutos.
- **Notificación**: Los incidentes críticos deben notificarse al equipo de seguridad dentro de 1 hora.
- **Recuperación**: Se deben tener planes de respaldo y recuperación probados cada 6 meses.

## 6. Capacidad de Auditoría
- **Logs de auditoría**: Todos los accesos y modificaciones deben registrarse con marca de tiempo, usuario y acción.
- **Retención**: Los logs deben retenerse por un mínimo de 12 meses.
- **Acceso a logs**: Solo personal autorizado con credenciales específicas puede acceder a los logs de auditoría.

---

*Última actualización: 2024-01-15*