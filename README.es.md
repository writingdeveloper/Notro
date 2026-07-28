<p align="center">
  <img src="docs/icon.png" width="88" alt="Notro">
</p>

<h1 align="center">Notro</h1>

<p align="center">
  <b>Emojis personalizados y archivos grandes en Discord — sin Nitro y sin tocar el cliente de Discord.</b>
</p>

<p align="center">
  <a href="../../releases/latest"><img src="https://img.shields.io/github/v/release/writingdeveloper/Notro?label=download&color=5865F2" alt="Última versión"></a>
  <a href="../../releases"><img src="https://img.shields.io/github/downloads/writingdeveloper/Notro/total?color=57F287" alt="Descargas"></a>
  <img src="https://img.shields.io/badge/Windows-10%20%7C%2011-0078D4" alt="Windows 10 / 11">
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-MIT-green" alt="MIT"></a>
</p>

<p align="center"><a href="README.md">English</a> | <a href="README.ko.md">한국어</a> | <a href="README.ja.md">日本語</a> | <a href="README.zh.md">中文</a> | <b>Español</b></p>

---

Dos cosas por las que Discord cobra, resueltas desde fuera de la aplicación:

- **Tu imagen pesa 14 MB y el límite gratuito es de 10 MB.** Notro lo nota en cuanto la
  copias, la reduce y la devuelve al portapapeles. Tú solo pulsas <kbd>Ctrl</kbd>+<kbd>V</kbd>.
- **Quieres usar emojis personalizados en cualquier parte.** Pulsa
  <kbd>Ctrl</kbd>+<kbd>Shift</kbd>+<kbd>E</kbd>, elige uno y aparece en el cuadro de mensaje.

**No parchea, no inyecta y no inicia sesión en nada.** Notro es una aplicación de bandeja
que prepara el portapapeles y pulsa <kbd>Ctrl</kbd>+<kbd>V</kbd> por ti — el mismo tipo de
automatización de entrada que el panel de emojis de Windows (<kbd>Win</kbd>+<kbd>.</kbd>).
Nunca modifica el cliente de Discord ni ve tu cuenta o tu token. La contrapartida honesta:
quien lo recibe ve tus emojis como imágenes adjuntas, no como emojis integrados.

<p align="center">
  <img src="docs/demo.gif" width="620" alt="El selector de Notro: al escribir se filtran en vivo los emojis personalizados y las flechas recorren la cuadrícula">
</p>

<p align="center"><sub>Interfaz real, biblioteca real: filtra al escribir, las flechas recorren y Enter pega.</sub></p>

<p align="center">
  <a href="../../releases/latest"><b>⬇ Descargar NotroSetup.exe</b></a><br>
  <sub>Sin permisos de administrador. Se instala en tu carpeta de usuario y se desinstala desde Configuración → Aplicaciones.</sub>
</p>

---

## El selector

<kbd>Ctrl</kbd>+<kbd>Shift</kbd>+<kbd>E</kbd> en cualquier sitio abre una ventana oscura
junto al cursor, con las pestañas **Emojis / Stickers / GIF**.

**Salen del tamaño que tienen los emojis de verdad.** Discord dibuja una imagen adjunta a su
tamaño real en píxeles, así que una biblioteca con un GIF de 20×20 junto a un PNG de
1080×1080 pegaría uno como una mota y el otro como una fotografía. Notro iguala el lado más
largo justo antes de pegar: **48 px** para emojis (el tamaño de un emoji personalizado en
grande), **160 px** para stickers y el tamaño original para los GIF. **Los archivos de tu
biblioteca no se modifican**; solo se redimensiona la copia que va al portapapeles.

**Añadir emojis** — pega la URL de *«Copiar enlace»*, o el texto `<:nombre:id>` que
obtienes al copiar un emoji directamente de un mensaje; arrastra y suelta archivos de
imagen; señala una **carpeta vigilada**; o simplemente crea una carpeta dentro de
`%APPDATA%\Notro\assets` y se convertirá en una colección sin ningún paso de registro.

**Volver a encontrarlos** — busca por nombre o palabra clave, incluidas las **consonantes
iniciales del coreano** (`ㅁㅋ` encuentra `미쿠`). Los favoritos y los usados recientemente
se quedan arriba.

**Sin ratón** — las flechas recorren la cuadrícula, <kbd>Enter</kbd> pega y <kbd>Esc</kbd>
cierra. Después del atajo no hace falta soltar el teclado.

<details>
<summary>Más comportamiento del selector</summary>

- Haz clic derecho en un elemento para renombrarlo, editar sus palabras clave, moverlo a
  otra colección, pegarlo como enlace (si se añadió por URL) o eliminarlo.
- Añadir una imagen que ya tienes en esa pestaña y colección se rechaza en lugar de
  duplicarse en silencio.
- Los stickers APNG animados se convierten a GIF al registrarlos, porque Discord no anima
  los APNG subidos.
- El botón del portapapeles guarda la imagen actual directamente en una colección de
  **Capturas**. Los ajustes pueden hacerlo automáticamente con cada imagen nueva del
  portapapeles — desactivado de forma predeterminada.
- La ventana se puede redimensionar y recuerda su tamaño, teniendo en cuenta el DPI del
  monitor.
- Elementos que superan el límite: las imágenes fijas se comprimen automáticamente y los
  GIF demasiado grandes se envían tal cual con un aviso.
- Hay un envío automático opcional que pulsa <kbd>Enter</kbd> por ti después de pegar —
  desactivado de forma predeterminada.

</details>

## Compresión automática

Notro vigila el portapapeles. Cuando aparece una imagen nueva calcula **el tamaño del PNG
que Discord produciría realmente**, y si cabe dentro del límite no hace nada. Si lo supera,
recodifica a WebP y después a JPEG, bajando la calidad y por último la resolución hasta
quedar por debajo de unos 9,5 MB, y devuelve el resultado **como archivo** para que
<kbd>Ctrl</kbd>+<kbd>V</kbd> lo suba como adjunto.

> Tus archivos originales en disco nunca se tocan — solo se reemplaza el portapapeles.

El límite se cambia desde la bandeja entre **10 / 50 / 500 MB** (gratis, Nitro Basic, Nitro).

## Clips de vídeo

Copia un clip de juego demasiado grande y Notro pregunta primero, mostrando exactamente qué
esperar:

```
52MB · 1:12 · 1080p60  →  unos 9,5MB · 480p30
```

En esa misma ventana puedes **recortarlo** (`inicio – fin`) y **quitarle el audio**, y la
estimación se actualiza mientras escribes. Esto pesa más que cualquier ajuste del
codificador: una captura de 30 segundos a 1080p60 tiene que bajar a **1080p30** como clip
entero, pero recortada a los siete segundos que realmente querías se queda en **1080p60**.

**ffmpeg nunca se incluye en el paquete.** Se descarga bajo demanda (unos 30 MB, verificado
con SHA-256) la primera vez que comprimes un vídeo, o se toma de tu `PATH` si ya lo tienes.
Si un clip no cabe ni a 360p, Notro lo dice en lugar de producir un mosaico.

## Instalación

Descarga **[`NotroSetup.exe`](../../releases/latest)** y ejecútalo. No requiere permisos de
administrador; se instala en `%LOCALAPPDATA%\Programs\Notro`.

> ⚠️ La compilación **aún no está firmada digitalmente**, así que SmartScreen dirá que el
> editor es desconocido — pulsa *Más información → Ejecutar de todas formas*. Cada versión
> incluye un `NotroSetup.exe.sha256` para que verifiques exactamente lo que has descargado,
> y también puedes [compilarlo tú mismo](#ejecutar-desde-el-código-compilar-y-configurar).
> Consulta [SECURITY.md](SECURITY.md#code-signing) y la
> [política de firma de código](CODE_SIGNING.md).

**Usuarios de Windows 10:** el selector necesita el entorno de ejecución Microsoft Edge
WebView2 (Windows 11 lo trae incorporado). El instalador lo descarga si falta. Sin él, solo
se desactiva el selector; la compresión sigue funcionando.

### ¿Dónde ha ido?

Notro **no tiene ventana principal** — se ejecuta en la bandeja, junto al reloj.
**Windows 11 oculta los iconos nuevos de la bandeja de forma predeterminada**, así que si no
lo ves, pulsa la flecha **`^`** y arrastra el icono de Notro a la barra de tareas.

<p align="center">
  <img src="docs/welcome.png" width="360" alt="Ventana de bienvenida de Notro en el primer arranque">
</p>

Todo lo demás está en el clic derecho sobre el icono de la bandeja: atajo del selector,
pausar y reanudar, actividad reciente, límite de subida, idioma, carpeta de salida y
ejecución al iniciar Windows (**desactivada de forma predeterminada**).

## Privacidad

Notro vigila tu portapapeles, así que es justo explicar qué hace con él.

- **Nada de lo que copias se transmite jamás.** Sin telemetría, sin analíticas, sin informes
  de fallos, sin cuentas.
- **Nada de lo que copias se guarda a menos que lo pidas.** El guardado automático de
  capturas está desactivado de forma predeterminada.
- Contacta exactamente con **cuatro** destinos, todos documentados: GitHub (comprobación de
  actualizaciones y el instalador, verificado con SHA-256), `cdn.discordapp.com` (solo
  cuando añades un emoji por enlace) y PyPI (solo la primera vez que comprimes un vídeo,
  para obtener ffmpeg, también verificado con SHA-256).
- Al desinstalar **se conserva tu biblioteca** a propósito en `%APPDATA%\Notro`, para que
  reinstalar no te haga perder los emojis.

Cada ubicación de archivo y cada destino están detallados en [SECURITY.md](SECURITY.md).

## Idiomas

English, 한국어, 日本語, 中文(简体), Español — se detecta automáticamente desde Windows y se
puede cambiar en cualquier momento desde la bandeja.

<details>
<summary><a id="ejecutar-desde-el-código-compilar-y-configurar"></a>Ejecutar desde el código, compilar y configurar</summary>

```sh
pip install -r requirements.txt
pythonw notro.py           # ejecutar
build.bat                  # compilar dist\Notro.exe
```

Requiere Windows y Python 3.10 o superior.

El comportamiento de la compresión está en `notro_app/config.py` y `notro_app/compress.py`:

| Ajuste | Predeterminado | Descripción |
|---|---|---|
| `LIMIT_MB` | 10 | Límite de subida — o elige 10/50/500 desde el menú de la bandeja |
| `SAFETY` | 0.95 | Margen de seguridad (apunta a unos 9,5 MB) |
| `WEBP_QUALITIES` | 90–50 | Pasos de calidad de WebP |
| `MIN_SCALE` | 0.4 | Límite inferior de reducción de resolución |

Pruebas:

```sh
pip install -r requirements-dev.txt
pytest
```

</details>

## Licencia

[MIT](LICENSE). Los componentes de terceros incluidos y sus licencias — entre ellos pystray,
que es LGPL-3.0 — están listados en [THIRD-PARTY-NOTICES.md](THIRD-PARTY-NOTICES.md).

> Notro es una herramienta no oficial — **sin afiliación, respaldo ni patrocinio de Discord
> Inc.** «Discord» es una marca registrada de Discord Inc.
