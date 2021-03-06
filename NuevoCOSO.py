import copy as copiar
import io
import json
import os
import warnings as avisar
from datetime import datetime as ft

import numpy as np
import pymc

import MATEMÁTICAS.NuevoIncert as Incert
from MATEMÁTICAS.Experimentos import Experimento
from MATEMÁTICAS.NuevaCalib import ModBayes


class Coso(object):
    """
    Un "coso", por falta de mejor palabra, se refiere a todo, TODO en el programa
    Tikon que representa un aspecto físico del ambiente y que tiene datos. Incluye
    paisajes, parcelas, variedades de cultivos, suelos, insectos, etc. Todos tienen la misma
    lógica para leer y escribir sus datos en carpetas externas, tanto como para la
    su calibración.
    """

    # La extensión para guardar recetas de este tipo de objeto
    ext = NotImplemented

    # Una referancia al diccionario con la información de los parámetros del objeto.
    dic_ecs = NotImplemented

    def __init__(símismo, nombre, fuente=None):
        """
        Creamos un Coso con un numbre y, posiblemente, una fuente de cual cargarlo.

        :param nombre: El nombre del Coso
        :type nombre: str

        :param fuente: El archivo de cual cargar el Coso
        :type fuente: str
        """

        # En 'coefs', ponemos todos los coeficientes del modelo (se pueden organizar en diccionarios). En 'estr',
        # pondremos la información estructural del modelo.

        símismo.receta = dict(coefs={},
                              estr={}
                              )

        # Acordarse de dónde vamos a guardar este Coso
        símismo.fuente = fuente

        # También el nombre, para referencia fácil
        símismo.nombre = nombre

        # Si se especificó un archivo para cargar, cargarlo.
        if fuente is not None:
            símismo.cargar(fuente)

    def especificar_apriori(símismo, etapa, ubic_parám, rango, certidumbre):
        """
        Esta función permite al usuario de especificar una distribución especial para el a priori de un parámetro.

        :param ubic_parám: Una lista de las llaves que traerán uno a través del diccionario de coeficientes del Coso
          hasta el parámetro de interés.
        :type ubic_parám: list

        :param rango: El rango a cuál queremos limitar el parámetro
        :type rango: tuple

        :param certidumbre: El % de certidumbre de que el parámetro se encuentre adentro del rango especificado.
        :type certidumbre: float

        """

        # Si "certidumbre" se especificó como un porcentaje, cambiarlo a una fracción.
        if certidumbre > 1:
            avisar.warn('El parámetro "certidumbre" se especificó a un valor superior a 1. Lo tomaremos como un '
                        'porcentaje.')
            certidumbre /= 100

        # Asegurarse de que "certidumbre" esté entre 0 y 1
        if not 0 < certidumbre <= 1:
            raise ValueError('El parámetro "certidumbre" debe ser un número en el rango (0, 1].')

        dic_parám = símismo.receta['coefs'][etapa]
        dic_ecs = símismo.dic_ecs

        for llave in ubic_parám:
            try:
                dic_parám = dic_parám[llave]
                dic_ecs = dic_ecs[llave]
            except KeyError:
                raise KeyError('Ubicación de parámetro erróneo.')

        try:
            líms = dic_ecs['límites']
        except KeyError:
            raise KeyError('Ubicación de parámetro erróneo.')

        dic_parám['especificado'] = Incert.rango_a_texto_dist(líms=líms, rango=rango, certidumbre=certidumbre,
                                                              cont=True)  # para hacer: parámetros discretos

    def guardar(símismo, archivo=''):
        """
        Esta función guarda el Coso para uso futuro.

        :param archivo: Donde hay que guardar el Coso
        :type archivo: str
        """

        # Si no se especificó archivo...
        if archivo == '':
            if símismo.fuente != '':
                archivo = símismo.fuente  # utilizar el archivo existente
            else:
                # Si no hay archivo existente, tenemos un problema.
                raise FileNotFoundError('Hay que especificar un archivo para guardar el objeto.')

        # Guardar el documento de manera que preserve carácteres no latinos (UTF-8)
        prep_json(símismo.receta['Coefs'])  # Convertir matrices a formato de lista y quitar objetos PyMC, si quedan

        with io.open(archivo, 'w', encoding='utf8') as d:
            json.dump(símismo.receta, d, ensure_ascii=False, sort_keys=True, indent=2)  # Guardar todo

    def cargar(símismo, fuente):
        """
        Esta función carga un archivo de receta para crear el Coso.

        :param fuente: Dónde se ubica el archivo.
        :type fuente: str

        """

        # Si necesario, agregar la extensión y el directorio
        if os.path.splitext(fuente)[1] != símismo.ext:
            fuente += símismo.ext
        if os.path.split(fuente)[0] == '':
            fuente = os.path.join(os.path.split(__file__)[0], 'Proyectos', fuente)

        # Intentar cargar el archivo (con formato UTF-8)
        try:
            with open(fuente, 'r', encoding='utf8') as d:
                nuevo_dic = json.load(d)

        except IOError as e:  # Si no funcionó, quejarse.
            raise IOError(e)

        else:  # Si se cargó el documento con éxito, usarlo
            # Copiar el documento a la receta de este Coso
            símismo.receta.clear()
            símismo.receta.update(nuevo_dic)

            # Convertir listas a matrices numpy en las ecuaciones (coeficientes)
            dic_lista_a_np(símismo.receta['coefs'])

    def _sacar_coefs_interno(símismo):
        """
        Esta función genera una lista de los coeficientes propios al objeto de interés para la calibración actual.
          Se debe implementar para cada Coso (objeto) que tiene coeficientes.

        :return: Una lista de diccionarios de coeficientes, con el formato siguiente:
           [ {calib1: distribución o [lista de valores],
              calib2: ibid,
              ...},
              {coeficiente 2...},
              ...
           ]
        :rtype: list

        """

        raise NotImplementedError

    def _sacar_líms_coefs_interno(símismo):
        """
        Esta función genera una lista de las límites de los coeficientes propios al objeto de interés para la
          calibración actual. Se debe implementar para cada Coso (objeto) que tiene coeficientes.

        :return: Un tuple, conteniendo:
          1. Una lista de diccionarios de coeficientes, con el formato siguiente:
           [ {calib1: distribución o [lista de valores],
              calib2: ibid,
              ...},
              {coeficiente 2...},
              ...
           ]

           2. Una lista de los límites de los coeficientes, en el mismo orden que (1.)
        :rtype: (list, list)

        """

        raise NotImplementedError


class Simulable(Coso):
    """
    Una subclase de Coso para objetos que se pueden simular y calibrar. (Por ejemplo, una Red AgroEcológica o una
      Parcela, pero NO un Insecto.
    """

    def __init__(símismo, nombre, fuente=None):
        """
        Un simulable se inicia como Coso.

        :param nombre: El nombre del simulable
        :type nombre: str

        :param fuente: Un archivo de cual cargar el Simulable
        :type fuente: str
        """

        # Primero, llamamos la función de inicio de la clase pariente 'Coso'
        super().__init__(nombre=nombre, fuente=fuente)

        # Añadir Calibraciones a la receta del Simulable. Este únicamente guarda la información sobre cada calibración.
        #   (Los resultados de las calibraciones se guardan en "coefs".
        if 'Calibraciones' not in símismo.receta:
            símismo.receta['Calibraciones'] = {'0': 'A prioris no informativos generados automáticamente por TIKON.'}

        # Para guardar los objetos relacionados con este Simulable. Sirve para encontrar todos los objetos que hay que
        #  mirar para una simulación o calibración.
        símismo.objetos = []

        # Indica si el Simulable está listo para una simulación.
        símismo.listo = False

        # Contendrá el objeto de modelo Bayesiano para la calibración
        símismo.ModBayes = None

        # Experimentos asociados
        símismo.exps = {}

        # Predicciones del modelo correspondiendo a los Experimentos asociados (para calibración y validación)
        símismo.predics_exps = {}

        # Predicciones de datos (para simulaciones normales)
        símismo.predics = {}

    def actualizar(símismo):
        """
        Esta función actualiza las matrices internas del Simulable para prepararlo para una simulación.
          Se aplica individualmente en todas las subclases de Simulable, que también deben llamar esta función al
          final para poner símismo.listo = True.

        """

        símismo.listo = True

    def simular(símismo, vals_inic, paso=1, tiempo_final=120, rep_parám=100, rep_estoc=1, extrn=None,
                calibs='Todos'):
        """
        Esta función corre una simulación del Simulable.

        :param vals_inic: Los valores iniciales para la simulación.
        :type vals_inic: dict

        :param paso: El paso de tiempo para la simulación
        :type paso: int

        :param tiempo_final: El tiempo final para la simulación.
        :type tiempo_final: int

        :param rep_parám: El número de repeticiones paramétricas para incluir en la simulación.
        :type rep_parám: int

        :param rep_estoc: El número de repeticiones estocásticas para incluir en la simulación
        :type rep_estoc: int

        :param extrn: Un diccionario externo de valores para usar en la simulación, si necesario. (Por ejemplo,
          aplicaciones de pesticidas para la simulación de una Red.)
        :type extrn: dict

        :param calibs: El nombre de la calibración que utilizar, o una lista de calibraciones para utilizar.
        :type calibs: list | str
        """

        # Actualizar el objeto, si necesario. Si ya se ha actualizado el objeto una vez, no se actualizará
        # automáticamente aquí (y no tendrá en cuenta cambios al objeto desde la última calibración).
        if not símismo.listo:
            símismo.actualizar()

        # Unos números útiles
        n_parcelas = valid_vals_inic(vals_inic)
        n_pasos = tiempo_final // paso

        # Preparar la lista de parámetros de interés
        lista_paráms, _ = símismo._gen_lista_coefs_interés_todo()
        calibs_filtr = símismo._filtrar_calibs(calibs=calibs, lista_paráms=lista_paráms)

        # Llenar las matrices internas de coeficientes
        comunes = (calibs == 'Comunes')
        símismo._llenar_coefs(n_rep_parám=rep_parám, calibs=calibs_filtr, comunes=comunes)

        # Preparar las matrices internas para guardar las predicciones
        símismo._prep_predics(n_pasos=n_pasos, n_rep_parám=rep_parám, n_rep_estoc=rep_estoc, n_parcelas=n_parcelas)

        # Simular el modelo
        símismo._calc_simul(paso=paso, n_pasos=n_pasos, extrn=extrn)

    def calibrar(símismo, nombre=None, aprioris=None, exper=None, paso=1,
                 n_iter=10000, quema=100, extraer=10):
        """
        Esta función calibra un Simulable. Para calibrar un modelo, hay algunas cosas que hacer:
          1. Estar seguro de el el nombre de la calibración sea válido
          2. Preparar listas de parámetros a calibrar, tanto como de sus límites matemáticas (para estar seguro de no
             calibrar un parámetro afuera de sus límites teoréticas).
          3. Generar la lista de nombres de calibraciones anteriores para emplear como distribuciones a prioris
             en la calibración de cada parámetro.
          4. Preparar los argumentos para la calibración, dado los experimentos vinculados.
          5. Generar un vector unidimensional, en orden reproducible, de las observaciones de los experimentos (para
             comparar más rápido después con las predicciones del modelo).
          6. Crear el modelo (ModBayes) para la calibración
          7. Por fin, calibrar el modelo.

        :param nombre: El nombre de la calibración.
        :type nombre: str

        :param aprioris: Las calibraciones anteriores que hay que utilizar para los a prioris.
        :type aprioris: int | str | list | None

        :param exper: Los experimentos vinculados al objeto a usar para la calibración. exper=None lleva al uso de
          todos los experimentos disponibles.
        :type exper: list | str | Experimento | None

        :param paso: El paso para la calibración
        :type paso: int

        :param n_iter: El número de iteraciones para la calibración.
        :type n_iter: int

        :param quema: El número de iteraciones iniciales que hay que botar. (Para evitar el efecto de condiciones
          iniciales en la calibración).
        :type quema: int

        :param extraer: Cada cuantas iteraciones guardar (para limitar el efecto de autocorrelación entre iteraciones).
          extraer = 1 lleva al uso de todas las iteraciones.
        :type extraer: int

        """

        # 1. Primero, validamos el nombre y, si necesario, lo creamos.
        # Si se especificó un nombre para la calibración, asegurarse de que no existe en la lista de calibraciones
        # existentes
        if nombre is not None and nombre in símismo.receta['Calibraciones']:
            raise ValueError('Nombre de calibración ya existe en el objeto. Escoger otro nombre y volver a intentar.')

        # Si no se especificó nombre para la calibración, generar un número de identificación aleatorio.
        if nombre is None:
            nombre = int(np.random.uniform() * 1e10)

            # Evitar el caso muy improbable de que el código aleatorio ya existe
            while nombre in símismo.receta['Calibraciones']:
                nombre = int(np.random.uniform() * 1e10)
        nombre = str(nombre)

        # 2. Creamos la lista de parámetros que hay que calibrar
        lista_paráms, lista_líms = símismo._gen_lista_coefs_interés_todo()

        # 3. Filtrar coeficientes por calib
        if aprioris is None:
            aprioris = ['0']
        lista_aprioris = símismo._filtrar_calibs(calibs=aprioris, lista_paráms=lista_paráms)

        # 4. Preparar el diccionario de argumentos para la función "simul_calib", según los experimentos escogidos
        # para la calibración.

        exper = símismo._prep_lista_exper(exper=exper)

        dic_argums = símismo._prep_args_simul_exps(exper=exper, n_rep_paráms=1, n_rep_estoc=1)
        dic_argums['paso'] = paso  # Guardar el paso en el diccionario también

        # 5. Generar el vector numpy de observaciones para los experimentos
        obs = símismo._prep_obs_exper(exper=exper)

        # 6. Creamos el modelo ModBayes de calibración, lo cual genera variables PyMC
        símismo.ModBayes = ModBayes(función=símismo._simul_exps,
                                    dic_argums=dic_argums,
                                    obs=obs,
                                    lista_paráms=lista_paráms,
                                    aprioris=lista_aprioris,
                                    lista_líms=lista_líms,
                                    id_calib=nombre,
                                    función_llenar_coefs=símismo._llenar_coefs
                                    )

        # 8. Calibrar el modelo, llamando las ecuaciones bayesianas a través del objeto ModBayes
        símismo.ModBayes.calib(rep=n_iter, quema=quema, extraer=extraer)

    def avanzar_calib(símismo, rep=10000, quema=100, extraer=10):
        """
        Añade a una calibración ya empezada.

        :param rep: El número de iteraciones extras.
        :type rep: int

        :param quema: El número de iteraciones iniciales que hay que botar.
        :type quema: int

        :param extraer: Cada cuántas iteraciones guardar.
        :type extraer: int

        """

        # Si ya no existe un modelo de calibración, no podemos avanzarla.
        if símismo.ModBayes is None:
            raise TypeError('Hay que iniciar una calibración antes de avanzarla.')

        # Avanzar la calibración.
        símismo.ModBayes.calib(rep=rep, quema=quema, extraer=extraer)

    def guardar_calib(símismo, descrip, utilizador, contacto):
        """
        Esta función guarda una calibración existente para uso futuro.

        :param descrip: La descripción de la calibración (para referencia futura).
        :type descrip: str

        :param utilizador: El nombre del utilizador que hizo la calibración.
        :type utilizador: str

        :param contacto: El contacto del utilizador
        :type contacto: str

        """

        # Si no hay modelo, no hay nada para guardar.
        if símismo.ModBayes is None:
            raise ValueError('No hay calibraciones para guardar')

        # La fecha y hora a la cual se guardó
        ahora = ft.now().strftime('%Y-%m-%d %H:%M:%S')

        # El nombre de identificación de la calibración.
        nb = símismo.ModBayes.id

        # Guardar la descripción de esta calibración en el diccionario del objeto
        símismo.receta['Calibraciones'][nb] = dict(Descripción=descrip,
                                                   Fecha=ahora,
                                                   Utilizador=utilizador,
                                                   Contacto=contacto,
                                                   Config=símismo.receta['estr'].deepcopy())

        # Guardar los resultados de la calibración
        símismo.ModBayes.guardar()

        # Borrar el objeto de modelo, ya que no se necesita
        símismo.ModBayes = None

    def añadir_exp(símismo, experimento, corresp):
        """
        Esta función añade un experimento al Simulable.

        :param experimento: El experimento para añadir
        :type experimento: Experimento

        :param corresp: Un diccionario con la información necesaria para hacer la conexión entre el experimento
          y las predicciones del Simulable.
        :type corresp: dict

        """

        símismo.exps[experimento.nombre] = experimento

        símismo._acción_añadir_exp(experimento=experimento, corresp=corresp)

    def validar(símismo, exper, calibs=None, paso=1, n_rep_parám=100, n_rep_estoc=100, dibujar=True):
        """
        Esta función valida el modelo con datos de observaciones de experimentos.

        :param exper: Los experimentos vinculados al objeto a usar para la calibración. exper=None lleva al uso de
          todos los experimentos disponibles.
        :type exper: list | str | Experimento | None

        :param calibs: Las calibraciones que hay que usar para la validación.
        :type calibs: list | str | None

        :param paso: El paso para la validación
        :type paso: int

        :param n_rep_parám: El número de repeticiones de parámetros.
        :type n_rep_parám: int

        :param n_rep_estoc: El número de repeticiones estocásticas.
        :type n_rep_estoc: int

        :param dibujar: Si hay que generar gráficos de los resultados.
        :type dibujar: bool

        :return: Un diccionario con los resultados de la validación.
        :rtype: dict
        """

        # Encontrar los parámetros de interés
        lista_paráms = símismo._gen_lista_coefs_interés_todo()[0]

        # Si no se especificaron calibraciones para validar, tomamos la calibración activa, si hay, y en el caso
        # contrario tomamos el conjunto de todas las calibraciones anteriores.
        if calibs is None:
            if símismo.ModBayes is None:
                calibs = 'Todos'
            else:
                calibs = símismo.ModBayes.id

        lista_calibs = símismo._filtrar_calibs(calibs=calibs, lista_paráms=lista_paráms)

        # Llenar coeficientes
        símismo._llenar_coefs(n_rep_parám=n_rep_parám, calibs=lista_calibs, comunes=(calibs == 'Comunes'))

        exper = símismo._prep_lista_exper(exper=exper)

        # Generar el vector numpy de observaciones para los experimentos
        obs = símismo._prep_obs_exper(exper=exper)

        # Simular los experimentos
        dic_argums = símismo._prep_args_simul_exps(exper=exper, n_rep_estoc=n_rep_estoc, n_rep_paráms=n_rep_parám)
        preds = símismo._simul_exps(**dic_argums, paso=paso)

        # Si hay que dibujar, dibujar
        if dibujar:
            símismo.dibujar()

        # Procesar los datos de la validación
        return símismo._procesar_validación(vector_obs=obs, vector_preds=preds)

    def dibujar(símismo, mostrar=True, archivo=''):
        """
        Una función para generar gráficos de los resultados del objeto.
        """

        raise NotImplementedError

    def _llenar_coefs(símismo, n_rep_parám, calibs, comunes):
        """
        Transforma los diccionarios de coeficientes a matrices internas (para aumentar la rapidez de la simulación).
          Las matrices internas, por supuesto, dependerán del tipo de Simulable en cuestión. No obstante, todas
          tienen la forma siguiente: eje 0 = repetición paramétrica, eje 1+ : dimensiones opcionales.

        :param n_rep_parám: El número de repeticiones paramétricas que incluir.
        :type n_rep_parám: int

        :param calibs: Una lista de los nombres de las calibraciones, o el nomre de una calibración, que hay que
          incluir.
        :type calibs: list | str

        :param comunes: Si queremos guardar las correspondencias de la distribución multidimensional entre
          parámetros calibrados en la misma calibración.
        :type comunes: bool

        """

        raise NotImplementedError

    def _prep_predics(símismo, n_pasos, n_rep_parám, n_rep_estoc, n_parcelas):
        """
        Esta función prepara el diccionario de predicciones para guardar los resultados de una simulación.
          Se tiene que implementar para cada tipo de Simulable. Modifica símismo.predics, así que no devuelve
          ningún valor.

        :param n_pasos: El número de pasos de la simulación que vamos a hacer.
        :type n_pasos: int

        :param n_rep_parám: El número de repeticiones paramétricas.
        :type n_rep_parám: int

        :param n_rep_estoc: El número de repeticiones estocásticas.
        :type n_rep_estoc: int

        :param n_parcelas: El número de parcelas en la simulación.
        :type n_parcelas: int

        """

        raise NotImplementedError

    def _calc_simul(símismo, paso, n_pasos, extrn=None):
        """
        Esta función aumenta el modelo para cada paso en la simulación. Se usa en simulaciones normales, tanto como en
          simulaciones de experimentos.

        :param paso: El paso para la simulación
        :type paso: int

        :param n_pasos: El número de pasos en la simulación.
        :type n_pasos: int

        :param extrn: Un diccionario externo, si necesario, con información para la simulación.
        :type extrn: dict

        """

        # Para cada paso de tiempo, incrementar el modelo
        for i in range(1, n_pasos):
            símismo._incrementar(paso, i=i, extrn=extrn)

    def _incrementar(símismo, paso, i, extrn):
        """
        Esta función incrementa el modelo por un paso. Se tiene que implementar en cada subclase de Simulable.
        
        :param paso: El paso con cual incrementar el modelo
        :type paso: int

        :param i: El número de este incremento en la simulación
        :type i: int

        :param extrn: Un diccionario de valores externos al modelo, si necesario
        :type extrn: dict

        """

        # Dejamos la implementación del incremento del modelo a las subclases individuales.
        raise NotImplementedError

    def _gen_lista_coefs_interés_todo(símismo):

        """
        Esta función devuelve una lista de todos los coeficientes de un Simulable y de sus objetos de manera
          recursiva, tanto como una lista, en el mismo orden, de los límites de dichos coeficientes.

        :return: Un tuple conteniendo una lista de todos los coeficientes de interés para la calibración y una lista
          de sus límites.
        :rtype: (list, list)

        """

        def sacar_coefs_recursivo(objeto):
            """
            La implementación recursiva de la función.

            :param objeto: El objeto Simulable a cual hay que sacar los coeficientes.
            :type objeto: Simulable

            :return: Un tuple, como descrito en la documentación de la función arriba.
            :rtype: (list, list)
            """

            # Inicializar las listas de coeficientes y de límites con los coeficientes y límites del objeto actual.
            lista_coefs = objeto._sacar_coefs_interno()
            lista_líms = objeto._sacar_líms_coefs_interno()

            if isinstance(objeto, Simulable):
                # Ahora, hacer lo mismo para cada objeto Simulable contenido en este objeto.
                for obj in objeto.objetos:
                    resultado = sacar_coefs_recursivo(obj)
                    lista_coefs += resultado[0]
                    lista_líms += resultado[1]

            # Devolver la lista de coeficientes y la lista de límites
            return lista_coefs, lista_líms

        # Implementar la función recursiva arriba
        return sacar_coefs_recursivo(símismo)

    def _sacar_coefs_interno(símismo):
        """
        Esta función genera una lista de los coeficientes propios al objeto de interés para la calibración actual.
          Se debe implementar para cada Coso (objeto) que tiene coeficientes.

        :return: Una lista de diccionarios de coeficientes, con el formato siguiente:
           [ {calib1: distribución o [lista de valores],
              calib2: ibid,
              ...},
              {coeficiente 2...},
              ...
           ]
        :rtype: list

        """

        raise NotImplementedError

    def _sacar_líms_coefs_interno(símismo):
        """
        Esta función genera una lista de las límites de los coeficientes propios al objeto de interés para la
          calibración actual. Se debe implementar para cada Coso (objeto) que tiene coeficientes.

        :return: Un tuple, conteniendo:
          1. Una lista de diccionarios de coeficientes, con el formato siguiente:
           [ {calib1: distribución o [lista de valores],
              calib2: ibid,
              ...},
              {coeficiente 2...},
              ...
           ]

           2. Una lista de los límites de los coeficientes, en el mismo orden que (1.)
        :rtype: (list, list)

        """

        raise NotImplementedError

    def _acción_añadir_exp(símismo, experimento, corresp):
        """

        :param experimento:
        :type experimento:
        :param corresp:
        :type corresp:
        :return:
        :rtype:
        """
        raise NotImplementedError

    def _prep_obs_exper(símismo, exper):
        """
        Prepara un vector numpy de las obsevaciones de los experimentos.

        :param exper: Una lista de los nombres de los experimentos que vamos a incluir para esta calibración.
        :type exper: list

        :return: Un vector, en orden reproducible, de las observaciones de los experimentos.
        :rtype: np.ndarray
        """

        raise NotImplementedError

    def _prep_args_simul_exps(símismo, exper, n_rep_estoc, n_rep_paráms):
        """
        Prepara un diccionaro de los argumentos para simul_exps. El diccionario debe de tener la forma elaborada
          abajo. Se implementa para cada subclase de Simulable.

        :param exper: Una lista de los nombres de los experimentos para incluir
        :type exper: list

        :param n_rep_estoc: El número de repeticiones estocásticas para las simulaciones.
        :type n_rep_estoc: int

        :param n_rep_paráms: El número de repeticiones paramétricas para las simulaciones.
        :type n_rep_paráms: int

        :return: Un diccionario del formato siguiente:
           {
            datos_inic: {},
            n_pasos: {},
            extrn: {}
            }
          Donde cada elemento del diccionario es un diccionario con los nombres de los experimentos como llaves.
        :rtype: dict

        """

        raise NotImplementedError

    def _simul_exps(símismo, datos_inic, paso, n_pasos, extrn):
        """
        Esta es la función que se calibrará cuando se calibra o valida el modelo. Devuelve las predicciones del modelo
          correspondiendo a los valores observados, y eso en el mismo orden.
        Todos los argumentos de esta función, a parte "paso," son diccionarios con el nombre de los experimentos para
          simular como llaves.

        :param datos_inic: Un diccionario de los datos iniciales para la simulación de cada experimento.
        :type datos_inic: dict

        :param paso: El paso para la simulación
        :type paso: int

        :param n_pasos: Un diccionario con el número de pasos para cada simulación
        :type n_pasos: dict

        :param extrn: Un diccionario de valores externas a pasar a la simulación, si aplica.
        :type extrn: dict

        :return: Matriz unidimensional Numpy de las predicciones del modelo correspondiendo a los valores observados.
        :rtype: np.ndarray

        """

        # Hacer una copia de los datos iniciales (así que, en la calibración del modelo, una iteración no borará los
        # datos iniciales para las próximas).
        símismo.predics_exps = copiar.deepcopy(datos_inic)

        # Para cada experimento...
        for exp in datos_inic:
            # Apuntar el diccionario de predicciones del Simulable al diccionario apropiado en símismo.predics_exps.
            símismo.predics = símismo.predics_exps[exp]

            # Simular el modelo
            símismo._calc_simul(paso=paso, n_pasos=n_pasos[exp], extrn=extrn[exp])

        # Convertir los diccionarios de predicciones en un vector numpy.
        vector_predics = símismo._procesar_predics_calib()

        # Devolver el vector de predicciones.
        return vector_predics

    def _procesar_predics_calib(símismo):
        """
        Procesa las predicciones de simulación de experimentos (predics_exps) del modelo y genera una matriz numpy
          unidimensional de las predicciones. Se debe implementar para cada subclase de Simulable.

        :return: Un vector numpy de las predicciones del modelo.
        :rtype: np.ndarray
        """

        raise NotImplementedError

    def _procesar_validación(símismo, vector_obs, vector_preds):
        """
        Esta función procesa los resultados de la validación del modelo. Se tiene que implementar para cada subclase
          de Simulable.

        :param vector_obs: El vector de observaciones.
        :type vector_obs: np.ndarray

        :param vector_preds: El vector de predicciones.
        :type vector_preds: np.ndarray

        :return: Un diccionario del análisis de la validación.
        :rtype: dict
        """

        raise NotImplementedError

    def _prep_lista_exper(símismo, exper):
        """
        Esta lista prepara la lista de nombres de los experimentos para validación o calibración.

        :param exper: Los experimentos a usar.
        :type exper: list | str | Experimento | None

        :return: Una lista de los nombres de los experimentos.
        :rtype: list
        """

        # Si "experimentos" no se especificó, usar todos los experimentos vinculados con el Simulable
        if exper is None:
            exper = list(símismo.exps)

        # Si exper no era una lista, hacer una.
        if not type(exper) is list:
            exper = [exper]

        # Para cada elemento de exper, poner únicamente el nombre.
        for n, exp in enumerate(exper):
            if type(exp) is Experimento:
                exper[n] = exp.nombre

        # Devolver exper
        return exper

    def _filtrar_calibs(símismo, calibs, lista_paráms):
        """
        Esta función, dado una lista de diccionarios de calibraciones de parámetros y una especificación de cuales
          calibraciones guardar, genera un lista de los nombre de las calibraciones que hay que incluir.
          Se usa para preparar simulaciones, calibraciones y validaciones.
        Notar que distribuciones a priori especificadas por el usuario para una calibración se aplican más tarde, en
          el objeto ModBayes sí mismo.

        :param calibs: Una indicación de cuales calibraciones utilizar.
          Puede ser un número o texto con el nombre/id de la calibración deseada.
          Puede ser una lista de nombres de calibraciones deseadas.
          Puede ser una de las opciones siguientes:
             1. 'Todos': Usa todas las calibraciones disponibles en los objetos involucrados en la simulación.
             2. 'Comunes': Usa únicamente las calibraciones comunes entre todos los objetos involucrados en la
                simulación
             3. 'Correspondientes': Usa únicamente las calibraciones que fueron calibradas con este objeto Simulable
                en particular.

        :type calibs: str | float | list

        :param lista_paráms:
        :type lista_paráms: list

        :return: Una lista de las calibraciones que hay que utilizar.
        :rtype: list
        """

        # Preparar el parámetro "calibs"

        if type(calibs) is str and calibs not in ['Todos', 'Comunes', 'Correspondientes']:
            # Si calibs es el nombre de una calibración (y no un nombre especial)...

            # Convertirlo en fecha
            calibs = [calibs]

        # Si calibs es una lista...
        if type(calibs) is list:

            # Para cada elemento de la lista...
            for n, calib in enumerate(calibs):

                # Asegurarse de que es en formato de texto.
                calibs[n] = str(calib)

        # Ahora, preparar la lista de calibraciones según las especificaciones en "calibs". Primero, los casos
        # especiales.

        if type(calibs) is str:
            # Si "calibs" es un nombre especial...

            if calibs == 'Todos':
                # Tomamos todas las calibraciones existentes en cualquier de los parámetros.

                # Una lista vacía para contener las calibraciones
                lista_calibs = []

                # Para cada parámetro...
                for parám in lista_paráms:

                    # Para cada calibración de este parámetro...
                    for id_calib in parám:

                        if id_calib not in lista_calibs:

                            # Si no existe ya la calibración en nuestra lista, añadirla
                            lista_calibs.append(id_calib)

            elif calibs == 'Comunes':
                # Tomamos todas las calibraciones en común entre los parámetros.

                # Hacemos una lista de calibraciones con las calibraciones del primer parámetro.
                lista_calibs = list(lista_paráms[0])

                # Para cada otro parámetro en la lista...
                for parám in lista_paráms[1:]:

                    # Para cada calibración en nuestra lista...
                    for id_calib in lista_calibs:

                        # Si la calibración no existe para este parámetro...
                        if id_calib not in parám:

                            # Borrarla de nuestra lista.
                            lista_calibs.remove(id_calib)

            elif calibs == 'Correspondientes':

                # Usar todas las calibraciones calibradas con este objeto Simulable.
                lista_calibs = [x for x in calibs if x in símismo.receta['Calibraciones']]

            else:

                # Si se especificó otro valor (lo que no debería de ser posible dado la preparación que damos a
                # "calibs" arriba), hay un error.
                raise ValueError("Parámetro 'calibs' inválido.")

            # Quitar la distribución a priori no informativa.
            if '0' in lista_calibs:
                lista_calibs.remove('0')

        elif type(calibs) is list:
            # Si se especificó una lista de calibraciones en particular, utilizarlas, si están en al menos un objeto
            # involucrado en la simulación

            # Una lista de todas las calibraciones en lista_paráms.
            todos_calibs = [c for p in lista_paráms for c in p]

            # Guardar únicamente las calibraciones de "calibs" si están en todos_calibs.
            lista_calibs = [c for c in calibs if c in todos_calibs]

        else:

            # Si "calibs" no era ni texto ni una lista, hay un error.
            raise ValueError("Parámetro 'calibs' inválido.")

        # Verificar la lista de calibraciones generada
        if len(lista_calibs) == 0:

            # Si no quedamos con ninguna calibración, usemos la distribución a priori no informativa
            lista_calibs = ['0']

        elif len(lista_calibs) == 1:

            # Si únicamente nos quedamos con la distribución a priori no informativa, sería mejor avisarle al
            # usuario.
            avisar.warn('Usando la distribución a priori no informativa por falta de calibraciones anteriores.')

        # Devolver la lista de calibraciones.
        return lista_calibs


def dic_lista_a_np(d):
    """
    Esta función recursiva toma las listas numéricas contenidas en un diccionario de estructura arbitraria y las
      convierte en matrices numpy. Cambia el diccionario in situ, así que no devuelve ningún valor.
      Una nota importante: esta función puede tomar diccionarios de estructura arbitraria, pero no convertirá
      exitosamente diccionarios que contienen listas que a su turno contienen otras listas para convertir a matrices
      numpy. No hay problema con listas compuestas representando matrices multidimensionales.

    :param d: El diccionario para convertir
    :type d: dict

    """

    # Para cada itema (llave, valor) del diccionario
    for ll, v in d.items():
        if type(v) is dict:
            # Si el itema era otro diccionario...

            # Llamar esta función de nuevo
            dic_lista_a_np(v)

        elif type(v) is list:
            # Si el itema era una lista...
            try:
                # Ver si se puede convertir a una matriz numpy
                d[ll] = np.array(v, dtype=float)
            except ValueError:
                # Si no funcionó, pasar al siguiente
                pass


def prep_json(d):
    """
    Esta función recursiva prepara un diccionario de coeficientes para ser guardado en formato json. Toma las listas
      numéricas contenidas en un diccionario de estructura arbitraria y las convierte en matrices de numpy. También
      quita variables de typo PyMC que no sa han guardado en forma de matriz. Cambia el diccionario in situ, así que
      no devuelve ningún valor. Una nota importante: esta función puede tomar diccionarios de estructura arbitraria,
      pero no convertirá exitosamente diccionarios que contienen listas de matrices numpy.

    :param d: El diccionario para convertir
    :type d: dict

    """

    # Para cada itema (llave, valor) del diccionario
    for ll, v in d.items():

        if type(v) is dict:

            # Si el itema era otro diccionario, llamar esta función de nuevo con el nuevo diccionario
            prep_json(v)

        elif type(v) is str:

            # Quitar distribuciones a priori especificadas por el usuario.
            if ll == 'especificado':
                d.pop(ll)

        elif isinstance(v, pymc.Stochastic):

            # Si el itema es un variable de PyMC, borrarlo
            d.pop(ll)


def valid_vals_inic(d, n=None):
    """
    Esta función valida que los datos iniciales de una simulación tengan dimensiones compatibles y que no haya errores.
        Es una función recursiva que pasa a través de cada diccionario en d.

    :param d: El diccionario de datos iniciales.
    :type d: dict

    :param n: El número de parcelas. No hay que definirla, por que sirve únicamente por la recursión de la función.
    :type n: int

    :return: El número de parcelas en los datos iniciales.
    :rtype: int

    """

    # Para cada elemento en el diccionario...
    for ll, v in d.items():

        if type(v) is dict:
            # Si es otro diccionario, llamar la misma función con este nuevo diccionario.
            valid_vals_inic(v, n)

        elif type(v) is np.ndarray:
            # Si es matriz numpy...

            # Sacar el número de parcelas por el tamaño de la dimensión 0 de la matriz.
            n_parcelas = v.shape[0]

            if n is None:
                # Si este es la primera iteración, guardar el número de parcelas en "n".
                n = n_parcelas

            elif n_parcelas != n:
                # Si no es la primera iteración de la función, y el número de parcelas no corresponde con el número
                # de parcelas anteriormente, hay un problema con los datos iniciales.
                raise ValueError('Error en el formato de los datos iniciales')

    # Devolver el número de parcelas en los datos iniciales.
    return n
