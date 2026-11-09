-- =====================================================================
-- MEDIDAS COMO VISTAS SQL · se pega y ejecuta en Supabase > SQL Editor
-- Se puede volver a ejecutar cuando quieras: borra y recrea todas las vistas.
-- security_invoker = true hace que las vistas respeten el RLS del usuario que consulta
-- (cada persona solo ve los grupos a los que pertenece).
--
-- Todo se calcula POR GRUPO (columna grupo_id) y en dos formas (columna "modo"):
--   'historico' : suma todas las visitas; cada valoración cuenta.
--   'actual'    : solo la última valoración de cada persona por restaurante;
--                 si vuelven y cambian de opinión, la nueva reemplaza a la anterior.
-- =====================================================================

drop view if exists v_valoracion cascade;   -- borra también todas las vistas que dependen de ella

-- ---------------------------------------------------------------------
-- Base: una fila por valoración, con nombres legibles y la nota global.
-- nota_global = promedio de los 5 criterios (no se guarda en la tabla).
-- ---------------------------------------------------------------------
create view v_valoracion with (security_invoker = true) as
select
  f.valoracion_id,
  f.grupo_id,
  f.restaurante_id,
  r.nombre                         as restaurante,
  r.comuna,
  t.tipo,
  f.fecha_id,
  f.persona_id,
  coalesce(p.apodo, p.nombre)      as persona,
  p.color_hex,
  p.foto_url,
  o.ocasion,
  f.gasto_persona,
  f.precio_calidad,
  f.sabor_presentacion,
  f.entorno,
  f.atencion,
  f.limpieza,
  round((f.precio_calidad + f.sabor_presentacion + f.entorno
         + f.atencion + f.limpieza) / 5.0, 2) as nota_global,
  f.volveria_recomendaria,
  f.comentario,
  f.creado_en
from fact_valoracion f
join dim_restaurante r           on r.restaurante_id = f.restaurante_id
left join dim_tipo_restaurante t on t.tipo_id        = r.tipo_id
join dim_persona p               on p.persona_id     = f.persona_id
left join dim_ocasion o          on o.ocasion_id     = f.ocasion_id;

-- Última valoración de cada persona en cada restaurante, dentro de cada grupo
create view v_valoracion_actual with (security_invoker = true) as
select distinct on (grupo_id, restaurante_id, persona_id) *
from v_valoracion
order by grupo_id, restaurante_id, persona_id, fecha_id desc, creado_en desc;

-- Las dos bases juntas, etiquetadas con "modo"
create view v_valoracion_modo with (security_invoker = true) as
select 'historico'::text as modo, h.* from v_valoracion h
union all
select 'actual'::text    as modo, a.* from v_valoracion_actual a;

-- ---------------------------------------------------------------------
-- Resumen general por grupo. "salidas" siempre cuenta todas las visitas reales
-- (un restaurante en un día); el resto cambia según el modo.
-- ---------------------------------------------------------------------
create view v_resumen with (security_invoker = true) as
select
  m.grupo_id,
  m.modo,
  (select count(distinct (v.restaurante_id, v.fecha_id))
     from v_valoracion v where v.grupo_id = m.grupo_id)         as salidas,
  count(distinct m.restaurante_id)                              as restaurantes_visitados,
  round(avg(m.nota_global), 2)                                  as nota_global,
  round(avg(m.gasto_persona))                                   as gasto_prom_persona,
  round(100.0 * avg(m.volveria_recomendaria::int))              as pct_volveria
from v_valoracion_modo m
group by m.grupo_id, m.modo;

-- ---------------------------------------------------------------------
-- Ranking de restaurantes por grupo. rango_precio por cuartiles del gasto promedio
-- dentro del grupo ($ = más barato ... $$$$ = más caro); vacío si no hay gastos.
-- "visitas" siempre cuenta las visitas reales, en ambos modos.
-- ---------------------------------------------------------------------
create view v_ranking_restaurante with (security_invoker = true) as
with base as (
  select
    grupo_id, modo, restaurante_id, restaurante, comuna, tipo,
    count(*)                                         as valoraciones,
    round(avg(nota_global), 2)                       as nota_global,
    round(avg(gasto_persona))                        as gasto_prom_persona,
    round(100.0 * avg(volveria_recomendaria::int))   as pct_volveria
  from v_valoracion_modo
  group by grupo_id, modo, restaurante_id, restaurante, comuna, tipo
),
visitas as (
  select grupo_id, restaurante_id, count(distinct fecha_id) as visitas
  from v_valoracion
  group by grupo_id, restaurante_id
),
cuartil as (
  select grupo_id, modo, restaurante_id,
         ntile(4) over (partition by grupo_id, modo order by gasto_prom_persona) as q
  from base
  where gasto_prom_persona is not null
)
select
  b.grupo_id, b.modo, b.restaurante_id, b.restaurante, b.comuna, b.tipo,
  v.visitas, b.valoraciones, b.nota_global, b.gasto_prom_persona, b.pct_volveria,
  r.latitud, r.longitud,
  repeat('$', c.q::int)                                                                    as rango_precio,
  rank() over (partition by b.grupo_id, b.modo order by b.nota_global desc, v.visitas desc) as posicion
from base b
join visitas v         on v.grupo_id = b.grupo_id and v.restaurante_id = b.restaurante_id
join dim_restaurante r on r.restaurante_id = b.restaurante_id
left join cuartil c    on c.grupo_id = b.grupo_id and c.modo = b.modo
                      and c.restaurante_id = b.restaurante_id;

-- ---------------------------------------------------------------------
-- Entre las personas del grupo
-- ---------------------------------------------------------------------
create view v_persona_resumen with (security_invoker = true) as
select
  grupo_id, modo, persona_id, persona, color_hex,
  count(*)                                         as valoraciones,
  round(avg(nota_global), 2)                       as nota_global,
  round(avg(gasto_persona))                        as gasto_prom,
  round(100.0 * avg(volveria_recomendaria::int))   as pct_volveria
from v_valoracion_modo
group by grupo_id, modo, persona_id, persona, color_hex;

-- Los 5 criterios en formato largo (una fila por valoración y criterio)
create view v_criterio_largo with (security_invoker = true) as
select
  v.grupo_id, v.modo, v.valoracion_id, v.restaurante_id, v.persona_id, v.persona, v.color_hex,
  c.criterio, c.valor
from v_valoracion_modo v
cross join lateral (values
  ('Precio / calidad',     v.precio_calidad),
  ('Sabor y presentación', v.sabor_presentacion),
  ('Entorno',              v.entorno),
  ('Atención',             v.atencion),
  ('Limpieza',             v.limpieza)
) as c(criterio, valor);

create view v_criterio_persona with (security_invoker = true) as
select grupo_id, modo, persona_id, persona, color_hex, criterio, round(avg(valor), 2) as promedio
from v_criterio_largo
group by grupo_id, modo, persona_id, persona, color_hex, criterio;

create view v_criterio_persona_restaurante with (security_invoker = true) as
select grupo_id, modo, restaurante_id, persona_id, persona, color_hex, criterio,
       round(avg(valor), 2) as promedio
from v_criterio_largo
group by grupo_id, modo, restaurante_id, persona_id, persona, color_hex, criterio;

-- Diferencia entre las notas del grupo cuando al menos dos personas valoraron
-- (rango = nota más alta menos nota más baja):
--   historico: la misma salida (restaurante + día)
--   actual:    el mismo restaurante (valoraciones vigentes, aunque sean de días distintos)
create view v_pares with (security_invoker = true) as
select
  grupo_id, 'historico'::text as modo, restaurante_id, restaurante, fecha_id,
  round(max(nota_global) - min(nota_global), 2)        as dif_global,
  max(precio_calidad)     - min(precio_calidad)        as dif_precio_calidad,
  max(sabor_presentacion) - min(sabor_presentacion)    as dif_sabor_presentacion,
  max(entorno)            - min(entorno)               as dif_entorno,
  max(atencion)           - min(atencion)              as dif_atencion,
  max(limpieza)           - min(limpieza)              as dif_limpieza
from v_valoracion
group by grupo_id, restaurante_id, restaurante, fecha_id
having count(*) >= 2
union all
select
  grupo_id, 'actual'::text, restaurante_id, restaurante, max(fecha_id),
  round(max(nota_global) - min(nota_global), 2),
  max(precio_calidad)     - min(precio_calidad),
  max(sabor_presentacion) - min(sabor_presentacion),
  max(entorno)            - min(entorno),
  max(atencion)           - min(atencion),
  max(limpieza)           - min(limpieza)
from v_valoracion_actual
group by grupo_id, restaurante_id, restaurante
having count(*) >= 2;

-- Índice de coincidencia: 100 = notas idénticas; 0 = máxima diferencia posible (4 puntos)
create view v_coincidencia with (security_invoker = true) as
select
  grupo_id, modo,
  count(*)                                            as salidas_compartidas,
  round(avg(dif_global), 2)                           as dif_global_prom,
  round(100 * (1 - avg(dif_global) / 4.0))            as indice_coincidencia
from v_pares
group by grupo_id, modo;

-- Criterio donde más se diferencian
create view v_discrepancia_criterio with (security_invoker = true) as
select p.grupo_id, p.modo, c.criterio, round(avg(c.dif), 2) as discrepancia_prom
from v_pares p
cross join lateral (values
  ('Precio / calidad',     p.dif_precio_calidad),
  ('Sabor y presentación', p.dif_sabor_presentacion),
  ('Entorno',              p.dif_entorno),
  ('Atención',             p.dif_atencion),
  ('Limpieza',             p.dif_limpieza)
) as c(criterio, dif)
group by p.grupo_id, p.modo, c.criterio;

-- ---------------------------------------------------------------------
-- Permisos para la API
-- ---------------------------------------------------------------------
grant select on
  v_valoracion, v_valoracion_actual, v_valoracion_modo, v_resumen,
  v_ranking_restaurante, v_persona_resumen, v_criterio_largo, v_criterio_persona,
  v_criterio_persona_restaurante, v_pares, v_coincidencia, v_discrepancia_criterio
to authenticated;
