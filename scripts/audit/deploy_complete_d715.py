#!/usr/bin/env python3
"""حارسُ D715 — النشرُ يُكمل الدورة: الواجهةُ تُبنى إن تغيّرت، والشجرةُ تُسوّى تامّةً.

قال المالك: «لم أجد التحديثات على التطبيق». وكانت دورةُ النشر (‏complete.sh) تُعيد الخادمَ وحدَه والواجهةُ مهمّةٌ منفصلة
(‏web)، فنُشرت تعديلاتُ الواجهة على الفرع ولم تُبنَ. وكانت التسويةُ ‎`git checkout FETCH_HEAD -- .`‎ تكتب الملفّاتِ ولا تحذف ما
حُذف من الفرع — فبقيت على الخادم ملفّاتٌ محذوفة (قِيس: ‏investor_calls.py · InvestorCalls.tsx). فالحارسُ يمنع العودة:
  · ‏complete.sh يبني الواجهةَ متى اختلفت بصمةُ شجرتها عن آخر بناء، ومهمّةُ ‏web تحفظ البصمة.
  · والتسويةُ (في النشر وفي سير العمل) تُثبّت المستودعَ على إيداع الفرع وتُزيل ما يقول تاريخُه إنه حُذف — **وحده**:
    يُجرَّب على مستودعٍ مصطنعٍ بحال الخادم: المحذوفُ يُزال، وملفٌّ لا تاريخَ له و‎.env‎ يبقيان.

    python3 scripts/audit/deploy_complete_d715.py
"""
import os, pathlib, re, subprocess, sys, tempfile
ROOT = pathlib.Path(__file__).resolve().parents[2]
fail = 0


def check(ok, label, det=""):
    global fail
    if not ok:
        fail = 1
    print(f"{'PASS' if ok else 'FAIL'} {label}" + (f" — {det}" if det else ""))


comp = (ROOT / "scripts/ops/complete.sh").read_text(encoding="utf-8")
ops = (ROOT / ".github/workflows/ops.yml").read_text(encoding="utf-8")
gi = (ROOT / ".gitignore").read_text(encoding="utf-8")
# ‏D716: والبناءُ لا يكون في دورة النشر (خنق الخادم) — الدورةُ تُعلن أنّ الواجهةَ تغيّرت، ومهمّةُ ‎web‎ تبنيها منفردة
check('git rev-parse FETCH_HEAD:frontend' in comp and '.web_built_tree' in comp and "تُبنى بمهمّة web" in comp
      and comp.index('git rev-parse FETCH_HEAD:frontend') < comp.index('say "٣ · لقطةُ «تداول»"'),
      "١ دورةُ النشر تُعلن أنّ الواجهةَ تغيّرت منذ آخر بناء (لا صمتَ يُخفي أنّها لم تُنشر)، والبناءُ بمهمّة web منفردة (‏D716)")
check("git rev-parse FETCH_HEAD:frontend > .web_built_tree" in ops and "/.web_built_tree" in gi,
      "٢ ومهمّةُ ‏web تحفظ بصمةَ ما بنته، والبصمةُ حالةُ نشرٍ لا تدخل المستودع")
for name, src in (("complete.sh", comp), ("ops.yml", ops)):
    check("checkout -q -f --detach FETCH_HEAD" in src and "--diff-filter=D" in src and "git clean" not in src
          and "reset --hard" not in src,
          f"٣ والتسويةُ في {name} تامّة: تثبيتٌ على إيداع الفرع وإزالةُ ما حُذف بتاريخه وحده — لا ‎git clean‎ ولا ‎reset --hard‎")

# ٤ سلوكاً: مستودعٌ بحال الخادم يُسوّى بمقطع ‏complete.sh نفسِه
m = re.search(r"(?s)(git -c advice\.detachedHead=false checkout -q -f --detach FETCH_HEAD.*?\nfi\n)", comp)
import shutil
if not m:
    check(False, "٤ مقطعُ التسوية موجودٌ في complete.sh")
elif not shutil.which("git"):
    print("… لم يُقَس ٤ (لا git في هذه البيئة — يُقاس على المضيف)")      # ‏D714: صورةُ الخادم بلا ‎git‎
else:
    snippet = m.group(1)
    d = pathlib.Path(tempfile.mkdtemp(prefix="sp-d715-"))
    env = {**os.environ, "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t", "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@t"}
    sh = lambda c: subprocess.run(["bash", "-c", c], cwd=d, env=env, capture_output=True, text=True)   # noqa: E731
    for p in ("frontend/src", "backend/app", "scripts"):
        (d / p).mkdir(parents=True)
    sh("git init -q && printf '.env\\n' > .gitignore")
    (d / "frontend/src/a.tsx").write_text("1"); (d / "frontend/src/x.tsx").write_text("x")
    (d / "backend/app/old.py").write_text("o")
    sh("git add -A && git commit -qm c0")                          # ‏x.tsx · old.py متتبَّعان
    sh("git rm -q frontend/src/x.tsx && git commit -qm c1")        # الخادمُ عند c1 و‎x.tsx‎ باقٍ على قرصه
    c1 = sh("git rev-parse HEAD").stdout.strip()
    (d / "frontend/src/a.tsx").write_text("2")
    sh("git rm -q backend/app/old.py && git add -A && git commit -qm c2")
    c2 = sh("git rev-parse HEAD").stdout.strip()
    sh(f"git checkout -q {c1}")                                    # حالُ الخادم: HEAD قديم
    (d / "frontend/src/x.tsx").write_text("x")                     # محذوفٌ في c1 باقٍ على القرص
    (d / "frontend/src/mine.tsx").write_text("m")                  # ملفٌّ لا تاريخَ له
    (d / ".env").write_text("SECRET=1")
    (d / ".git/FETCH_HEAD").write_text(f"{c2}\t\tbranch 'b' of origin\n")
    r = sh("git checkout FETCH_HEAD -- . && " + snippet)
    left = {p for p in ("frontend/src/x.tsx", "backend/app/old.py", "frontend/src/mine.tsx", ".env", "frontend/src/a.tsx") if (d / p).exists()}
    head = sh("git rev-parse HEAD").stdout.strip()
    check(left == {"frontend/src/mine.tsx", ".env", "frontend/src/a.tsx"} and head == c2
          and (d / "frontend/src/a.tsx").read_text() == "2",
          "٤ وسلوكاً: المحذوفُ من الفرع يُزال (ما حُذف قديماً وما حُذف الآن)، وما لا تاريخَ له و‎.env‎ يبقيان، والمستودعُ عند إيداع الفرع",
          f"باقٍ {sorted(left)} · HEAD {'= الفرع' if head == c2 else head[:8]}")
print("\nالنتيجة:", "نظيف ✔" if not fail else "عطب ✖")
sys.exit(fail)
