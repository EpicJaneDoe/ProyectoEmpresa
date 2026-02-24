from flask import Flask, render_template, request, redirect, url_for, session
import pandas as pd

app = Flask(__name__)
app.secret_key = 'ecuacorp_2026_premium'

def obtener_datos():
    # Asegúrate de que el archivo se llame así o cámbialo al nombre exacto que tengas
    df = pd.read_excel('Base de Datos.xlsx', skiprows=2)
    df.columns = ['N', 'Nombre', 'Cedula', 'Cargo', 'Ingreso', 'Sueldo']
    return df.dropna(subset=['Nombre'])

@app.route('/')
def home():
    return render_template('login.html')

@app.route('/login', methods=['POST'])
def login():
    cedula = request.form['cedula']
    df = obtener_datos()
    empleado = df[df['Cedula'].astype(str) == str(cedula)]
    
    if not empleado.empty:
        session['usuario'] = empleado.iloc[0].to_dict()
        return redirect(url_for('dashboard'))
    return "Cédula no registrada. Contacte a RR.HH."

@app.route('/dashboard')
def dashboard():
    if 'usuario' not in session: return redirect(url_for('home'))
    
    u = session['usuario']
    sueldo = float(u['Sueldo'])
    
    # --- CÁLCULOS DE LEY ECUADOR (Mensualizados) ---
    iess = sueldo * 0.0945
    fondo_reserva = sueldo * 0.0833
    decimo_3ro = sueldo / 12
    decimo_4to = 460 / 12  # SBU 2024/25 es $460. Ajustar según año.
    
    ingresos_totales = sueldo + fondo_reserva + decimo_3ro + decimo_4to
    neto_recibir = ingresos_totales - iess
    
    return render_template('perfil.html', 
                           u=u, 
                           iess=iess, 
                           fr=fondo_reserva, 
                           d3=decimo_3ro, 
                           d4=decimo_4to,
                           total_ing=ingresos_totales,
                           neto=neto_recibir)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('home'))

if __name__ == '__main__':
    app.run(debug=True)