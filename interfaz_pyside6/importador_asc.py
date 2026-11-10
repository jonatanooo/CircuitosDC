"""Importación acotada de esquemas LTspice ASC para el modelo DC del proyecto.

Referencias de pines y rotaciones: documentación de esquemas de Analog Devices,
https://github.com/analogdevicesinc/ltspice-reference/blob/main/ai_ref/SCHEMATIC-REFERENCE.md
"""
import math
import re
from pathlib import Path


class ErrorImportacionASC(ValueError):
    pass


def _valor(texto):
    texto = texto.strip()
    if texto.lower().startswith('dc '):
        texto = texto[3:].strip()
    patron = r'([+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?)(meg|[tgkmunpfµ])?'
    m = re.fullmatch(patron, texto, re.IGNORECASE)
    if not m:
        raise ErrorImportacionASC(f"Valor no compatible: '{texto}'. Solo se admiten valores DC numéricos.")
    factor = {'': 1, 't': 1e12, 'g': 1e9, 'meg': 1e6, 'k': 1e3, 'm': 1e-3,
              'u': 1e-6, 'µ': 1e-6, 'n': 1e-9, 'p': 1e-12, 'f': 1e-15}[ (m.group(2) or '').lower() ]
    valor = float(m.group(1)) * factor
    if not math.isfinite(valor):
        raise ErrorImportacionASC('Valor no finito.')
    return valor


def _pin(x, y, px, py, orientacion):
    if orientacion == 'R0': return (x + px, y + py)
    if orientacion == 'R90': return (x - py, y + px)
    if orientacion == 'R180': return (x - px, y - py)
    if orientacion == 'R270': return (x + py, y - px)
    raise ErrorImportacionASC(f'Orientación no compatible: {orientacion}.')


def importar_asc(ruta):
    datos = Path(ruta).read_bytes()
    if datos.startswith((b'\xff\xfe', b'\xfe\xff')):
        contenido = datos.decode('utf-16')
    else:
        try: contenido = datos.decode('utf-8-sig')
        except UnicodeDecodeError: contenido = datos.decode('cp1252')
    lineas = contenido.splitlines()
    cables, flags, simbolos = [], [], []
    actual = None
    for numero, linea in enumerate(lineas, 1):
        partes = linea.strip().split()
        if not partes: continue
        tipo = partes[0].upper()
        try:
            if tipo == 'WIRE':
                if len(partes) != 5: raise ValueError('WIRE incompleto')
                a, b = tuple(map(int, partes[1:3])), tuple(map(int, partes[3:5]))
                if a[0] != b[0] and a[1] != b[1]: raise ValueError('cable diagonal no compatible')
                cables.append((a, b))
            elif tipo == 'FLAG':
                if len(partes) != 4: raise ValueError('FLAG incompleto')
                flags.append((tuple(map(int, partes[1:3])), partes[3]))
            elif tipo == 'SYMBOL':
                if len(partes) != 5: raise ValueError('SYMBOL incompleto')
                nombre = partes[1].lower()
                if nombre not in ('res', 'res2', 'voltage', 'current', 'h'):
                    raise ValueError(f"símbolo '{partes[1]}' no compatible")
                actual = {'tipo': nombre, 'x': int(partes[2]), 'y': int(partes[3]), 'orientacion': partes[4].upper(), 'atributos': {}}
                simbolos.append(actual)
            elif tipo == 'SYMATTR':
                if actual is None or len(partes) < 3: raise ValueError('SYMATTR sin símbolo o valor')
                actual['atributos'][partes[1].lower()] = ' '.join(partes[2:])
            elif tipo == 'TEXT':
                if '!' in linea and linea.split('!', 1)[1].strip().lower() != '.op':
                    raise ValueError('directiva SPICE no compatible; solo se admite .op')
            elif tipo not in ('VERSION', 'SHEET', 'WINDOW'):
                raise ValueError(f"registro '{partes[0]}' no compatible")
        except (ValueError, IndexError) as exc:
            raise ErrorImportacionASC(f'Línea {numero}: {exc}') from exc
    if not simbolos: raise ErrorImportacionASC('El archivo no contiene componentes compatibles.')
    offsets = {'res': ((16,16),(16,96)), 'res2': ((16,0),(16,64)), 'voltage': ((0,16),(0,96)),
               'current': ((0,0),(0,80)), 'h': ((0,16),(0,96))}
    tipos = {'res': 'RESISTENCIA', 'res2': 'RESISTENCIA', 'voltage': 'FUENTE_VOLTAJE',
             'current': 'FUENTE_CORRIENTE', 'h': 'FUENTE_CCVS'}
    unidades = {'RESISTENCIA': 'Ω', 'FUENTE_VOLTAJE': 'V', 'FUENTE_CORRIENTE': 'A', 'FUENTE_CCVS': 'Ω'}
    nombres = set()
    for s in simbolos:
        attrs = s['atributos']; s['id'] = attrs.get('instname', '')
        if not s['id'] or s['id'].lower() in nombres: raise ErrorImportacionASC('Falta una etiqueta de componente o está repetida.')
        nombres.add(s['id'].lower())
        extra = set(attrs) - {'instname', 'value', 'value2', 'description'}
        if extra: raise ErrorImportacionASC(f"{s['id']}: atributos SPICE no compatibles: {', '.join(sorted(extra))}.")
        s['control'] = ''
        if s['tipo'] == 'h':
            s['control'] = attrs.get('value','').strip()
            valor = attrs.get('value2','')
            if not s['control'] or not valor: raise ErrorImportacionASC(f"{s['id']}: CCVS requiere fuente de control en Value y ganancia en Value2.")
        else:
            if attrs.get('value2'): raise ErrorImportacionASC(f"{s['id']}: parámetros adicionales no compatibles.")
            valor = attrs.get('value','')
        s['valor'] = _valor(valor)
        if s['tipo'] in ('res','res2') and s['valor'] <= 0: raise ErrorImportacionASC(f"{s['id']}: la resistencia debe ser positiva.")
        s['pines'] = [_pin(s['x'],s['y'],*p,s['orientacion']) for p in offsets[s['tipo']]]
        a,b = s['pines']; horizontal = a[1] == b[1]
        if (horizontal and a[0] > b[0]) or (not horizontal and a[1] > b[1]):
            if s['tipo'] not in ('res','res2'):
                raise ErrorImportacionASC(f"{s['id']}: orientación con polaridad invertida no compatible; gírela en LTspice.")
            s['pines'].reverse()
        s['orientacion_grafica'] = 'H' if horizontal else 'V'
    fuentes = {s['id'].lower(): s for s in simbolos if s['tipo'] == 'voltage'}
    for s in simbolos:
        if s['tipo'] == 'h':
            control = fuentes.get(s['control'].lower())
            if not control: raise ErrorImportacionASC(f"{s['id']}: la fuente de control '{s['control']}' no existe o no es una fuente de voltaje.")
            s['control'] = control['id']
    puntos = {p for cable in cables for p in cable} | {p for p,_ in flags} | {p for s in simbolos for p in s['pines']}
    padre = {p:p for p in puntos}
    def buscar(p):
        while padre[p] != p:
            padre[p] = padre[padre[p]]; p = padre[p]
        return p
    def unir(a,b):
        a,b=buscar(a),buscar(b)
        if a != b: padre[b]=a
    for a,b in cables:
        for p in puntos:
            if ((a[0] == b[0] == p[0] and min(a[1],b[1]) <= p[1] <= max(a[1],b[1])) or
                (a[1] == b[1] == p[1] and min(a[0],b[0]) <= p[0] <= max(a[0],b[0]))): unir(a,p)
    nombres_red = {}
    for punto,nombre in flags:
        nombre = nombre.lower()
        if nombre in nombres_red: unir(punto,nombres_red[nombre])
        else: nombres_red[nombre] = punto
    if '0' not in nombres_red: raise ErrorImportacionASC('Falta FLAG de tierra (0).')
    raiz_tierra = buscar(nombres_red['0'])
    raices = {buscar(p) for s in simbolos for p in s['pines']}
    if raiz_tierra not in raices: raise ErrorImportacionASC('La referencia de tierra no está conectada a ningún componente.')
    orden = {raiz_tierra:0}
    for raiz in sorted(raices - {raiz_tierra}): orden[raiz]=len(orden)
    etiquetas = {raiz: ('GND' if id_nodo == 0 else f'N{id_nodo}') for raiz,id_nodo in orden.items()}
    for punto,nombre in flags:
        raiz = buscar(punto)
        if raiz in etiquetas and raiz != raiz_tierra: etiquetas[raiz] = nombre
    minx = min(p[0] for s in simbolos for p in s['pines']); miny = min(p[1] for s in simbolos for p in s['pines'])
    componentes, redes = [], {r:[] for r in orden}
    for s in simbolos:
        a,b = s['pines']; ra,rb = buscar(a),buscar(b)
        if ra == rb: raise ErrorImportacionASC(f"{s['id']}: ambos terminales están cortocircuitados; esta topología no se puede representar en el lienzo.")
        comp = {'id': s['id'], 'tipo': tipos[s['tipo']], 'valor': str(s['valor']), 'unidad': unidades[tipos[s['tipo']]],
                'factor': 1.0, 'x': (a[0]+b[0])/2-minx+110, 'y': (a[1]+b[1])/2-miny+100,
                'orientacion': s['orientacion_grafica'], 'control': s['control'],
                'nodo_a': orden[ra], 'nodo_b': orden[rb], 'etiqueta_a': etiquetas[ra], 'etiqueta_b': etiquetas[rb]}
        componentes.append(comp); redes[ra].append((s['id'],'A')); redes[rb].append((s['id'],'B'))
    nombre_gnd = 'GND'
    while nombre_gnd.lower() in nombres: nombre_gnd += '_ref'
    g = nombres_red['0']
    componentes.append({'id':nombre_gnd,'tipo':'TIERRA','valor':'0','unidad':'V','factor':1.0,
                        'x':g[0]-minx+110,'y':g[1]-miny+120,'orientacion':'V','control':'',
                        'nodo_a':0,'nodo_b':0,'etiqueta_a':'GND','etiqueta_b':'GND'})
    redes[raiz_tierra].append((nombre_gnd,'A'))
    enlaces = []
    ubicaciones = {c['id']: c for c in componentes}
    def posicion(terminal):
        c = ubicaciones[terminal[0]]
        if c['tipo'] == 'TIERRA': return (c['x'], c['y'] - 20)
        desplazamiento = -46 if terminal[1] == 'A' else 46
        return ((c['x'] + desplazamiento, c['y']) if c['orientacion'] == 'H'
                else (c['x'], c['y'] + desplazamiento))
    for terminales in redes.values():
        if len(terminales) < 2:
            continue
        conectados, pendientes = [terminales[0]], terminales[1:]
        while pendientes:
            opciones = []
            for a in conectados:
                for b in pendientes:
                    if a[0] == b[0]:
                        continue
                    pa, pb = posicion(a), posicion(b)
                    opciones.append(((pa[0] - pb[0]) ** 2 + (pa[1] - pb[1]) ** 2, a, b))
            if not opciones:
                raise ErrorImportacionASC('Una conexión no se puede representar con los terminales disponibles.')
            _, base, destino = min(opciones)
            enlaces.append({'origen':base[0],'pin_origen':base[1], 'destino':destino[0], 'pin_destino':destino[1]})
            pendientes.remove(destino)
            conectados.append(destino)
    return {'version':1,'componentes':componentes,'cables':enlaces}
