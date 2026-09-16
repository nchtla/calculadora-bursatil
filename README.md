# Calculadora bursátil web

Aplicación creada con Streamlit para buscar una empresa por nombre o ticker, recuperar cotización y fundamentales desde Financial Modeling Prep, calcular una operación y mostrar gráficos.

## Uso local

1. Instala Python 3.11 o superior.
2. Abre una terminal en esta carpeta.
3. Ejecuta:

```bash
pip install -r requirements.txt
```

4. Crea la carpeta `.streamlit` y un archivo `.streamlit/secrets.toml` con:

```toml
FMP_API_KEY = "TU_CLAVE_AQUI"
```

5. Ejecuta:

```bash
streamlit run app.py
```

## Publicación con Streamlit Community Cloud

1. Sube estos archivos a un repositorio privado o público de GitHub.
2. En Streamlit Community Cloud, crea una aplicación desde ese repositorio.
3. En Settings > Secrets, añade:

```toml
FMP_API_KEY = "TU_CLAVE_AQUI"
```

4. Publica la aplicación.

## Seguridad

No guardes la clave API dentro de `app.py`, en Excel ni en un repositorio público.

## Limitaciones

La cobertura de mercados, el retraso de cotizaciones, los límites de peticiones y los fundamentales disponibles dependen del plan y del proveedor de datos. La aplicación no constituye asesoramiento financiero.
