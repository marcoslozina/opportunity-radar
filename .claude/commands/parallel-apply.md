Implementá las tasks del cambio actual en paralelo donde sea posible.

1. Recuperar tasks de Engram:
   - mem_search(query: "sdd/{cambio-actual}/tasks")
   - mem_get_observation(id) para lista completa

2. Analizar dependencias entre tasks:
   - Identificar qué tasks son independientes entre sí
   - Identificar qué tasks dependen de otras (deben ir secuencial)
   - Presentar el análisis al usuario antes de ejecutar

   Formato:
   ```
   Tasks independientes (van en paralelo):
     - task-1: [título]
     - task-2: [título]

   Tasks secuenciales (dependen de anteriores):
     - task-3: depende de task-1 y task-2
     - task-4: depende de task-3
   ```

3. Pedir confirmación: "¿Arrancamos con este orden?"

4. Ejecutar por grupos:
   - Grupo paralelo 1: lanzar tasks independientes como delegate simultáneos
   - Esperar grupo 1
   - Grupo secuencial: ejecutar tasks dependientes en orden con task (sync)
   - Repetir hasta completar todas

5. Después de cada grupo: mostrar qué se completó y qué sigue.

6. Al terminar todo: sugerir "/sdd-verify" para validar contra el spec.
