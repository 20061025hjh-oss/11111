export const EFFECTS = {
 click:[[0,620,.045,'triangle',.25,820]],
 start:[[0,392,.10,'triangle',.28],[.10,523,.10,'triangle',.28],[.20,784,.16,'triangle',.25]],
 jump:[[0,220,.13,'triangle',.32,640],[0,110,.09,'sine',.17,300]],
 doubleJump:[[0,380,.16,'triangle',.3,950],[.045,760,.09,'sine',.13,1320]],
 coin:[[0,988,.065,'triangle',.24],[0,1976,.035,'sine',.10],[.055,1480,.13,'sine',.22],[.09,2960,.10,'sine',.07]],
 magic:[[0,850,.13,'triangle',.24,170],[0,1420,.055,'sine',.13,720],[0,1600,.08,'noise',.12,350]],
 stomp:[[0,150,.09,'sine',.3,55],[0,400,.045,'noise',.18],[.035,360,.10,'triangle',.21,640]],
 hit:[[0,210,.07,'square',.17,85],[0,1600,.07,'noise',.16]],
 defeat:[[0,330,.065,'triangle',.25],[.065,494,.075,'triangle',.22],[.14,659,.10,'triangle',.18]],
 hurt:[[0,185,.14,'sawtooth',.11,62],[.03,97,.18,'triangle',.20,48]],
 fall:[[0,440,.30,'triangle',.24,75]],
 block:[[0,440,.045,'square',.13],[.055,880,.09,'triangle',.23]],
 heal:[[0,523,.09,'sine',.28],[.09,659,.09,'sine',.28],[.18,784,.16,'sine',.25]],
 power:[[0,523,.08,'triangle',.24],[.07,784,.08,'triangle',.22],[.14,1047,.08,'triangle',.21],[.21,1568,.18,'sine',.19]],
 checkpoint:[[0,392,.10,'triangle',.24],[.10,494,.10,'triangle',.24],[.20,587,.10,'triangle',.23],[.30,784,.19,'sine',.24]],
 place:[[0,170,.055,'triangle',.25,90],[.025,450,.045,'sine',.12]],
 recover:[[0,480,.07,'triangle',.23,800]],
 clear:[[0,523,.13,'triangle',.24],[.13,659,.13,'triangle',.24],[.26,784,.13,'triangle',.24],[.39,1047,.28,'triangle',.22]],
 win:[[0,523,.11,'triangle',.25],[.12,659,.11,'triangle',.25],[.24,784,.11,'triangle',.24],[.36,1047,.16,'triangle',.23],[.53,784,.13,'triangle',.21],[.67,1047,.35,'triangle',.24],[.67,1319,.35,'sine',.13]],
 gameover:[[0,392,.16,'triangle',.24],[.18,330,.16,'triangle',.24],[.36,262,.16,'triangle',.23],[.54,196,.35,'triangle',.23]],
 test:[[0,523,.22,'triangle',.3],[.3,659,.22,'triangle',.3],[.6,784,.4,'triangle',.3]],
 step:[[0,160,.035,'noise',.13],[0,95,.045,'sine',.18,65]],
 land:[[0,130,.08,'sine',.27,55],[0,350,.05,'noise',.11]],
 boss:[[0,90,.3,'sawtooth',.15,45],[0,65,.38,'sine',.27],[.11,260,.16,'noise',.18]],
 bossDefeat:[[0,100,.28,'noise',.24],[0,90,.35,'sine',.25,35],[.15,392,.13,'triangle',.24],[.28,523,.14,'triangle',.23],[.42,784,.3,'sine',.23]]
};

const midi=n=>440*2**((n-69)/12);
// 三首原创 8 小节像素配乐：旋律、和弦分解、低音、鼓与沙锤。
export const MUSIC_NAMES=['风铃草原 · 晨光出发','暮色矿谷 · 萤石回响','星光城堡 · 勇气之门'];
export function musicScore(index){
 const bpm=[132,112,142][index],beat=60/bpm,duration=beat*32,notes=[];
 const melodies=[
 [[76,79,81,79,76,74,72,74],[77,81,84,81,79,77,76,74],[74,77,79,81,79,77,74,71],[72,76,79,84,83,79,76,72]],
 [[76,79,83,79,78,76,74,71],[72,76,79,83,81,79,76,74],[74,78,81,78,76,74,71,69],[71,74,78,83,81,78,76,71]],
 [[81,84,88,84,83,81,79,76],[77,81,84,88,86,84,81,79],[79,83,86,83,81,79,76,74],[76,80,83,88,86,83,80,76]]
 ][index];
 const roots=[[48,53,55,48],[52,48,50,47],[45,41,43,40]][index];
 for(let bar=0;bar<8;bar++){
  const t=bar*4*beat,root=roots[bar%4],minor=index>0&&bar%4===0;
  for(let step=0;step<8;step++){
   const time=t+step*beat/2,pitch=melodies[bar%4][step]+(bar>=4&&step===6?12:0);
   notes.push([time,midi(pitch),beat*.42,'triangle',.21]);
   notes.push([time,midi(root+12+[0,minor?3:4,7,12][step%4]),beat*.38,'sine',.08]);
   notes.push([time,6500,beat*.12,'noise',step%2?.024:.038]);
  }
  for(let b=0;b<4;b++){
   notes.push([t+b*beat,midi(root+(b%2?7:0)),beat*.75,'triangle',.17]);
   if(b%2===0)notes.push([t+b*beat,115,.16,'sine',.25,42]);
   else notes.push([t+b*beat,1800,.10,'noise',.12],[t+b*beat,180,.065,'triangle',.08,85]);
  }
 }
 return {notes,duration};
}
export const SAMPLE_RATE=22050;
export function renderPCM(notes,duration=null,loop=false){
 duration??=Math.max(...notes.map(([delay,,length])=>delay+length))+.12;
 const out=new Float32Array(Math.ceil(duration*SAMPLE_RATE));let seed=7919;
 for(const [delay,frequency,length,type,volume,end=frequency] of notes){
  let phase=0,noiseLow=0;
  for(let i=0;i<Math.ceil(length*SAMPLE_RATE);i++){
   const t=i/SAMPLE_RATE,progress=t/length;phase+=frequency*Math.pow(end/frequency,progress)/SAMPLE_RATE;
   const p=phase%1;if(type==='noise'){seed=(Math.imul(seed,1664525)+1013904223)>>>0;const noise=seed/2147483648-1;noiseLow+=Math.min(.9,frequency/SAMPLE_RATE*4)*(noise-noiseLow);}
   const wave=type==='noise'?noiseLow:type==='square'?(p<.5?1:-1):type==='sawtooth'?2*p-1:type==='triangle'?1-4*Math.abs(p-.5):Math.sin(phase*2*Math.PI);
   const envelope=Math.min(1,(i+1)/(SAMPLE_RATE*.002))*Math.max(0,1-progress)**1.7;
   const pos=Math.round(delay*SAMPLE_RATE)+i;if(pos<out.length)out[pos]+=wave*volume*envelope;
  }
 }
 if(!loop){ // 很轻的短回声，为奖励和魔法增添空间感。
  const offset=Math.round(SAMPLE_RATE*.043);for(let i=out.length-1;i>=offset;i--)out[i]+=out[i-offset]*.14;
 }
 let peak=.001;for(const value of out)peak=Math.max(peak,Math.abs(value));
 const scale=(loop?.53:.64)/peak;
 for(let i=0;i<out.length;i++)out[i]=Math.tanh(out[i]*scale);
 out[0]=0;out[out.length-1]=0;
 return out;
}
