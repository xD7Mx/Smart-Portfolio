const {chromium}=await import(`${process.env.NODE_PATH.split(":")[0]}/playwright/index.mjs`);
const TOK=process.env.SP_TOKEN||"";
const BASE=process.env.SP_URL||"http://127.0.0.1:8098";
const b=await chromium.launch({executablePath:process.env.CHROME_BIN||"/opt/pw-browsers/chromium",args:["--no-sandbox","--no-proxy-server"]});
const PAGES=["/portfolio","/market","/governance","/reports","/calculators","/ai","/library","/notifications","/settings","/chart"];
let bad=0;
for(const th of ["light","dark"]){
  const ctx=await b.newContext({viewport:{width:1280,height:1000}});
  await ctx.addInitScript(t=>localStorage.setItem("sp_token",t),TOK);
  const p=await ctx.newPage();
  for(const path of PAGES){
    await p.goto(BASE+path,{waitUntil:"domcontentloaded"});
    await p.waitForTimeout(1800);
    await p.evaluate(t=>{const r=document.documentElement;
      r.classList.toggle("light",t==="light");r.classList.toggle("dark",t==="dark");},th);
    await p.waitForTimeout(2600);
    const hits=await p.evaluate(()=>{
      const lin=c=>{c/=255;return c<=.03928?c/12.92:Math.pow((c+.055)/1.055,2.4);};
      const L=([r,g,b])=>.2126*lin(r)+.7152*lin(g)+.0722*lin(b);
      const CR=(a,b)=>{const x=L(a),y=L(b);return (Math.max(x,y)+.05)/(Math.min(x,y)+.05);};
      const parse=s=>{const m=String(s).match(/[\d.]+/g);return m?m.slice(0,3).map(Number):null;};
      /* ══ الأرضية تُركَّب لا تُقرأ ══
         سقط هذا المسح مرّتين قبل أن يصدق:
           • عمي عن التدرّجات، فأبلغ عن ٣٥ نصّاً «مختفياً» كلُّها أبيضُ
             على تدرّجٍ بنفسجيّ سليم.
           • ثمّ أهمل الشفافية، فقرأ `rgba(59,130,246,.15)` أرضيةً زرقاء
             مصمتة تحت نصٍّ أزرق — أي ١٫٠٠:١ لشارةٍ صحيحة تماماً.
         فالأرضية الآن تُركَّب من الجذر نزولاً: كل طبقةٍ تُمزج بما تحتها
         بنسبة شفافيتها، والتدرّج يُؤخذ بأسوأ محطّاته. */
      const layers=e=>{const st=[];let n=e;
        while(n){const g=getComputedStyle(n);
          if(g.backgroundImage&&g.backgroundImage!=="none"){
            const s2=[];
            for(const m of String(g.backgroundImage).matchAll(/rgba?\(([^)]+)\)/g)){
              const v=m[1].split(",").map(Number);
              if(v.length>=3) s2.push({rgb:v.slice(0,3), a:v.length>3?v[3]:1});}
            if(s2.length) st.push(s2);
          }
          const c=String(g.backgroundColor||"");
          const v=(c.match(/[\d.]+/g)||[]).map(Number);
          if(v.length>=3){const al=v.length>3?v[3]:1; if(al>0) st.push([{rgb:v.slice(0,3), a:al}]);}
          n=n.parentElement;}
        return st;};
      const over=(fg,a,bg)=>fg.map((f,i)=>f*a+bg[i]*(1-a));
      const bgOf=e=>{
        const st=layers(e);
        const root=/dark/.test(document.documentElement.className)?[15,15,15]:[255,255,255];
        // أسوأ الحالات: تُجرَّب كل محطّةٍ في الطبقة العليا فوق ما تحتها
        let base=root;
        for(let i=st.length-1;i>=1;i--) base=over(st[i][0].rgb, st[i][0].a, base);
        return st.length?st[0].map(x=>over(x.rgb,x.a,base)):[base];
      };
      const out=[];
      for(const e of document.querySelectorAll("*")){
        if(e.children.length) continue;
        const t=(e.textContent||"").trim(); if(!t||t.length>60) continue;
        const g=getComputedStyle(e);
        if(g.visibility==="hidden"||g.display==="none"||parseFloat(g.opacity)<.15) continue;
        const r=e.getBoundingClientRect(); if(r.width<4||r.height<4) continue;
        const fg=parse(g.color); if(!fg) continue;
        const alpha=parseFloat((String(g.color).match(/[\d.]+/g)||[])[3] ?? "1");
        if(alpha<.15){ out.push([t.slice(0,28),"شفافيةٌ شبه تامّة"]); continue; }
        const c=Math.min(...bgOf(e).map(bg=>CR(fg,bg)));
        if(c<2) out.push([t.slice(0,28), c.toFixed(2)+":1"]);
      }
      return out.slice(0,6);
    });
    if(hits.length){ bad+=hits.length;
      console.log(`✖ ${th}${path}`); for(const [t,c] of hits) console.log(`     «${t}» — ${c}`); }
  }
  await ctx.close();
}
console.log(bad?`\n✖ B-FADED — ${bad} نصّاً شبه مختفٍ`:"✔ B-FADED          نظيف");
await b.close();
process.exit(bad?1:0);
