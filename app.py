from flask import Flask, render_template, request, redirect, url_for, session, flash
import pandas as pd
import os
import logging
from datetime import date
import calendar

app = Flask(__name__)
# Mejor usar variable de entorno para la clave secreta en producción
app.secret_key = os.environ.get('ECUACORP_SECRET', 'ecuacorp_2026_premium')

# Configuraciones y constantes
SBU_DECIMO_CUARTO = float(os.environ.get('SBU_DECIMO_CUARTO', 460))  # salario básico unificado anual/porcentaje
DATA_FILE = os.environ.get('ECUACORP_DATAFILE', 'Base de Datos.xlsx')

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

_DF_CACHE = None

def obtener_datos():
    """Carga el archivo de datos y normaliza columnas. Usa cache en memoria para evitar relecturas frecuentes."""
    global _DF_CACHE
    if _DF_CACHE is not None:
        return _DF_CACHE

    if not os.path.exists(DATA_FILE):
        logger.error('Archivo de datos no encontrado: %s', DATA_FILE)
        raise FileNotFoundError(f"No se encontró el archivo de datos: {DATA_FILE}")

    df = pd.read_excel(DATA_FILE, skiprows=2)
    # Normalizar nombres de columnas si vienen distintos
    df.columns = ['N', 'Nombre', 'Cedula', 'Cargo', 'Ingreso', 'Sueldo']
    df = df.dropna(subset=['Nombre'])
    # Convertir tipos para serializar en session
    df['Cedula'] = df['Cedula'].astype(str).str.strip()
    df['Sueldo'] = pd.to_numeric(df['Sueldo'], errors='coerce').fillna(0).astype(float)

    _DF_CACHE = df
    return df


@app.route('/')
def home():
    return render_template('login.html')


@app.route('/login', methods=['POST'])
def login():
    cedula = request.form.get('cedula', '').strip()
    if not cedula:
        flash('Ingrese una cédula válida.', 'warning')
        return redirect(url_for('home'))

    try:
        df = obtener_datos()
    except FileNotFoundError as e:
        return render_template('error.html', message=str(e)), 500
    except Exception as e:
        logger.exception('Error al leer datos')
        return render_template('error.html', message='Error interno al cargar datos.'), 500

    empleado = df[df['Cedula'] == cedula]
    if not empleado.empty:
        row = empleado.iloc[0]
        # Guardar solo campos simples en session
        session['usuario'] = {
            'Nombre': row['Nombre'],
            'Cedula': row['Cedula'],
            'Cargo': row.get('Cargo', ''),
            'Ingreso': str(row.get('Ingreso', '')),
            'Sueldo': float(row.get('Sueldo', 0))
        }
        return redirect(url_for('dashboard'))

    flash('Cédula no registrada. Contacte a RR.HH.', 'danger')
    return redirect(url_for('home'))


@app.route('/dashboard')
def dashboard():
    if 'usuario' not in session:
        return redirect(url_for('home'))

    u = session['usuario']
    sueldo = float(u.get('Sueldo', 0))

    # --- CÁLCULOS DE LEY ECUADOR (Mensualizados) ---
    iess = round(sueldo * 0.0945, 2)
    fondo_reserva = round(sueldo * 0.0833, 2)
    decimo_3ro = round(sueldo / 12, 2)
    decimo_4to = round(SBU_DECIMO_CUARTO / 12, 2)

    ingresos_totales = round(sueldo + fondo_reserva + decimo_3ro + decimo_4to, 2)
    neto_recibir = round(ingresos_totales - iess, 2)

    # --- FECHA ESTIMADA DE PAGO SEGÚN SUELDO ---
    # reglas ficticias: sueldos bajos pagan antes, sueldos altos al final de mes
    today = date.today()
    last_day = calendar.monthrange(today.year, today.month)[1]
    if sueldo < 500:
        pago_dia = 25
    elif sueldo < 1000:
        pago_dia = 27
    else:
        pago_dia = last_day
    pago_fecha = date(today.year, today.month, pago_dia)
    # formato manual en español simple
    meses = ['enero','febrero','marzo','abril','mayo','junio','julio','agosto','septiembre','octubre','noviembre','diciembre']
    pago_str = f"{pago_fecha.day} de {meses[pago_fecha.month-1]} de {pago_fecha.year}"

    return render_template('perfil.html',
                           u=u,
                           iess=iess,
                           fr=fondo_reserva,
                           d3=decimo_3ro,
                           d4=decimo_4to,
                           total_ing=ingresos_totales,
                           neto=neto_recibir,
                           pay_date=pago_str)


@app.route('/logout')
def logout():
    session.clear()
    flash('Sesión cerrada correctamente.', 'info')
    return redirect(url_for('home'))


@app.route('/download_pdf')
def download_pdf():
    # Placeholder: aquí se puede integrar generación de PDF (reportlab, weasyprint, xhtml2pdf, etc.)
    if 'usuario' not in session:
        return redirect(url_for('home'))
    flash('Funcionalidad de descarga de PDF próximamente.', 'info')
    return redirect(url_for('dashboard'))


if __name__ == '__main__':
    app.run(debug=True)