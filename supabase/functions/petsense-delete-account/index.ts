import {deleteAccountHandler} from './handler.mjs';
// Exact deployed origin(s), set by the operator after the Vercel URL is known.
const origins=(Deno.env.get('PETSENSE_ALLOWED_ORIGINS')||'').split(',').map(x=>x.trim()).filter(Boolean);
Deno.serve(deleteAccountHandler({url:Deno.env.get('SUPABASE_URL'),anonKey:Deno.env.get('SUPABASE_ANON_KEY'),serviceKey:Deno.env.get('SUPABASE_SERVICE_ROLE_KEY'),origins}));
