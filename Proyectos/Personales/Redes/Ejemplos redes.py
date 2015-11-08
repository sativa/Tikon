from REDES.INSECTOS import Simple
from REDES.REDES import Red

# Unos ejemplos del uso del módulo de insectos y del módulo de redes agroecológicas

# Crear nuestros insectos
mosca = Simple('mosca')
araña = Simple('araña')

# Decidir quién come quién
araña.secome(mosca)
mosca.secome('cebolla')

# Crear y probar la red agroecológica
red_cebolla = Red('red_cebolla', [mosca, araña])

red_cebolla.ejec(poblaciones_iniciales={'mosca': {'Adulto': 100}, 'araña': {'Adulto': 10}})

red_cebolla.simul(paso=1, estado_cultivo=100000, tiempo_final=300, rep=100)

# Calibrar la red según datos 'reales':
red_cebolla.datos = {'mosca': {'Adulto': (list(range(11)),
                                          [100, 25, 30, 33, 40, 50, 44, 12, 11, 9])
                               },
                     'araña': {'Adulto': (list(range(11)),
                                          [10, 4, 5, 3, 4, 5, 3, 1, 1, 3])
                               }
                     }
