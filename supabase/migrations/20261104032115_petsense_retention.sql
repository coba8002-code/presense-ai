-- Apply only to the dedicated PetSense project. Auth accounts are retained until
-- account deletion; profile/observation/request/plan rows expire independently.
create extension if not exists pg_cron;
select cron.schedule('petsense-expired-records','17 * * * *',$job$
  delete from public.ps_notes where expires_at <= now();
  delete from public.ps_requests where expires_at <= now();
  delete from public.ps_plans where expires_at <= now();
  delete from public.ps_dogs where expires_at <= now();
$job$);
