-- =====================================================================
-- MIGRACIÓN A GRUPOS · se ejecuta UNA SOLA VEZ
-- Supabase > SQL Editor > New query > pegar todo > Run
-- Después, ejecutar vistas.sql (que ahora incluye grupo_id).
--
-- Qué hace:
--   * Crea grupos (hasta 5 por persona, hasta 5 personas por grupo) y su líder.
--   * Asigna todas tus valoraciones actuales a un grupo inicial llamado "Nosotros".
--   * Cambia los permisos: cada grupo ve solo sus valoraciones.
--   * Restaurantes: catálogo compartido; solo quien lo creó puede editarlo.
--   * Crea el almacenamiento para las fotos de perfil.
-- No borra ninguna valoración, restaurante ni usuario.
-- =====================================================================

do $$
begin
  if to_regclass('public.dim_grupo') is not null then
    raise exception 'La migración ya se ejecutó. No hace falta correrla de nuevo.';
  end if;
end $$;

-- ---------------------------------------------------------------------
-- 1. TABLAS DE GRUPOS
-- ---------------------------------------------------------------------

create table dim_grupo (
  grupo_id          bigint generated always as identity primary key,
  nombre            text not null check (length(trim(nombre)) between 1 and 40),
  color_hex         text not null default '#4C78A8' check (color_hex ~ '^#[0-9A-Fa-f]{6}$'),
  lider_persona_id  bigint not null references dim_persona(persona_id),
  creado_en         timestamptz not null default now()
);

create table grupo_miembro (
  grupo_id    bigint not null references dim_grupo(grupo_id)     on delete cascade,
  persona_id  bigint not null references dim_persona(persona_id) on delete cascade,
  fecha_alta  date   not null default current_date,
  primary key (grupo_id, persona_id)
);
create index on grupo_miembro (persona_id);

-- Límites: máximo 5 personas por grupo y 5 grupos por persona
create function public.validar_limites_grupo()
returns trigger
language plpgsql
security definer
set search_path = public
as $$
begin
  if (select count(*) from grupo_miembro where grupo_id = new.grupo_id) >= 5 then
    raise exception 'El grupo ya tiene el máximo de 5 personas.';
  end if;
  if (select count(*) from grupo_miembro where persona_id = new.persona_id) >= 5 then
    raise exception 'Esa persona ya pertenece a 5 grupos, que es el máximo.';
  end if;
  return new;
end;
$$;

create trigger trg_limites_grupo
  before insert on grupo_miembro
  for each row execute function public.validar_limites_grupo();

-- ---------------------------------------------------------------------
-- 2. FUNCIONES AUXILIARES (las usan las políticas de seguridad)
-- ---------------------------------------------------------------------

create function public.es_miembro(p_grupo bigint)
returns boolean language sql stable security definer set search_path = public as $$
  select exists (
    select 1 from grupo_miembro gm
    join dim_persona p on p.persona_id = gm.persona_id
    where gm.grupo_id = p_grupo and p.user_id = auth.uid()
  );
$$;

create function public.es_lider(p_grupo bigint)
returns boolean language sql stable security definer set search_path = public as $$
  select exists (
    select 1 from dim_grupo g
    join dim_persona p on p.persona_id = g.lider_persona_id
    where g.grupo_id = p_grupo and p.user_id = auth.uid()
  );
$$;

create function public.comparte_grupo(p_persona bigint)
returns boolean language sql stable security definer set search_path = public as $$
  select exists (
    select 1
    from grupo_miembro a
    join grupo_miembro b on b.grupo_id = a.grupo_id
    join dim_persona yo  on yo.persona_id = a.persona_id
    where yo.user_id = auth.uid() and b.persona_id = p_persona
  );
$$;

grant execute on function public.es_miembro(bigint), public.es_lider(bigint),
                          public.comparte_grupo(bigint) to authenticated;

-- ---------------------------------------------------------------------
-- 3. ACCIONES DE GRUPO (la app las llama; validan quién puede hacer qué)
-- ---------------------------------------------------------------------

create function public.crear_grupo(p_nombre text, p_color text default '#4C78A8')
returns bigint
language plpgsql security definer set search_path = public as $$
declare
  v_persona bigint := public.mi_persona_id();
  v_id bigint;
begin
  if v_persona is null then
    raise exception 'Tu usuario no tiene perfil.';
  end if;
  if (select count(*) from grupo_miembro where persona_id = v_persona) >= 5 then
    raise exception 'Ya perteneces a 5 grupos, que es el máximo.';
  end if;
  insert into dim_grupo (nombre, color_hex, lider_persona_id)
  values (trim(p_nombre), p_color, v_persona)
  returning grupo_id into v_id;
  insert into grupo_miembro (grupo_id, persona_id) values (v_id, v_persona);
  return v_id;
end;
$$;

create function public.agregar_miembro_por_correo(p_grupo bigint, p_correo text)
returns void
language plpgsql security definer set search_path = public as $$
declare
  v_user uuid;
  v_persona bigint;
begin
  if not public.es_lider(p_grupo) then
    raise exception 'Solo el líder del grupo puede agregar personas.';
  end if;
  select id into v_user from auth.users where lower(email) = lower(trim(p_correo));
  if v_user is null then
    raise exception 'No hay ninguna cuenta con ese correo. La persona debe crear su cuenta primero.';
  end if;
  select persona_id into v_persona from dim_persona where user_id = v_user;
  if v_persona is null then
    raise exception 'Esa cuenta no tiene perfil.';
  end if;
  if exists (select 1 from grupo_miembro where grupo_id = p_grupo and persona_id = v_persona) then
    raise exception 'Esa persona ya está en el grupo.';
  end if;
  insert into grupo_miembro (grupo_id, persona_id) values (p_grupo, v_persona);
end;
$$;

create function public.quitar_miembro(p_grupo bigint, p_persona bigint)
returns void
language plpgsql security definer set search_path = public as $$
begin
  if not public.es_lider(p_grupo) then
    raise exception 'Solo el líder del grupo puede quitar personas.';
  end if;
  if exists (select 1 from dim_grupo where grupo_id = p_grupo and lider_persona_id = p_persona) then
    raise exception 'El líder no puede quitarse a sí mismo. Traspasa el liderazgo o elimina el grupo.';
  end if;
  delete from grupo_miembro where grupo_id = p_grupo and persona_id = p_persona;
end;
$$;

create function public.salir_del_grupo(p_grupo bigint)
returns void
language plpgsql security definer set search_path = public as $$
declare v_persona bigint := public.mi_persona_id();
begin
  if public.es_lider(p_grupo) then
    raise exception 'El líder no puede salir. Traspasa el liderazgo o elimina el grupo.';
  end if;
  delete from grupo_miembro where grupo_id = p_grupo and persona_id = v_persona;
end;
$$;

create function public.traspasar_liderazgo(p_grupo bigint, p_persona bigint)
returns void
language plpgsql security definer set search_path = public as $$
begin
  if not public.es_lider(p_grupo) then
    raise exception 'Solo el líder del grupo puede traspasar el liderazgo.';
  end if;
  if not exists (select 1 from grupo_miembro where grupo_id = p_grupo and persona_id = p_persona) then
    raise exception 'Esa persona no pertenece al grupo.';
  end if;
  update dim_grupo set lider_persona_id = p_persona where grupo_id = p_grupo;
end;
$$;

create function public.eliminar_grupo(p_grupo bigint)
returns void
language plpgsql security definer set search_path = public as $$
begin
  if not public.es_lider(p_grupo) then
    raise exception 'Solo el líder del grupo puede eliminarlo.';
  end if;
  delete from dim_grupo where grupo_id = p_grupo;   -- borra miembros y valoraciones del grupo
end;
$$;

grant execute on function
  public.crear_grupo(text, text),
  public.agregar_miembro_por_correo(bigint, text),
  public.quitar_miembro(bigint, bigint),
  public.salir_del_grupo(bigint),
  public.traspasar_liderazgo(bigint, bigint),
  public.eliminar_grupo(bigint)
to authenticated;

-- ---------------------------------------------------------------------
-- 4. VALORACIONES POR GRUPO
-- ---------------------------------------------------------------------

alter table fact_valoracion
  add column grupo_id bigint references dim_grupo(grupo_id) on delete cascade;

-- Grupo inicial con los datos actuales. El líder es la persona más antigua
-- (normalmente tú); se puede traspasar el liderazgo después desde la app.
do $$
declare
  v_lider bigint;
  v_grupo bigint;
begin
  select min(persona_id) into v_lider from dim_persona;
  if v_lider is not null then
    insert into dim_grupo (nombre, lider_persona_id)
    values ('Nosotros', v_lider)
    returning grupo_id into v_grupo;

    insert into grupo_miembro (grupo_id, persona_id)
    select v_grupo, persona_id from dim_persona order by persona_id limit 5;

    update fact_valoracion set grupo_id = v_grupo where grupo_id is null;
  end if;
end $$;

alter table fact_valoracion alter column grupo_id set not null;

alter table fact_valoracion
  drop constraint if exists fact_valoracion_restaurante_id_fecha_id_persona_id_key;
alter table fact_valoracion
  add constraint fact_valoracion_unica unique (grupo_id, restaurante_id, fecha_id, persona_id);
create index on fact_valoracion (grupo_id);

-- ---------------------------------------------------------------------
-- 5. RESTAURANTES: catálogo compartido, edita solo quien lo creó
-- ---------------------------------------------------------------------

alter table dim_restaurante add column creado_por bigint references dim_persona(persona_id);

update dim_restaurante r
set creado_por = coalesce(
  (select f.persona_id from fact_valoracion f
   where f.restaurante_id = r.restaurante_id order by f.creado_en limit 1),
  (select min(persona_id) from dim_persona)
);

alter table dim_restaurante alter column creado_por set default public.mi_persona_id();

-- ---------------------------------------------------------------------
-- 6. SEGURIDAD (RLS)
-- ---------------------------------------------------------------------

alter table dim_grupo     enable row level security;
alter table grupo_miembro enable row level security;

grant select on dim_grupo, grupo_miembro to authenticated;
grant update (nombre, color_hex) on dim_grupo to authenticated;

create policy "ver mis grupos" on dim_grupo
  for select to authenticated using (public.es_miembro(grupo_id));
create policy "el lider edita su grupo" on dim_grupo
  for update to authenticated
  using (public.es_lider(grupo_id)) with check (public.es_lider(grupo_id));

create policy "ver miembros de mis grupos" on grupo_miembro
  for select to authenticated using (public.es_miembro(grupo_id));

-- Personas: me veo a mí y a quienes comparten algún grupo conmigo
drop policy if exists "leer personas" on dim_persona;
create policy "ver personas de mis grupos" on dim_persona
  for select to authenticated
  using (persona_id = public.mi_persona_id() or public.comparte_grupo(persona_id));

-- Restaurantes: todos leen y crean; solo el creador edita
drop policy if exists "crear restaurantes"  on dim_restaurante;
drop policy if exists "editar restaurantes" on dim_restaurante;
create policy "crear restaurantes" on dim_restaurante
  for insert to authenticated with check (creado_por = public.mi_persona_id());
create policy "editar mis restaurantes" on dim_restaurante
  for update to authenticated
  using (creado_por = public.mi_persona_id())
  with check (creado_por = public.mi_persona_id());

-- Valoraciones: las ve todo el grupo; cada uno escribe solo las suyas
drop policy if exists "leer valoraciones"        on fact_valoracion;
drop policy if exists "crear mis valoraciones"   on fact_valoracion;
drop policy if exists "editar mis valoraciones"  on fact_valoracion;
drop policy if exists "borrar mis valoraciones"  on fact_valoracion;

create policy "ver valoraciones de mis grupos" on fact_valoracion
  for select to authenticated using (public.es_miembro(grupo_id));
create policy "crear mis valoraciones" on fact_valoracion
  for insert to authenticated
  with check (persona_id = public.mi_persona_id() and public.es_miembro(grupo_id));
create policy "editar mis valoraciones" on fact_valoracion
  for update to authenticated
  using (persona_id = public.mi_persona_id() and public.es_miembro(grupo_id))
  with check (persona_id = public.mi_persona_id() and public.es_miembro(grupo_id));
create policy "borrar mis valoraciones" on fact_valoracion
  for delete to authenticated
  using (persona_id = public.mi_persona_id() and public.es_miembro(grupo_id));

-- ---------------------------------------------------------------------
-- 7. FOTOS DE PERFIL (Storage)
--    Bucket público de lectura: cualquiera con el enlace exacto ve la foto.
--    Solo cada usuario puede subir o cambiar archivos dentro de su propia carpeta.
-- ---------------------------------------------------------------------

insert into storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
values ('avatares', 'avatares', true, 2097152, array['image/jpeg', 'image/png', 'image/webp'])
on conflict (id) do update
  set public = true, file_size_limit = 2097152,
      allowed_mime_types = array['image/jpeg', 'image/png', 'image/webp'];

create policy "avatares: ver la propia carpeta" on storage.objects
  for select to authenticated
  using (bucket_id = 'avatares' and (storage.foldername(name))[1] = auth.uid()::text);
create policy "avatares: subir en la propia carpeta" on storage.objects
  for insert to authenticated
  with check (bucket_id = 'avatares' and (storage.foldername(name))[1] = auth.uid()::text);
create policy "avatares: cambiar en la propia carpeta" on storage.objects
  for update to authenticated
  using (bucket_id = 'avatares' and (storage.foldername(name))[1] = auth.uid()::text)
  with check (bucket_id = 'avatares' and (storage.foldername(name))[1] = auth.uid()::text);
