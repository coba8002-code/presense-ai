import {defineConfig} from 'vite';
import {cp,mkdir,readFile,writeFile} from 'node:fs/promises';
import {fileURLToPath} from 'node:url';
export default defineConfig({plugins:[{name:'existing-local-video-review',async closeBundle(){
 const source=fileURLToPath(new URL('../backend/static/video/',import.meta.url));
 const target=fileURLToPath(new URL('./dist/video-review/',import.meta.url));
 await mkdir(target,{recursive:true});await cp(source,target,{recursive:true});
 const html=await readFile(target+'index.html','utf8');await writeFile(target+'index.html',html.replace('href="/app"','href="/"').replace('href="/understand?lang=ko"','href="/#observe"'));
}}]});
