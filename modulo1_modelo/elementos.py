"""
Módulo 1: Modelo Eléctrico y Generación de Ecuaciones.

Contiene las clases orientadas a objetos para representar los elementos
de un circuito de corriente directa (DC):
    - Nodos (incluyendo Tierra / GND)
    - Resistencias
    - Fuentes de Corriente Independientes
    - Fuentes de Voltaje Independientes
    - Fuentes de Voltaje Controladas por Corriente (CCVS / Dependientes)
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass(frozen=True)
class Nodo:
    """
    Representa un nodo de interconexión eléctrica en el circuito.

    Atributos:
        id_nodo (int): Identificador numérico único del nodo.
                       Por convención, id_nodo = 0 representa el nodo de referencia (Tierra / GND).
        nombre (str): Etiqueta descriptiva del nodo (ej. 'GND', 'V1', 'V2', 'V3').
        es_tierra (bool): Indica si este nodo actúa como referencia de 0V.
    """
    id_nodo: int
    nombre: str = ""
    es_tierra: bool = field(init=False)

    def __post_init__(self) -> None:
        if self.id_nodo < 0:
            raise ValueError("El identificador del nodo (id_nodo) no puede ser negativo.")
        es_ref = (self.id_nodo == 0)
        object.__setattr__(self, "es_tierra", es_ref)
        if not self.nombre:
            nombre_defecto = "GND" if es_ref else f"N{self.id_nodo}"
            object.__setattr__(self, "nombre", nombre_defecto)


class Componente(ABC):
    """
    Clase base abstracta para cualquier componente eléctrico de dos terminales (dipolo).

    Convención de terminales y signos:
        - nodo_a: Terminal positivo (+) o nodo de entrada/origen de la corriente nominal.
        - nodo_b: Terminal negativo (-) o nodo de salida/destino de la corriente nominal.
        - El voltaje del elemento se define como V_ab = V(nodo_a) - V(nodo_b).
    """

    def __init__(self, nombre: str, nodo_a: Nodo, nodo_b: Nodo, valor: float) -> None:
        if not nombre or not nombre.strip():
            raise ValueError("El componente debe tener un nombre identificador válido.")
        if nodo_a.id_nodo == nodo_b.id_nodo:
            raise ValueError(
                f"El componente '{nombre}' no puede estar conectado en cortocircuito "
                f"al mismo nodo ({nodo_a.nombre})."
            )
        self.nombre: str = nombre.strip()
        self.nodo_a: Nodo = nodo_a
        self.nodo_b: Nodo = nodo_b
        self.valor: float = float(valor)

    @property
    @abstractmethod
    def unidad(self) -> str:
        """Retorna el símbolo de la unidad física del componente."""
        pass

    @property
    @abstractmethod
    def tipo(self) -> str:
        """Retorna el nombre descriptivo del tipo de componente."""
        pass

    def __repr__(self) -> str:
        return (
            f"{self.__class__.__name__}(nombre='{self.nombre}', "
            f"nodo_a='{self.nodo_a.nombre}', nodo_b='{self.nodo_b.nombre}', "
            f"valor={self.valor} {self.unidad})"
        )


class Resistencia(Componente):
    """
    Representa un resistor lineal ideal en el circuito DC.

    La corriente fluye de nodo_a a nodo_b según la Ley de Ohm:
        I = (V_a - V_b) / R = G * (V_a - V_b)
    donde G = 1 / R es la conductancia en Siemens (S).
    """

    def __init__(self, nombre: str, nodo_a: Nodo, nodo_b: Nodo, resistencia_ohms: float) -> None:
        if resistencia_ohms <= 0:
            raise ValueError(
                f"La resistencia '{nombre}' debe tener un valor estrictamente positivo (> 0 Ω)."
            )
        super().__init__(nombre, nodo_a, nodo_b, resistencia_ohms)

    @property
    def conductancia(self) -> float:
        """Retorna la conductancia G = 1/R en Siemens [S]."""
        return 1.0 / self.valor

    @property
    def unidad(self) -> str:
        return "Ω"

    @property
    def tipo(self) -> str:
        return "Resistencia"


class FuenteCorriente(Componente):
    """
    Representa una fuente de corriente continua independiente ideal.

    Convención de dirección:
        La corriente nominal fluye internamente desde `nodo_a` hacia `nodo_b`
        (sale del nodo_a e ingresa al nodo_b).
    """

    def __init__(self, nombre: str, nodo_a: Nodo, nodo_b: Nodo, corriente_amperios: float) -> None:
        super().__init__(nombre, nodo_a, nodo_b, corriente_amperios)

    @property
    def unidad(self) -> str:
        return "A"

    @property
    def tipo(self) -> str:
        return "Fuente de Corriente"


class FuenteVoltaje(Componente):
    """
    Representa una fuente de voltaje continuo independiente ideal.

    Convención de polaridad:
        - `nodo_a` corresponde a la terminal positiva (+).
        - `nodo_b` corresponde a la terminal negativa (-).
        - Ecuación de restricción de potencial: V(nodo_a) - V(nodo_b) = valor.
        - La corriente incógnita asociada I_fuente se define entrando por el
          terminal positivo (`nodo_a`) y saliendo por el negativo (`nodo_b`)
          (convención pasiva para el estampado MNA).
    """

    def __init__(self, nombre: str, nodo_a: Nodo, nodo_b: Nodo, voltaje_voltios: float) -> None:
        super().__init__(nombre, nodo_a, nodo_b, voltaje_voltios)

    @property
    def unidad(self) -> str:
        return "V"

    @property
    def tipo(self) -> str:
        return "Fuente de Voltaje"


class FuenteVoltajeControladaCorriente(Componente):
    """
    Representa una Fuente de Voltaje Controlada por Corriente (CCVS - Current-Controlled
    Voltage Source) para el Análisis Nodal Modificado (MNA).

    Ecuación constitutiva:
        V(nodo_a) - V(nodo_b) = r * i_phi
    Donde:
        - `nodo_a`: Terminal positivo (+) de la fuente dependiente.
        - `nodo_b`: Terminal negativo (-) de la fuente dependiente.
        - `r` (`valor` / `transresistencia`): Ganancia de transresistencia en Ohmios [V/A o Ω].
        - `componente_control`: El elemento del circuito por el cual circula la corriente
                                de control `i_phi` (definida fluyendo desde
                                `componente_control.nodo_a` hacia `componente_control.nodo_b`).
    """

    def __init__(
        self,
        nombre: str,
        nodo_a: Nodo,
        nodo_b: Nodo,
        transresistencia: float,
        componente_control: Componente,
    ) -> None:
        if componente_control is None:
            raise ValueError(
                f"La fuente CCVS '{nombre}' requiere un componente de control válido para i_phi."
            )
        super().__init__(nombre, nodo_a, nodo_b, transresistencia)
        self.componente_control: Componente = componente_control

    @property
    def transresistencia(self) -> float:
        """Ganancia r [V/A o Ω] tal que V_ab = r * i_phi."""
        return self.valor

    @property
    def unidad(self) -> str:
        return f"·i({self.componente_control.nombre}) [V]"

    @property
    def tipo(self) -> str:
        return "Fuente CCVS (Dependiente)"


class Circuito:
    """
    Contenedor topológico del circuito eléctrico DC.

    Gestiona el registro de nodos y componentes, garantizando la integridad
    de los identificadores y la existencia del nodo de referencia (GND = 0).
    """

    def __init__(self, nombre: str = "Circuito DC") -> None:
        self.nombre: str = nombre
        self._nodos: Dict[int, Nodo] = {0: Nodo(0, "GND")}
        self._componentes: List[Componente] = []
        self._mapa_componentes: Dict[str, Componente] = {}

    def obtener_o_crear_nodo(self, id_nodo: int, nombre: str = "") -> Nodo:
        """
        Obtiene un nodo existente por su ID o lo crea y registra si no existe.

        Si el nodo ya existe con su etiqueta genérica (ej. 'N1') y se provee
        un `nombre` descriptivo, se actualiza la etiqueta y se propaga el
        nuevo objeto a los componentes ya registrados, para que todos
        compartan la misma referencia de nodo.
        """
        if id_nodo not in self._nodos:
            self._nodos[id_nodo] = Nodo(id_nodo, nombre)
        elif nombre and self._nodos[id_nodo].nombre == f"N{id_nodo}":
            # Permite actualizar la etiqueta descriptiva si antes tenía el nombre genérico
            nuevo = Nodo(id_nodo, nombre)
            self._nodos[id_nodo] = nuevo
            for comp in self._componentes:
                if comp.nodo_a.id_nodo == id_nodo:
                    comp.nodo_a = nuevo
                if comp.nodo_b.id_nodo == id_nodo:
                    comp.nodo_b = nuevo
        return self._nodos[id_nodo]

    def esta_registrado(self, componente: Componente) -> bool:
        """Indica si `componente` es el mismo objeto registrado bajo su nombre."""
        return self._mapa_componentes.get(componente.nombre) is componente

    def obtener_componente(self, nombre: str) -> Componente:
        """Busca y retorna un componente registrado por su nombre."""
        if nombre not in self._mapa_componentes:
            raise KeyError(f"No existe ningún componente llamado '{nombre}' en el circuito.")
        return self._mapa_componentes[nombre]

    def agregar_componente(self, componente: Componente) -> None:
        """
        Registra un componente en el circuito y asegura que sus nodos estén registrados.
        """
        if componente.nombre in self._mapa_componentes:
            raise ValueError(
                f"Ya existe un componente con el nombre '{componente.nombre}' en el circuito."
            )
        for nodo in (componente.nodo_a, componente.nodo_b):
            if nodo.id_nodo not in self._nodos:
                self._nodos[nodo.id_nodo] = nodo

        self._componentes.append(componente)
        self._mapa_componentes[componente.nombre] = componente

    def agregar_resistencia(
        self, nombre: str, id_nodo_a: int, id_nodo_b: int, valor_ohms: float
    ) -> Resistencia:
        """Método auxiliar para crear y agregar una resistencia directamente por IDs de nodo."""
        na = self.obtener_o_crear_nodo(id_nodo_a)
        nb = self.obtener_o_crear_nodo(id_nodo_b)
        res = Resistencia(nombre, na, nb, valor_ohms)
        self.agregar_componente(res)
        return res

    def agregar_fuente_corriente(
        self, nombre: str, id_nodo_origen: int, id_nodo_destino: int, valor_amperios: float
    ) -> FuenteCorriente:
        """
        Método auxiliar para crear y agregar una fuente de corriente independiente.
        La corriente fluye desde `id_nodo_origen` hacia `id_nodo_destino`.
        """
        na = self.obtener_o_crear_nodo(id_nodo_origen)
        nb = self.obtener_o_crear_nodo(id_nodo_destino)
        fc = FuenteCorriente(nombre, na, nb, valor_amperios)
        self.agregar_componente(fc)
        return fc

    def agregar_fuente_voltaje(
        self, nombre: str, id_nodo_pos: int, id_nodo_neg: int, valor_voltios: float
    ) -> FuenteVoltaje:
        """
        Método auxiliar para crear y agregar una fuente de voltaje independiente.
        `id_nodo_pos` es la terminal (+) y `id_nodo_neg` es la terminal (-).
        """
        na = self.obtener_o_crear_nodo(id_nodo_pos)
        nb = self.obtener_o_crear_nodo(id_nodo_neg)
        fv = FuenteVoltaje(nombre, na, nb, valor_voltios)
        self.agregar_componente(fv)
        return fv

    def agregar_fuente_ccvs(
        self,
        nombre: str,
        id_nodo_pos: int,
        id_nodo_neg: int,
        transresistencia: float,
        componente_o_nombre_control: Componente | str,
    ) -> FuenteVoltajeControladaCorriente:
        """
        Método auxiliar para crear y agregar una Fuente de Voltaje Controlada por
        Corriente (CCVS) de valor V = transresistencia * i_phi.
        """
        if isinstance(componente_o_nombre_control, str):
            comp_ctrl = self.obtener_componente(componente_o_nombre_control)
        else:
            comp_ctrl = componente_o_nombre_control
            if not self.esta_registrado(comp_ctrl):
                raise ValueError(
                    f"La fuente CCVS '{nombre}' usa como control a "
                    f"'{comp_ctrl.nombre}', pero ese objeto no está registrado en "
                    "este circuito. Agregue primero el componente de control al "
                    "circuito o páselo por su nombre."
                )

        na = self.obtener_o_crear_nodo(id_nodo_pos)
        nb = self.obtener_o_crear_nodo(id_nodo_neg)
        ccvs = FuenteVoltajeControladaCorriente(
            nombre=nombre,
            nodo_a=na,
            nodo_b=nb,
            transresistencia=transresistencia,
            componente_control=comp_ctrl,
        )
        self.agregar_componente(ccvs)
        return ccvs

    @property
    def nodos(self) -> List[Nodo]:
        """Retorna la lista de todos los nodos ordenados por su id_nodo."""
        return [self._nodos[k] for k in sorted(self._nodos.keys())]

    @property
    def nodos_incognita(self) -> List[Nodo]:
        """Retorna la lista de nodos activos (excluyendo el nodo de referencia id_nodo=0)."""
        return [n for n in self.nodos if not n.es_tierra]

    @property
    def componentes(self) -> List[Componente]:
        """Retorna la lista de todos los componentes del circuito."""
        return list(self._componentes)

    @property
    def resistencias(self) -> List[Resistencia]:
        """Retorna únicamente las resistencias del circuito."""
        return [c for c in self._componentes if isinstance(c, Resistencia)]

    @property
    def fuentes_corriente(self) -> List[FuenteCorriente]:
        """Retorna únicamente las fuentes de corriente independientes del circuito."""
        return [c for c in self._componentes if isinstance(c, FuenteCorriente)]

    @property
    def fuentes_voltaje(self) -> List[FuenteVoltaje]:
        """Retorna únicamente las fuentes de voltaje independientes del circuito."""
        return [c for c in self._componentes if isinstance(c, FuenteVoltaje)]

    @property
    def fuentes_ccvs(self) -> List[FuenteVoltajeControladaCorriente]:
        """Retorna únicamente las fuentes de voltaje controladas por corriente (CCVS)."""
        return [
            c for c in self._componentes if isinstance(c, FuenteVoltajeControladaCorriente)
        ]

    @property
    def todas_fuentes_voltaje_mna(
        self,
    ) -> List[FuenteVoltaje | FuenteVoltajeControladaCorriente]:
        """
        Retorna todas las fuentes que imponen una restricción de voltaje en el MNA
        (tanto fuentes de voltaje independientes como fuentes dependientes CCVS),
        en el orden en que fueron agregadas al circuito.
        """
        return [
            c
            for c in self._componentes
            if isinstance(c, (FuenteVoltaje, FuenteVoltajeControladaCorriente))
        ]

    def resumen_topologia(self) -> str:
        """
        Retorna un resumen legible de la topología (nodos y componentes),
        útil para ejemplos, capturas de consola y verificación manual.
        No resuelve el circuito: solo describe el modelo eléctrico.
        """
        lineas = [f"Circuito '{self.nombre}': {len(self.nodos_incognita)} nodo(s) + GND, "
                  f"{len(self._componentes)} componente(s)"]
        lineas.append("Nodos: " + ", ".join(
            f"{n.nombre}(id={n.id_nodo})" for n in self.nodos))
        for comp in self._componentes:
            extra = ""
            if isinstance(comp, FuenteVoltajeControladaCorriente):
                extra = f" [control: i({comp.componente_control.nombre})]"
            lineas.append(
                f"  - {comp.nombre}: {comp.tipo} "
                f"{comp.nodo_a.nombre} -> {comp.nodo_b.nombre} "
                f"({comp.valor} {comp.unidad}){extra}")
        return "\n".join(lineas)
