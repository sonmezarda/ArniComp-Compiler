# ArniComp-Compiler Asama ve Ozellik Durum Raporu

Tarih: 2026-02-28  
Hazirlayan: Codex

## 1) Projenin Su Anki Asamasi

**Genel seviye:** Erken asama fakat calisan bir **C subset -> ISA assembly** pipeline'i mevcut.  
**Asama tanimi:** "Alpha - cekirdek backend prototipi".

Bu su anlama geliyor:
- Pipeline mimarisi kurulu ve calisiyor.
- Belirli bir dil alt-kumesinde (asagida listeli) uctan uca dogru sonuc uretiyor.
- Ozellikle kontrol akisi + bellek adresleme (MAR) tarafinda ilk kritik dogruluk sorunlari cozuldu.
- Kapsam disi kalan operatorler ve statement turleri halen acik olarak `NotImplemented` veriyor.

## 2) Pipeline Durumu (Modul Bazli)

### 2.1 Frontend Parse
- `pycparser` ile C parse: **Calisiyor**
- `main` fonksiyonunu alma: **Calisiyor**
- Top-level global decl parse: **Calisiyor**

### 2.2 Symbol Table
- `char/int`, `const/volatile` bilgisi: **Calisiyor**
- `main` icindeki degiskenleri static alana koyma modeli: **Calisiyor** (tasarimsal olarak gecici)
- Cok fonksiyon/stack-temelli kapsam: **Henuz yok**

### 2.3 HIR Uretimi
- Atama, aritmetik expr, if/else, goto/label: **Calisiyor**
- Unary (`-`, `~`, `!`) HIR satirlari: **Calisiyor**
- `CALL` satirini HIR seviyesinde temsil: **Calisiyor**
- `while/for`: **Yok**

### 2.4 HIR Optimizasyon
- Constant propagation: **Calisiyor**
- Dead assignment elimination: **Calisiyor**
- Temp collapse (arithmetic/assignment + unary/call): **Calisiyor**

### 2.5 LIR Uretimi
- Assignment lowering (const, var->var): **Calisiyor**
- If/Goto/Label lowering: **Calisiyor**
- Aritmetik lowering (`+`, `-`, `&`, `^`): **Calisiyor**
- Unary lowering (`bitnot`, `neg`, `not`): **Calisiyor**
- `|` lowering (De Morgan sentezi): **Calisiyor**
- `<<` lowering (yalnizca sabit shift): **Calisiyor**
- `CALL` lowering: **Yok**
- `* / % >>` lowering: **Yok**
- `<<` variable shift lowering: **Yok**

### 2.6 LIR Optimizasyon
- `SETPR` redundant temizleme: **Calisiyor**
- `SETMAR` CFG-aware temizleme (basic block + dataflow): **Calisiyor**
- Branch guvenliginde MAR state koruma: **Calisiyor**

### 2.7 Assembly Uretimi
- ISA komutlari (`MOV/LDI/CMP/J*`, `ADD/SUB/AND/XOR/NOT`, `SMSBRA`): **Calisiyor**
- MAR cache invalidation (label join noktalarinda): **Calisiyor**
- Register-to-register MOV backend destegi: **Calisiyor**

## 3) Uctan Uca Kesin Calisan Ozellikler (Dogrulanmis)

Asagidaki ozellikler compile + assemble + emulator ile test edilmis ve **PASS** alinmistir:

1. Sabit atama: `a = 42`
2. Degisken kopyalama: `b = a`
3. If/else kontrol akisi: `if (a > 50) ... else ...`
4. Aritmetik toplama: `a = a + b`
5. Aritmetik cikarma: `a = a - b`
6. Bitwise AND: `a = a & b`
7. Bitwise XOR: `a = a ^ b`
8. Bitwise OR: `a = a | b` (sentezlenmis)
9. Bitwise NOT: `a = ~b`
10. Unary minus: `a = -b`
11. Logical NOT: `a = !b`
12. Left shift (sabit): `a = b << 2`
13. Negatif literal: `a = -1`

## 4) Dogrulama Matrisi (Calisanlar)

| Senaryo | Beklenen | Sonuc |
|---|---:|---:|
| `assign_const` | `a=42` | PASS |
| `assign_copy` | `a=9,b=9` | PASS |
| `if_else` | `a=50,b=200` | PASS |
| `add` | `a=15` | PASS |
| `sub` | `a=7` | PASS |
| `and` | `a=10` | PASS |
| `xor` | `a=5` | PASS |
| `or` | `a=15` | PASS |
| `bitnot` | `a=255` | PASS |
| `neg` | `a=255` | PASS |
| `logical_not` | `a=1` | PASS |
| `shl_const` | `a=12` | PASS |
| `negative_literal` | `a=255` | PASS |

## 5) Bilincli Olarak Henuz Calismayanlar (Beklenen Fail)

Asagidakiler su an destek disi ve bilinclu sekilde hata veriyor:

1. Carpma: `*`
2. Bolme: `/`
3. Mod: `%`
4. Sag kaydirma: `>>`
5. Degisken miktarda sol kaydirma: `a << b`
6. Fonksiyon cagrisi lowering: `CALL`
7. `while` statement lowering
8. `for` statement lowering

## 6) Bilinen Tasarimsal Sinirlar

1. Mimari 8-bit oldugu icin tum runtime sonuclar 0..255 araligina sariliyor.
2. `main` local degiskenleri static/global benzeri adrese yerlestiriliyor (stack modeli henuz yok).
3. Control-flow analizleri ilk asamada; daha agresif code motion/hoisting henuz yok.
4. `CALL` icin ABI (arg passing / return convention / clobber kurallari) tanimli degil.

## 7) Kod Durumu (Degisiklik Alani)

Son degisikliklerde etkilenen ana dosyalar:
- `entities/HirLine.py`
- `modules/HIROptimizer.py`
- `entities/LirLine.py`
- `modules/LIRGen.py`
- `modules/LIROptimizer.py`
- `modules/AssemblyGen.py`
- `COMPILER_INCELEME_NOTLARI.md`

## 8) Sonraki Teknik Asama Onerisi

Cekirdek kisitlarini koruyarak onerilen siralama:

1. `>>` lowering (sabit ve sonra variable)
2. `*` lowering (tekrarlayan toplama + erken cikis optimizasyonu)
3. `/` ve `%` lowering (tekrarlayan cikarma, carry/compare tabanli)
4. `while` lowering (label + condition re-eval + CFG entegrasyonu)
5. `CALL` lowering icin minimal ABI

## 9) Kisa Sonuc

Proje su an "calisan cekirdek prototip" asamasinda.  
Dar ama anlamli bir C alt-kumesi icin compiler->assembler->emulator zinciri dogru sonuc veriyor.  
Kritik bir sonraki adim, ifade kapsamini (`* / % >>`) ve statement kapsamini (`while/for`) sistematik genisletmek.
