# ArniComp-Compiler Inceleme Notlari

Tarih: 2026-02-28
Inceleyen: Codex
Durum: Acik bulgular listesi (duzeltme backlog'u)

## Kapsam
- Repo: `ArniComp-Compiler`
- Referans: `ArniComp-Support-Package` (assembler + emulator + onceki compiler)
- Yontem: statik kod inceleme + secili dinamik calistirma

## Calistirma Notu
- Sistem `python` ile `pycparser` bulunamadi.
- `./venv/Scripts/python.exe` ile test akislari calisti.

## Bulgular (Oncelik Sirasiyla)

### F-001 (Kritik) - Control-flow altinda MAR cache semantik bozuyor
**Etki:** `if/else` gibi dallanmalarda `MAR` state'i gecersiz oldugu halde cache'e guvenildigi icin yanlis adrese yazim olabiliyor.

**Belirti:** `if.c` senaryosunda else kolunda `b` yerine `a` adresine yazim goruldu.

**Kod referanslari:**
- `modules/AssemblyGen.py:91`
- `modules/AssemblyGen.py:99`
- `modules/AssemblyGen.py:139`
- `modules/AssemblyGen.py:150`
- `modules/LIROptimizer.py:4`

**Not:** Branch-aware invalidation yok.

**Durum Guncellemesi (2026-02-28):**
- LIR optimizer'da CFG/basic-block tabanli `SETMAR` eliminasyonu eklendi.
- `AssemblyGen` tarafinda label girislerinde MAR cache invalidation eklendi.
- `if.c` senaryosu emulator ile tekrar dogrulandi (`a=50, b=200`).
- Durum: **Kapali (ilk faz)**. Ileride daha agresif hoisting/scheduling iyilestirmeleri eklenebilir.

---

### F-002 (Kritik) - HIR producer/parser format uyumsuzlugu
**Etki:** Bazi expression turlerinde optimizer parse asamasinda patliyor.

**Belirti:**
- `".t0 = bitnot b"`
- `".t0 = CALL foo()"`

Bu satirlar uretiliyor ama parser desteklemiyor.

**Kod referanslari:**
- `modules/HIRGen.py:148`
- `modules/HIRGen.py:181`
- `entities/HirLine.py:33`

**Durum Guncellemesi (2026-02-28):**
- `UnaryOpHirLine` ve `CallHirLine` eklendi.
- `parse_hir_line` artik `neg/bitnot/not` ve `CALL` formatlarini parse ediyor.
- Temp birlestirme optimizasyonu unary/call satirlarini da kapsayacak sekilde guncellendi.
- Durum: **Kapali** (CALL parse sorunu cozuldu; CALL lowering ayri backlog maddesi).

---

### F-003 (Yuksek) - Negatif literal handling bozuk
**Etki:** `-1` gibi degerler constant algilanmadigi icin `var:-1` gibi gecersiz LIR uretiliyor.

**Kod referanslari:**
- `entities/HirLine.py:51`
- `modules/LIRGen.py:33`

**Durum Guncellemesi (2026-02-28):**
- Signed integer token parse (ornegin `-1`) HIR katmanina eklendi.
- `a = -1` artik constant olarak dogru algilaniyor ve `LDI 255` seklinde uretiliyor.
- Durum: **Kapali**.

---

### F-004 (Yuksek) - LIRGen kismi implementasyon, gercek inputlarda NotImplemented
**Etki:** `tests/define.c` benzeri girislerde compile akisinda duruyor.

**Kod referanslari:**
- `modules/LIRGen.py:63`
- `modules/LIRGen.py:70`

**Durum Guncellemesi (2026-02-28):**
- `ArithmeticOpHirLine` lowering eklendi (`+`, `-`, `&`, `^`).
- `UnaryOpHirLine` lowering eklendi (`bitnot`, `neg`).
- LIR'e `AluOpLirLine` eklendi; Assembly backend `ADD/SUB/AND/XOR/NOT` uretimini destekliyor.
- `tests/define.c` artik pipeline'dan geciyor.
- Cekirdek-uyumlu ek loweringler:
  - `|` operatoru De Morgan ile sentezlendi (`NOT` + `AND` + `NOT`).
  - `!` operatoru `CMP + JEQ + label` akisiyla eklendi.
  - `<<` operatoru sabit kaydirma icin tekrarli doubling (`ADD RD`) ile eklendi.
  - `<<` operatoru degisken kaydirma (`a << b`) icin loop tabanli lowering eklendi.
  - `ConditionalOpHirLine` lowering eklendi:
    - Karsilastirma expressionlari: `<, <=, >, >=, ==, !=`
    - Mantiksal expressionlar: `&&, ||`
- Emulator dogrulamalari:
  - `a=5,b=3 -> a=a|b` sonucu `a=7`.
  - `b=0 -> a=!b` sonucu `a=1`.
  - `b=3 -> a=b<<2` sonucu `a=12`.
- Durum: **Kismen Kapali**.
- Acik kalanlar: `*`, `/`, `%`, `>>`, genel `CALL` lowering/ABI.

---

### F-005 (Orta) - `SymbolTable.add` constructor cagri imzasi hatali
**Etki:** Latent bug; method kullanildiginda yanlis `Symbol(...)` olusumu.

**Kod referanslari:**
- `entities/SymbolTable.py:24`
- `entities/SymbolTable.py:47`

**Durum Guncellemesi (2026-02-28):**
- `SymbolTable.add(...)` imzasi `kind` parametresi ile duzeltildi.
- `Symbol(...)` cagrisi dogru arguman sirasiyla uretiliyor.
- Durum: **Kapali**.

---

### F-006 (Orta) - Register modeli ISA ile tam uyumlu degil
**Etki:** Register-state takibi eksik; `PRL/PRH/ACC/PCL/PCH` gibi register'lar backend davranisinda kullaniliyor ama config modeli minimal.

**Kod referanslari:**
- `modules/Config.py:6`
- `helpers/ArchitectureHelper.py:3`
- `modules/AssemblyGen.py:173`

**Durum Guncellemesi (2026-02-28):**
- `modules/Config.py` register tanimina `ACC/PRL/PRH/PCL/PCH` eklendi.
- `AssemblyGen._ASM_set_pr` artik `PRL` register-state bilgisini de guncelliyor.
- `SETPR` icin iki-gecisli placeholder cozumu eklendi:
  - Label adresi compiler tarafinda cozuluyor.
  - `PRL` yukleme `LDI low7 + (SMSBRA|NOP) + MOV PRL,RA` ile uretiliyor.
  - Boylece `label > 127` durumlarinda assembler `LDI` limitine takilmadan calisiyor.
- Label girislerinde kontrol-akisi kaynakli register-cache invalidation genisletildi
  (`RA/RB/RD/ACC/PR*/PC*/MAR*`), branch-join yanlis cache hit'leri engellendi.
- Durum: **Kismen Kapali** (state tracking tabani guclendi; tam veri-akisi tabanli register-value modellemesi hala acik).

---

### F-007 (Orta) - Optimize edilmis LIR asm uretiminde kullanilmiyor
**Etki:** `optimize_lir` sonucu uretiliyor ama `generate_assembly_code` ham LIR ile cagriliyor.

**Kod referansi:**
- `test.py:53`

**Durum Guncellemesi (2026-02-28):**
- `test.py` asm uretimi artik `optimized_lir_lines` ile yapiliyor.
- Durum: **Kapali**.

---

### F-008 (Orta) - Scope/memory modeli gecici varsayima dayali
**Etki:** `main` icindeki decl'ler global gibi ele aliniyor; cok fonksiyonlu/stack tabanli modele geciste refactor gerekecek.

**Kod referanslari:**
- `modules/SymbolTableGen.py:43`
- `modules/MemoryManager.py:84`

**Durum Guncellemesi (2026-02-28):**
- Fonksiyon ici degiskenler symbol table'da artik `LOCAL` scope olarak isaretleniyor.
- Memory katmani, mevcut stacksiz mimariye uygun sekilde `GLOBAL+LOCAL` degiskenleri statik adrese yerlestiriyor.
- Durum: **Kismen Kapali** (scope semantigi duzeldi; gercek stack/frame modeli henuz yok).

---

### F-009 (Orta) - CALL lowering eksik
**Etki:** CALL parse ediliyor ancak LIR lowering asamasinda `NotImplementedError` veriyor.

**Kod referanslari:**
- `modules/LIRGen.py` (CALL branch)
- `entities/HirLine.py` (`CallHirLine`)

**Durum Guncellemesi (2026-02-28):**
- Basit fonksiyon cagrilari icin compile-time inlining eklendi:
  - Kapsam: no-arg, tek `return <expr>;` fonksiyonlar
  - Uygulama noktasi: `HIRGen` (`FuncCall` olusmadan once expression inlining)
- E2E case: `call_inline_const.c` PASS.
- Durum: **Kismen Kapali** (genel ABI/call stack tabanli lowering hala acik).

---

## E2E Test Turu (2026-02-28)

Yeni eklenen test case dizini:
- `tests/e2e_cases/`

Runner:
- `tests/run_e2e_emulator.py`

Calistirma:
- `.\venv\Scripts\python.exe .\tests\run_e2e_emulator.py`

Sonuc:
- Toplam: 10
- PASS: 8
- FAIL: 2

### F-010 (Yuksek) - `!` lowering sonucunda RA clobber (yanlis sonuc yazimi)
**Etki:** `logical not` sonucunun 0/1 yerine label adresi gibi alakasiz degerler memory'ye yazilabiliyor.
**Durum:** **Kapali** (2026-02-28)

**Gozlem:**
- `unary_ops` case'inde `not1` icin beklenen `0`, emulator sonucu `50`.
- Kiritik sebep: `not` lowering icinde sonuc RA'da varsayiliyor; fakat branch kodunda `SETPR` asm asamasinda `RA` uzerinden yuklenerek sonucu eziyor.

**Kod referanslari:**
- `modules/LIRGen.py` (`_generate_unary_lir`, `not` branch)
- `modules/AssemblyGen.py` (`_ASM_set_pr` RA kullanim sekli)

**Kapanis notu:**
- `not` lowering sonucu RA yerine RB'de tutulacak sekilde guncellendi.
- Boylesiyle `SETPR` kaynakli RA clobber sonuc degerini bozamiyor.
- E2E sonucu: `unary_ops` PASS.

---

### F-011 (Yuksek) - Karma ifade temp/alias clobber (`(a+b) ^ (c<<2)`)
**Etki:** Ara sonuc korunmadigi icin dogru matematiksel sonuc bozuluyor.
**Durum:** **Kapali** (2026-02-28)

**Gozlem:**
- `expr_temporaries` case'inde beklenen `out=15`, emulator sonucu `out=0`.
- Uretilen asm'de sol taraftaki `a+b` sonucu korunmadan sag taraf hesabi tarafindan eziliyor; sonunda `XOR ACC` ile `RD==ACC` oldugu anda `0` cikiyor.

**Kod referanslari:**
- `modules/LIRGen.py` (temp_registers alias/accumulator korunumu)
- `tests/e2e_artifacts/expr_temporaries.asm`

**Kapanis notu:**
- Temp degerler sadece register alias ile tutulmak yerine memory spill akisiyla uretilecek sekilde lowering guncellendi.
- Assembly tarafinda `.t*` temp isimleri icin dinamik variable olusturma eklendi.
- E2E sonucu: `expr_temporaries` PASS.

---

## E2E Test Turu (2026-02-28, 2. Tur)

Eklenen yeni case'ler:
- `tests/e2e_cases/cond_compare_expr.c`
- `tests/e2e_cases/cond_logic_expr.c`
- `tests/e2e_cases/shift_left_var.c`
- `tests/e2e_cases/call_inline_const.c`

Sonuc:
- Toplam: 14
- PASS: 14
- FAIL: 0

Not:
- `cond_logic_expr` uzerinde `SETPR` + RA clobber kaynakli ara regression yakalandi ve kapatildi.
- `ConditionalOp` temp birlestirme (`.tX`) optimizasyonu `HIROptimizer` tarafina eklendi.
- `shift_left_var` akisi icin optimizer/backend cache-etkilesiminde MAR-bilinmezlik handling duzeltildi.

---

## Support-Package ile Eslestirme Ozet
- ISA source-of-truth assembler+emulator tarafinda net ve tutarli.
- Yeni compiler backend kararlarinda o taraftaki decode/execute semantigi baz alinmali.

Referanslar:
- `ArniComp-Support-Package/assembler/README.md:17`
- `ArniComp-Support-Package/assembler/modules/AssemblyHelper.py:38`
- `ArniComp-Support-Package/emulator/cpu.py:226`

## Onerilen Duzeltme Sirasi (MVP)
1. **F-004** Kalan operator lowering'leri (`|`, shifts, mul/div/mod, logical not).
2. **F-009** `CALL` lowering (arg passing + return convention).
3. **F-007** optimize LIR'in asm stage'de kullanilmasi.
4. **F-005/F-006/F-008** model temizligi ve yapisal refactor.

## Takip
Bu dosya sonraki turlarda checklist olarak guncellenecek.
Her duzeltmede ilgili bulguya:
- Durum: Acik / Devam Ediyor / Kapali
- Commit/degisiklik notu
- Ek test senaryosu
bilgisi eklenecek.
