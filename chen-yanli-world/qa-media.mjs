import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {SoundEngine,EFFECTS} from './dist/sound.js';
class Media{
 constructor(src){this.src=src;this.paused=true;this.ended=false;this.plays=0;this.pauses=0;this.reject=false;}
 setAttribute(){}load(){this.loaded=true;}
 pause(){this.paused=true;this.pauses++;}
 play(){this.plays++;this.paused=false;return this.reject?Promise.reject(Error('blocked')):Promise.resolve();}
}
const session={type:'ambient'},host={Audio:Media,navigator:{audioSession:session},performance:{now:()=>1000}};
const a=new SoundEngine(host);a.prewarm();assert(a.pools.size===25);assert(a.tracks.every(t=>t.loaded&&t.loop));
await a.unlock();assert(a.ready);assert.equal(session.type,'playback');assert(a.tracks[0].plays===1);
a.setScene('play',1);assert(a.tracks[0].paused);assert(a.tracks[1].plays===1);
const pool=a.pools.get('coin'),src=pool[0].src;a.play('coin');assert.equal(pool[0].src,src);assert.equal(pool[0].plays,1);
a.recent.clear();a.play('coin');assert.equal(pool[1].plays,1);assert(!pool[0].paused&&!pool[1].paused);
a.setMusicEnabled(false);assert(a.tracks[1].paused);a.play('jump');assert(a.pools.get('jump')[0].plays===1);
a.setMusicEnabled(true);assert(a.tracks[1].plays===2);a.setScene('paused',1);assert(a.tracks[1].paused);
a.setEnabled(false);assert([...a.pools.values()].every(pool=>pool.every(e=>e.paused)));
await a.test();assert(a.enabled);assert(a.pools.get('test')[0].plays===1);
a.pools.get('magic')[0].reject=true;a.play('magic');await Promise.resolve();assert(a.lastError.includes('阻止'));
for(const name of [...Object.keys(EFFECTS),'bg0','bg1','bg2']){
 const wav=readFileSync(`dist/audio/${name}.wav`);assert.equal(wav.toString('ascii',0,4),'RIFF');assert.equal(wav.readUInt32LE(40),wav.length-44);
 let peak=0;for(let i=44;i<wav.length;i+=2)peak=Math.max(peak,Math.abs(wav.readInt16LE(i)));assert(peak>12000&&peak<24000);
 if(name.startsWith('bg'))assert(wav.length>500000);
}
console.log('PASS: preloaded fixed-source compatibility pools, simultaneous voices, 3 music tracks, mute/pause, feedback and PCM WAV assets.');
