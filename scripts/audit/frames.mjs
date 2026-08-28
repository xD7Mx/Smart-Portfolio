const {chromium}=await import(`${process.env.NODE_PATH.split(":")[0]}/playwright/index.mjs`);
const TOK=process.env.SP_TOKEN||"";
const BASE=process.env.SP_URL||"http://127.0.0.1:8098";
const b=await chromium.launch({executablePath:process.env.CHROME_BIN||"/opt/pw-browsers/chromium",args:["--no-sandbox","--no-proxy-server"]});
const PAGES=["/portfolio","/market","/governance","/reports","/calculators","/ai","/library","/notifications","/settings","/chart","/portfolio/1"];
const found=[];
for(const th of ["light","dark"]){
  const ctx=await b.newContext({viewport:{width:1280,height:900}});
  await ctx.addInitScript(t=>localStorage.setItem("sp_token",t),TOK);
  const p=await ctx.newPage();
  for(const path of PAGES){
    await p.goto(BASE+path,{waitUntil:"domcontentloaded"}).catch(()=>{});
    await p.waitForTimeout(1600);
    await p.evaluate(t=>{const r=document.documentElement;r.classList.toggle("light",t==="light");r.classList.toggle("dark",t==="dark");},th);
    await p.waitForTimeout(2400);
    const hits=await p.evaluate(()=>{
      const out=[];
      const label=e=>(e.textContent||"").trim().slice(0,22)||("."+String(e.className).split(" ")[0]);
      for(const e of document.querySelectorAll("button, a[role=button], .card, .panel, input, .seg-btn, [role=tab]")){
        const g=getComputedStyle(e), r=e.getBoundingClientRect();
        if(r.width<8||r.height<8) continue;
        const w=["Top","Right","Bottom","Left"].map(s=>parseFloat(g["border"+s+"Width"])||0);
        const c=["Top","Right","Bottom","Left"].map(s=>g["border"+s+"Color"]);
        const has=w.filter(x=>x>0).length;
        // ① إطارٌ ناقص الأضلاع: بعضها له عرض وبعضها صفر (تشوّهٌ ظاهر)
        if(has>1 && has<4) out.push([label(e),"أضلاعٌ ناقصة "+w.join("/")]);
        // ② أضلاعٌ بألوانٍ مختلفة على العنصر الواحد
        else if(has===4 && new Set(c).size>2) out.push([label(e),"ثلاثةُ ألوانٍ فأكثر لأضلاع عنصرٍ واحد"]);
        // ③ إطارٌ له عرض ولونه شفّاف تماماً ⇒ فراغٌ يزيح التخطيط بلا أن يُرى
        else if(has===4 && c.every(x=>/rgba\(0, 0, 0, 0\)|transparent/.test(x)))
          out.push([label(e),"إطارٌ شفّاف يشغل مساحة "+w[0]+"px"]);
      }
      // ④ حلقةٌ متدرّجة غير مستوية — العطب الحقيقيّ وحده.
      //    البصمة الدقيقة: غلافٌ **خلفيتُه تدرّج** بحشوةٍ رفيعة، وابنٌ
      //    خلفيتُه مصمتة يغطّيه فلا يبقى من التدرّج إلا حلقة. وشرط استواء
      //    الحلقة: استدارةُ الابن = استدارةُ الغلاف − الحشوة.
      //    ولا يُوسَم شريطُ تبويبٍ مجزّأ ولا حبّةٌ تحوي وسماً: كلاهما طبقتان
      //    بلا حلقةٍ أصلاً، ووسمُهما ضجيجٌ يُخفي الحقيقيّ (وقع فعلاً: أوّل
      //    صياغةٍ لهذا المعيار أطلقت ٣٢ إنذاراً أكثرها على شيفرةٍ سليمة).
      for(const wrap of document.querySelectorAll("button, a, div")){
        const gw=getComputedStyle(wrap);
        if(!/gradient/.test(gw.backgroundImage||"")) continue;
        const pad=parseFloat(gw.paddingTop)||0;
        if(pad<=0||pad>4) continue;
        const kid=wrap.firstElementChild;
        if(!kid) continue;
        const gk=getComputedStyle(kid);
        const opaque=gk.backgroundColor && !/rgba\(0, 0, 0, 0\)|transparent/.test(gk.backgroundColor);
        if(!opaque) continue;
        const R=parseFloat(gw.borderTopLeftRadius)||0;
        const r=parseFloat(gk.borderTopLeftRadius)||0;
        if(R<6) continue;
        if(Math.abs(r-(R-pad))>0.8)
          out.push([label(wrap),`حلقةٌ غير مستوية: الخارج ${R} − حشوة ${pad} ⇒ ${R-pad} والداخل ${r}`]);
      }
      return out.slice(0,6);
    }).catch(()=>[]);
    for(const [t,why] of hits) found.push(`${th}${path} · «${t}» — ${why}`);
  }
  await ctx.close();
}
const uniq=[...new Set(found)];
console.log(uniq.length?`✖ B-FRAMES — ${uniq.length} إطاراً مشوّهاً:`:"✔ B-FRAMES         نظيف");
uniq.slice(0,25).forEach(x=>console.log("   "+x));
await b.close();
process.exit(uniq.length?1:0);
