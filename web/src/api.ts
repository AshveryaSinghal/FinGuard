const BASE=import.meta.env.VITE_API_URL||'http://localhost:3000/api';
export async function api<T>(path:string,init?:RequestInit):Promise<T>{const r=await fetch(`${BASE}${path}`,{headers:{'Content-Type':'application/json',...(init?.headers||{})},...init});if(!r.ok)throw new Error((await r.json().catch(()=>({detail:r.statusText}))).detail||'Request failed');return r.json()}
