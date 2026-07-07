import 'dotenv/config';
import express from 'express'; import { rateLimit } from 'express-rate-limit'; import cors from 'cors'; import helmet from 'helmet'; import compression from 'compression'; import morgan from 'morgan'; import { createProxyMiddleware } from 'http-proxy-middleware';
const app=express(); const port=Number(process.env.PORT||3000); const target=process.env.ML_API_URL||'http://127.0.0.1:8000';
app.use(helmet({crossOriginResourcePolicy:false})); app.use(cors({origin:true,credentials:true})); app.use(compression()); app.use(morgan('tiny'));
app.use('/api', rateLimit({windowMs:60_000, limit:Number(process.env.RATE_LIMIT_PER_MINUTE||120), standardHeaders:'draft-7', legacyHeaders:false}));
app.get('/gateway/health',(_,res)=>res.json({status:'ok',service:'finguard-gateway',ml_core:target}));
app.use('/api',createProxyMiddleware({target,changeOrigin:true,pathRewrite:{'^/api':''},proxyTimeout:120000}));
app.listen(port,()=>console.log(`FinGuard gateway http://localhost:${port} -> ${target}`));
