import {mkdirSync,writeFileSync} from 'node:fs';
import {EFFECTS,SAMPLE_RATE,renderPCM,musicScore} from './dist/audio-data.js';
const rate=SAMPLE_RATE;mkdirSync('dist/audio',{recursive:true});
function wav(name,samples){
 const data=Buffer.alloc(44+samples.length*2);data.write('RIFF',0);data.writeUInt32LE(data.length-8,4);data.write('WAVE',8);data.write('fmt ',12);data.writeUInt32LE(16,16);data.writeUInt16LE(1,20);data.writeUInt16LE(1,22);data.writeUInt32LE(rate,24);data.writeUInt32LE(rate*2,28);data.writeUInt16LE(2,32);data.writeUInt16LE(16,34);data.write('data',36);data.writeUInt32LE(samples.length*2,40);
 for(let i=0;i<samples.length;i++)data.writeInt16LE(Math.round(Math.max(-1,Math.min(1,samples[i]))*32767),44+i*2);
 writeFileSync(`dist/audio/${name}.wav`,data);
}
for(const [name,notes] of Object.entries(EFFECTS))wav(name,renderPCM(notes));
for(let i=0;i<3;i++){const s=musicScore(i);wav(`bg${i}`,renderPCM(s.notes,s.duration,true));}
wav('silence',new Float32Array(Math.ceil(.06*rate)));
console.log(`Generated ${Object.keys(EFFECTS).length} layered effects and 3 original background loops.`);
